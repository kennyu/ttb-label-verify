from fastapi import APIRouter, File, HTTPException, UploadFile
from loguru import logger

from api.models.upload import UploadedImage
from api.services.storage import save_upload

router = APIRouter(prefix="/upload", tags=["upload"])


@router.post("", response_model=list[UploadedImage])
async def upload_images(files: list[UploadFile] = File(...)) -> list[UploadedImage]:
    if not files:
        raise HTTPException(status_code=400, detail="No files provided")
    logger.info("Upload request file_count={}", len(files))

    results: list[UploadedImage] = []
    for file in files:
        try:
            saved = await save_upload(file)
            results.append(saved)
            logger.info(
                "Upload stored file_id={} filename={} content_type={} size_bytes={}",
                saved.id,
                saved.filename,
                saved.content_type,
                saved.size_bytes,
            )
        except ValueError as exc:
            logger.warning(
                "Upload rejected filename={} content_type={} error={}",
                file.filename,
                file.content_type,
                str(exc),
            )
            raise HTTPException(status_code=400, detail=str(exc)) from exc
    return results
