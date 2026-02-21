WARNING_TEXT = """GOVERNMENT WARNING: (1) According to the Surgeon General, women should not drink
alcoholic beverages during pregnancy because of the risk of birth defects.
(2) Consumption of alcoholic beverages impairs your ability to drive a car or
operate machinery, and may cause health problems."""


def _to_words(text: str) -> list[str]:
    compact = " ".join(text.split())
    return compact.split(" ") if compact else []


def validate_warning_exact(text: str | None) -> tuple[bool, str | None]:
    if not text:
        return False, "Government Warning missing — required per 27 CFR Part 16"

    expected_words = _to_words(WARNING_TEXT)
    observed_words = _to_words(text)

    if len(observed_words) < 3:
        return False, "Government Warning appears incomplete — required text missing (27 CFR Part 16)"
    if observed_words[0] != "GOVERNMENT" or observed_words[1] != "WARNING:":
        return False, "Government Warning heading must be exactly 'GOVERNMENT WARNING:' in all caps (27 CFR Part 16)"

    try:
        idx1 = observed_words.index("(1)")
        idx2 = observed_words.index("(2)")
    except ValueError:
        return False, "Government Warning must include both numbered clauses (1) and (2) (27 CFR Part 16)"
    if idx2 < idx1:
        return False, "Government Warning must include both numbered clauses in order (27 CFR Part 16)"

    if len(observed_words) != len(expected_words):
        return False, "Government Warning wording does not match required verbatim text (27 CFR Part 16)"

    for idx, expected_word in enumerate(expected_words):
        observed_word = observed_words[idx]
        if idx < 2:
            # The heading must be exact case.
            if observed_word != expected_word:
                return False, "Government Warning heading must be exactly 'GOVERNMENT WARNING:' in all caps (27 CFR Part 16)"
            continue
        if observed_word.lower() != expected_word.lower():
            return False, "Government Warning wording does not match required verbatim text (27 CFR Part 16)"

    return True, None
