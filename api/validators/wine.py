from api.models.label import FieldResult
from api.validators.common import field_fail, field_pass, field_unreadable


REQUIRED_FIELDS: list[tuple[str, str]] = [
    ("brand_name", "27 CFR 4.32"),
    ("class_type", "27 CFR 4.34"),
    ("alcohol_content", "27 CFR 4.36"),
    ("net_contents", "27 CFR 4.72"),
    ("name_address", "27 CFR 4.35"),
]


def validate_wine(extracted: dict[str, str | None], unreadable: set[str]) -> list[FieldResult]:
    results: list[FieldResult] = []
    for key, cfr in REQUIRED_FIELDS:
        if key in unreadable:
            results.append(field_unreadable(key, f"{key} unreadable after OCR retry", cfr))
            continue
        value = extracted.get(key)
        if not value:
            results.append(field_fail(key, f"{key} missing — required for wine >=7% ABV", cfr))
            continue
        if key == "alcohol_content" and "ABV" in value.upper():
            results.append(
                field_unreadable(
                    key,
                    "Alcohol content format ambiguous: uses 'ABV'; requires agent review",
                    cfr,
                )
            )
            continue
        results.append(field_pass(key, value, image_idx=extracted.get(f"{key}_image_idx")))
    return results
