from pathlib import Path

from loguru import logger

from api.models.batch import LabelGroupRequest
from api.models.label import (
    BeverageType,
    FieldResult,
    LabelVerificationResult,
    OverallStatus,
)
from api.services.openai_client import ExtractionFailed, extract_label_fields
from api.services.storage import read_image_bytes
from api.validators.beer import validate_beer
from api.validators.health_warning import validate_warning_exact
from api.validators.spirits import validate_spirits
from api.validators.wine import validate_wine


def _resolve_auto_beverage_type(extracted: dict[str, str | None]) -> BeverageType:
    detected = (extracted.get("beverage_type") or "").strip().lower()
    if detected in {BeverageType.SPIRITS.value, BeverageType.BEER.value, BeverageType.WINE.value}:
        return BeverageType(detected)

    class_type = (extracted.get("class_type") or "").lower()
    spirits_tokens = ("whiskey", "whisky", "bourbon", "gin", "rum", "vodka", "tequila", "brandy")
    beer_tokens = ("beer", "ale", "lager", "stout", "porter", "pilsner", "ipa")
    wine_tokens = ("wine", "cabernet", "merlot", "pinot", "chardonnay", "sauvignon", "sparkling")
    if any(token in class_type for token in spirits_tokens):
        return BeverageType.SPIRITS
    if any(token in class_type for token in beer_tokens):
        return BeverageType.BEER
    if any(token in class_type for token in wine_tokens):
        return BeverageType.WINE

    return BeverageType.SPIRITS


async def verify_label_group(group: LabelGroupRequest) -> LabelVerificationResult:
    try:
        logger.info(
            "Label verification started label_id={} label_name={} beverage_type={} image_count={}",
            group.label_id,
            group.label_name,
            group.beverage_type.value,
            len(group.images),
        )
        images: list[tuple[bytes, str, str]] = []
        for image in group.images:
            image_bytes = read_image_bytes(image.storage_key)
            ext = Path(image.storage_key).suffix.lower()
            images.append((image_bytes, ext, image.filename))
        logger.debug("Label images loaded label_id={} storage_keys={}", group.label_id, [i.storage_key for i in group.images])

        pass_one = await extract_label_fields(images, group.beverage_type, specialized_retry=False)
        unreadable = set(pass_one.get("unreadable_fields", []))
        logger.info(
            "OCR pass 1 complete label_id={} unreadable_fields={}",
            group.label_id,
            sorted(unreadable),
        )

        extracted = pass_one
        if unreadable:
            pass_two = await extract_label_fields(images, group.beverage_type, specialized_retry=True)
            extracted = pass_two
            unreadable = set(pass_two.get("unreadable_fields", []))
            logger.info(
                "OCR retry complete label_id={} unreadable_fields={}",
                group.label_id,
                sorted(unreadable),
            )

        resolved_beverage_type = group.beverage_type
        if group.beverage_type == BeverageType.AUTO:
            resolved_beverage_type = _resolve_auto_beverage_type(extracted)
            logger.info(
                "Auto beverage type resolved label_id={} resolved_beverage_type={}",
                group.label_id,
                resolved_beverage_type.value,
            )

        if resolved_beverage_type.value == "spirits":
            fields = validate_spirits(extracted, unreadable)
        elif resolved_beverage_type.value == "beer":
            fields = validate_beer(extracted, unreadable)
        else:
            fields = validate_wine(extracted, unreadable)
        logger.debug(
            "Field validation complete label_id={} field_count={} fail_count={} unreadable_count={}",
            group.label_id,
            len(fields),
            sum(1 for f in fields if f.status.value == "fail"),
            sum(1 for f in fields if f.status.value == "unreadable"),
        )

        warning_ok, warning_reason = validate_warning_exact(extracted.get("government_warning"))
        if warning_ok:
            fields.append(
                FieldResult(
                    field_name="government_warning",
                    status="pass",
                    extracted_value=extracted.get("government_warning"),
                    cfr_reference="27 CFR Part 16",
                )
            )
        else:
            fields.append(
                FieldResult(
                    field_name="government_warning",
                    status="fail",
                    extracted_value=extracted.get("government_warning"),
                    failure_reason=warning_reason,
                    cfr_reference="27 CFR Part 16",
                )
            )

        has_fail = any(f.status.value == "fail" for f in fields)
        has_unreadable = any(f.status.value == "unreadable" for f in fields)

        if has_fail:
            overall = OverallStatus.FAIL
            escalation_reason = None
        elif has_unreadable:
            overall = OverallStatus.ESCALATE
            escalation_reason = "Unreadable or ambiguous field values require human review"
        else:
            overall = OverallStatus.PASS
            escalation_reason = None
        logger.info(
            "Label verification finished label_id={} status={} has_fail={} has_unreadable={}",
            group.label_id,
            overall.value,
            has_fail,
            has_unreadable,
        )

        return LabelVerificationResult(
            label_id=group.label_id,
            label_name=group.label_name,
            overall_status=overall,
            beverage_type=resolved_beverage_type,
            fields=fields,
            escalation_reason=escalation_reason,
            images_processed=len(group.images),
        )
    except ExtractionFailed as exc:
        logger.error(
            "Label verification extraction failure label_id={} label_name={} error={}",
            group.label_id,
            group.label_name,
            str(exc),
        )
        return LabelVerificationResult(
            label_id=group.label_id,
            label_name=group.label_name,
            overall_status=OverallStatus.FAIL,
            beverage_type=BeverageType.SPIRITS if group.beverage_type == BeverageType.AUTO else group.beverage_type,
            fields=[
                FieldResult(
                    field_name="ocr_extraction",
                    status="fail",
                    failure_reason=str(exc),
                    cfr_reference=None,
                )
            ],
            escalation_reason=None,
            images_processed=len(group.images),
        )
    except Exception as exc:
        logger.exception(
            "Label verification error label_id={} label_name={} error={}",
            group.label_id,
            group.label_name,
            str(exc),
        )
        return LabelVerificationResult(
            label_id=group.label_id,
            label_name=group.label_name,
            overall_status=OverallStatus.ERROR,
            beverage_type=BeverageType.SPIRITS if group.beverage_type == BeverageType.AUTO else group.beverage_type,
            fields=[
                FieldResult(
                    field_name="processing",
                    status="fail",
                    failure_reason=f"Processing error: {exc}",
                )
            ],
            escalation_reason=None,
            images_processed=len(group.images),
        )
