# TTB Label Verifier (Prototype)

## Features
- FastAPI backend:
  - `POST /upload` (JPEG/PNG only)
  - `POST /verify/batch` (SSE streaming per-label results)
  - `GET /verify/batch/{batch_id}/export.csv` (CSV export)
- Verification logic:
  - Multi-image label groups (1-3 images)
  - OCR retry path for unreadable fields
  - `PASS` / `FAIL` / `ESCALATE` / `ERROR` outcomes
  - Government warning validator with heading case requirement (`GOVERNMENT WARNING:`)
- React + Vite frontend:
  - Upload, group, and bulk single-group creation
  - Streamed results with full-size label previews
  - Remove actions for ungrouped images and streamed results
  - CSV export link for completed batch

## Requirements
- Python 3.14+
- `uv`
- Bun

## Environment
Create `.env` (or copy from `.env.example`) and set:
- `OPENAI_API_KEY` (required for verification)
- `OPENAI_MODEL` (default: `gpt-4.1-mini`)
- `OPENAI_TIMEOUT_SECONDS` (default: `60`)
- `OPENAI_MAX_RETRIES` (default: `2`)
- `LOG_LEVEL` (`INFO` or `DEBUG`)
- `UPLOAD_DIR` (default: `tmp/uploads`)
- `MAX_BATCH_SIZE` (default: `100`)

## Local Run
### Backend
```bash
uv venv
source .venv/bin/activate
uv sync
cp .env.example .env
uv run uvicorn api.main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend
```bash
cd web
bun install
bun run dev
```

Frontend dev server proxies API calls to `http://localhost:8000`.

## Test
```bash
uv run pytest -q
```

## Notes
- Verification now fails explicitly if OpenAI extraction is unavailable or errors (no mock fallback path).
- Batch max is 100 labels.
- Partial per-label processing errors do not block the rest of the batch stream.
- Logging uses `loguru`. Set `LOG_LEVEL=DEBUG` in `.env` to trace OCR pass/retry and per-label verification flow.
- Every backend response includes `X-Request-ID`; pass your own `x-request-id` header to correlate request logs.

## Railway Deploy
Use this start command:
```bash
uv run uvicorn api.main:app --host 0.0.0.0 --port $PORT
```
