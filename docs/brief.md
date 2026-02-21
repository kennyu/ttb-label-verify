# Brief

I approached this project by making the assumption that 1 to 3 image labels could be represented as one product. For example, a front and back label belonging to the same beverage. I scoped the detection to three types: spirit, beer / malt beverage, and wine. Each beverage type has specific validation logic as well as a common validation for elements like the goverment warning. The user can leave it to the app to auto-detect the beverage or override with the beverage type. The second assumption is that uploading the labels is a seperate step from verifying the labels. The user can batch verify after uploading the labels. The third assumption is that labels is either a PASS / FAIL / UNREADABLE state and the OCR will retry once if it is UNREADABLE. We use async calls to verify the labels and stream the results to the user so the user will not have to wait for the entire batch to finish. The labels are marked as PASS, FAIL, ESCALATE ( unreadable ) or ERROR ( missing api keys, or internal app issue ) 

## Approach
- Built a vertical-slice prototype first (upload -> verify -> stream -> export) to get a usable product quickly.
- Implemented backend-first core logic in FastAPI, then layered a single-screen React UI for grouping, live batch status, and CSV export.
- Used asynchronous batch processing with bounded concurrency (`Semaphore(10)`) and SSE (`StreamingResponse`) so results arrive per-label as soon as each finishes.
- Added deterministic compliance outcomes with two levels:
  - Field-level statuses: `pass`, `fail`, `unreadable`
  - Overall label outcomes: `PASS`, `FAIL`, `ESCALATE`, `ERROR` (`RETRY` is internal processing behavior)
  Each result includes explicit reasons and CFR references where applicable.
- Added auto-detect beverage type (`auto`) with manual override options (`spirits`, `beer`, `wine`).
- Removed mock extraction fallback: OpenAI extraction errors now fail explicitly so behavior is production-honest.

## Tools Used
- Backend:
  - `FastAPI` + `uvicorn`
  - `pydantic` + `pydantic-settings`
  - `openai` Python SDK (Responses API, async client)
  - `python-multipart`
  - `loguru` (request-correlated logging)
- Frontend:
  - `React` + `TypeScript` + `Vite`
  - `Bun` for package install/build/dev
- Packaging/Runtime:
  - `uv` for Python dependency management and execution
  - Multi-stage `Dockerfile` (Bun frontend build + Python runtime) for single-container Railway deploy
- Testing/Validation:
  - `pytest` regression tests for upload validation, SSE partial-failure behavior, and CSV export

## Assumptions Made
- Prototype scope only: no auth, no COLA integration, no persistent audit store.
- Accepted upload formats are JPEG/PNG only.
- Max batch size is 100 labels.
- Partial batch failures should not block already-completed results from streaming.
- CSV is the only export format for v1.
- OpenAI API access is available in deployment environment and `OPENAI_API_KEY` is configured.
- Temporary file storage is local disk for now (`UPLOAD_DIR`), with R2 as a future enhancement.
- Frontend and backend are deployed together in one Railway container, with FastAPI serving `web/dist`.
