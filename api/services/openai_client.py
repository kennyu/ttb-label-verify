import base64
from typing import Any

from loguru import logger
from openai import APIConnectionError, APIStatusError, AsyncOpenAI, RateLimitError
from pydantic import BaseModel, Field

from api.config import settings
from api.models.label import BeverageType


class ExtractionFailed(Exception):
    pass


class ExtractionPayload(BaseModel):
    beverage_type: str | None = None
    brand_name: str | None = None
    class_type: str | None = None
    alcohol_content: str | None = None
    net_contents: str | None = None
    name_address: str | None = None
    government_warning: str | None = None
    unreadable_fields: list[str] = Field(default_factory=list)


def _to_data_url(image_bytes: bytes, ext: str) -> str:
    mime = "image/png" if ext.lower() == ".png" else "image/jpeg"
    b64 = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime};base64,{b64}"


def _build_client() -> AsyncOpenAI:
    return AsyncOpenAI(
        api_key=settings.openai_api_key,
        timeout=settings.openai_timeout_seconds,
        max_retries=settings.openai_max_retries,
    )


def _normalize_payload(payload: ExtractionPayload | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, ExtractionPayload):
        return payload.model_dump()
    if "unreadable_fields" not in payload or not isinstance(payload["unreadable_fields"], list):
        payload["unreadable_fields"] = []
    return payload


async def extract_label_fields(
    images: list[tuple[bytes, str, str]],
    beverage_type: BeverageType,
    specialized_retry: bool = False,
) -> dict[str, Any]:
    filenames = [name for _, _, name in images]
    logger.debug(
        "Extraction requested beverage_type={} retry={} image_count={} filenames={}",
        beverage_type.value,
        specialized_retry,
        len(images),
        filenames,
    )
    if not settings.openai_api_key:
        logger.error(
            "OpenAI key missing; failing extraction beverage_type={} retry={}",
            beverage_type.value,
            specialized_retry,
        )
        raise ExtractionFailed("OpenAI extraction unavailable: OPENAI_API_KEY is not configured")

    client = _build_client()

    instruction = (
        "Extract required TTB label fields from these product label images. "
        "Return strict JSON only with keys: beverage_type, brand_name, class_type, alcohol_content, "
        "net_contents, name_address, government_warning, unreadable_fields (array of keys). "
        "Set beverage_type to one of: spirits, beer, wine."
    )
    if specialized_retry:
        instruction += " Focus on noisy, low-contrast text and infer layout context where possible."

    content: list[dict[str, Any]] = [{"type": "input_text", "text": instruction}]
    for image_bytes, ext, _ in images:
        content.append({"type": "input_image", "image_url": _to_data_url(image_bytes, ext)})

    try:
        logger.info(
            "Calling OpenAI extraction model={} beverage_type={} retry={} image_count={}",
            settings.openai_model,
            beverage_type.value,
            specialized_retry,
            len(images),
        )
        response = await client.responses.parse(
            model=settings.openai_model,
            input=[{"role": "user", "content": content}],
            text_format=ExtractionPayload,
        )
        if response.output_parsed is None:
            raise ValueError("Response parse produced no structured payload")
        parsed = _normalize_payload(response.output_parsed)
        logger.info(
            "OpenAI extraction success beverage_type={} retry={} unreadable_fields={}",
            beverage_type.value,
            specialized_retry,
            parsed.get("unreadable_fields", []),
        )
        return parsed
    except (APIConnectionError, RateLimitError, APIStatusError) as exc:
        logger.exception(
            "OpenAI API error; failing extraction beverage_type={} retry={} error={}",
            beverage_type.value,
            specialized_retry,
            str(exc),
        )
        raise ExtractionFailed(f"OpenAI API error: {exc}") from exc
    except Exception as exc:
        logger.exception(
            "OpenAI extraction parse failed; failing extraction beverage_type={} retry={} error={}",
            beverage_type.value,
            specialized_retry,
            str(exc),
        )
        raise ExtractionFailed(f"OpenAI extraction parse error: {exc}") from exc
