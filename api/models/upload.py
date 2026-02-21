from pydantic import BaseModel


class UploadedImage(BaseModel):
    id: str
    filename: str
    content_type: str
    storage_key: str
    size_bytes: int
