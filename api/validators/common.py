from api.models.label import FieldResult, FieldStatus


def field_pass(name: str, extracted: str | None, image_idx: int | None = None) -> FieldResult:
    return FieldResult(
        field_name=name,
        status=FieldStatus.PASS,
        extracted_value=extracted,
        found_on_image=image_idx,
    )


def field_fail(name: str, reason: str, cfr: str, extracted: str | None = None) -> FieldResult:
    return FieldResult(
        field_name=name,
        status=FieldStatus.FAIL,
        extracted_value=extracted,
        failure_reason=reason,
        cfr_reference=cfr,
    )


def field_unreadable(name: str, reason: str, cfr: str) -> FieldResult:
    return FieldResult(
        field_name=name,
        status=FieldStatus.UNREADABLE,
        failure_reason=reason,
        cfr_reference=cfr,
    )
