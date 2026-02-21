from pydantic import BaseModel, ConfigDict, Field

from api.models.label import BeverageType, LabelVerificationResult


class ImageRef(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    id: str = Field(min_length=1)
    filename: str = Field(min_length=1)
    storage_key: str = Field(min_length=1)


class LabelGroupRequest(BaseModel):
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    label_id: str = Field(min_length=1)
    label_name: str = Field(min_length=1)
    beverage_type: BeverageType
    images: list[ImageRef] = Field(min_length=1, max_length=3)


class BatchVerifyRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    labels: list[LabelGroupRequest] = Field(min_length=1, max_length=100)


class BatchResultsSnapshot(BaseModel):
    batch_id: str
    total: int
    completed: int
    results: list[LabelVerificationResult]
