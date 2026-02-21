from api.models.label import FieldResult
from api.validators.common import field_fail, field_pass, field_unreadable


REQUIRED_FIELDS: list[tuple[str, str]] = [
    ("brand_name", "27 CFR 7.64"),
    ("class_type", "27 CFR 7.141"),
    ("net_contents", "27 CFR 7.70"),
    ("name_address", "27 CFR 7.66"),
]


def validate_beer(extracted: dict[str, str | None], unreadable: set[str]) -> list[FieldResult]:
    results: list[FieldResult] = []
    for key, cfr in REQUIRED_FIELDS:
        if key in unreadable:
            results.append(field_unreadable(key, f"{key} unreadable after OCR retry", cfr))
            continue
        value = extracted.get(key)
        if not value:
            results.append(field_fail(key, f"{key} missing — required for malt beverages", cfr))
            continue
        results.append(field_pass(key, value, image_idx=extracted.get(f"{key}_image_idx")))

    abv = extracted.get("alcohol_content")
    if abv and "ABV" in abv.upper():
        results.append(
            field_unreadable(
                "alcohol_content",
                "Alcohol content uses non-permitted abbreviation 'ABV'; requires review",
                "27 CFR 7.63",
            )
        )
    return results
