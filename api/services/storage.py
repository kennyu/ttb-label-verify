from pathlib import Path
from uuid import uuid4

from fastapi import UploadFile
from loguru import logger

from api.config import settings
from api.models.upload import UploadedImage

ALLOWED_TYPES = {"image/jpeg", "image/png"}
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png"}


def validate_image_type(upload: UploadFile) -> None:
    suffix = Path(upload.filename or "").suffix.lower()
    if upload.content_type not in ALLOWED_TYPES or suffix not in ALLOWED_EXTENSIONS:
        raise ValueError("Only JPEG and PNG files are accepted")


async def save_upload(upload: UploadFile) -> UploadedImage:
    validate_image_type(upload)

    file_id = str(uuid4())
    suffix = Path(upload.filename or "").suffix.lower() or ".jpg"
    storage_key = f"{file_id}{suffix}"
    destination = settings.upload_path / storage_key

    data = await upload.read()
    destination.write_bytes(data)
    logger.debug(
        "File saved storage_key={} destination={} size_bytes={}",
        storage_key,
        str(destination),
        len(data),
    )

    return UploadedImage(
        id=file_id,
        filename=upload.filename or storage_key,
        content_type=upload.content_type or "application/octet-stream",
        storage_key=storage_key,
        size_bytes=len(data),
    )


def read_image_bytes(storage_key: str) -> bytes:
    path = settings.upload_path / storage_key
    if not path.exists():
        logger.error("Storage key not found storage_key={} path={}", storage_key, str(path))
        raise FileNotFoundError(f"Image not found: {storage_key}")
    logger.debug("Reading image bytes storage_key={} path={}", storage_key, str(path))
    return path.read_bytes()
