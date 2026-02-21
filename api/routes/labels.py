import asyncio
import csv
import io
from uuid import uuid4

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response, StreamingResponse
from loguru import logger

from api.config import settings
from api.models.batch import BatchResultsSnapshot, BatchVerifyRequest, LabelGroupRequest
from api.models.label import BatchProgressEvent
from api.services.state import batch_store
from api.services.verification import verify_label_group

router = APIRouter(prefix="/verify", tags=["verify"])


async def _verify_with_limit(group: LabelGroupRequest, sem: asyncio.Semaphore):
    async with sem:
        return await verify_label_group(group)


@router.post("/batch")
async def verify_batch_stream(request: BatchVerifyRequest) -> StreamingResponse:
    if len(request.labels) > settings.max_batch_size:
        raise HTTPException(status_code=400, detail=f"Batch limit is {settings.max_batch_size}")

    batch_id = str(uuid4())
    total = len(request.labels)
    sem = asyncio.Semaphore(10)
    logger.info("Batch requested batch_id={} total_labels={}", batch_id, total)

    async def event_stream():
        completed = 0
        results = []

        tasks = [asyncio.create_task(_verify_with_limit(group, sem)) for group in request.labels]
        for task in asyncio.as_completed(tasks):
            result = await task
            completed += 1
            results.append(result)
            logger.info(
                "Batch label completed batch_id={} label_id={} label_name={} status={} progress={}/{}",
                batch_id,
                result.label_id,
                result.label_name,
                result.overall_status.value,
                completed,
                total,
            )

            event = BatchProgressEvent(
                batch_id=batch_id,
                completed=completed,
                total=total,
                result=result,
            )
            yield f"data: {event.model_dump_json()}\n\n"

        batch_store[batch_id] = BatchResultsSnapshot(
            batch_id=batch_id,
            total=total,
            completed=completed,
            results=results,
        )
        logger.info("Batch finished batch_id={} completed={}", batch_id, completed)
        yield "event: done\ndata: done\n\n"

    return StreamingResponse(event_stream(), media_type="text/event-stream")


@router.get("/batch/{batch_id}/export.csv")
async def export_batch_csv(batch_id: str) -> Response:
    snapshot = batch_store.get(batch_id)
    if not snapshot:
        logger.warning("CSV export missing batch_id={}", batch_id)
        raise HTTPException(status_code=404, detail="Batch not found")

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(
        [
            "batch_id",
            "label_id",
            "label_name",
            "beverage_type",
            "overall_status",
            "field_name",
            "field_status",
            "extracted_value",
            "found_on_image",
            "failure_reason",
            "cfr_reference",
            "images_processed",
        ]
    )

    for result in snapshot.results:
        for field in result.fields:
            writer.writerow(
                [
                    snapshot.batch_id,
                    result.label_id,
                    result.label_name,
                    result.beverage_type.value,
                    result.overall_status.value,
                    field.field_name,
                    field.status.value,
                    field.extracted_value or "",
                    field.found_on_image if field.found_on_image is not None else "",
                    field.failure_reason or "",
                    field.cfr_reference or "",
                    result.images_processed,
                ]
            )

    csv_data = output.getvalue()
    headers = {"Content-Disposition": f'attachment; filename="batch-{batch_id}.csv"'}
    rows = sum(len(r.fields) for r in snapshot.results)
    logger.info(
        "CSV export generated batch_id={} rows={} labels={}",
        batch_id,
        rows,
        len(snapshot.results),
    )
    return Response(content=csv_data, media_type="text/csv", headers=headers)
