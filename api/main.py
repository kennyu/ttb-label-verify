from pathlib import Path
import sys
import time
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from loguru import logger

from api.config import Settings, settings
from api.routes.health import router as health_router
from api.routes.labels import router as labels_router
from api.routes.upload import router as upload_router


def _configure_logging(app_settings: Settings) -> None:
    logger.configure(patcher=lambda record: record["extra"].setdefault("request_id", "-"))
    logger.remove()
    logger.add(
        sys.stderr,
        level=app_settings.log_level.upper(),
        format="{time:YYYY-MM-DD HH:mm:ss.SSS} | {level} | req={extra[request_id]} | {name}:{function}:{line} | {message}",
    )


@asynccontextmanager
async def lifespan(app: FastAPI):
    app_settings = settings
    _configure_logging(app_settings)
    app.state.settings = app_settings
    logger.bind(request_id="-").info(
        "Starting app app_name={} debug={} log_level={}",
        app_settings.app_name,
        app_settings.debug,
        app_settings.log_level,
    )
    yield
    logger.bind(request_id="-").info("Shutting down app app_name={}", app_settings.app_name)


app = FastAPI(title=settings.app_name, debug=settings.debug, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(upload_router)
app.include_router(labels_router)


@app.middleware("http")
async def add_request_context(request: Request, call_next) -> Response:
    request_id = request.headers.get("x-request-id", str(uuid4()))
    bound_logger = logger.bind(request_id=request_id)
    start = time.perf_counter()
    bound_logger.info("Request start method={} path={}", request.method, request.url.path)
    try:
        response = await call_next(request)
    except Exception:
        bound_logger.exception("Request failed method={} path={}", request.method, request.url.path)
        raise
    duration_ms = (time.perf_counter() - start) * 1000
    bound_logger.info(
        "Request finish method={} path={} status={} duration_ms={:.2f}",
        request.method,
        request.url.path,
        response.status_code,
        duration_ms,
    )
    response.headers["X-Request-ID"] = request_id
    return response

frontend_dist = Path("web/dist")
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="web")
