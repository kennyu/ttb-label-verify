from enum import Enum

from pydantic import BaseModel


class BeverageType(str, Enum):
    SPIRITS = "spirits"
    BEER = "beer"
    WINE = "wine"


class FieldStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNREADABLE = "unreadable"


class OverallStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    ESCALATE = "ESCALATE"
    RETRY = "RETRY"
    ERROR = "ERROR"


class FieldResult(BaseModel):
    field_name: str
    status: FieldStatus
    found_on_image: int | None = None
    extracted_value: str | None = None
    failure_reason: str | None = None
    cfr_reference: str | None = None


class LabelVerificationResult(BaseModel):
    label_id: str
    label_name: str
    overall_status: OverallStatus
    beverage_type: BeverageType
    fields: list[FieldResult]
    escalation_reason: str | None = None
    images_processed: int


class BatchProgressEvent(BaseModel):
    batch_id: str
    completed: int
    total: int
    result: LabelVerificationResult
