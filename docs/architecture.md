# TTB Label Verification Tool — Architecture

## Overview

Single-container application deployed to Railway.

- FastAPI provides API endpoints and serves the compiled React frontend from `web/dist`.
- Images are stored temporarily on local disk (`UPLOAD_DIR`, default `tmp/uploads`) for this prototype.
- Batch verification runs asynchronously and streams per-label results to the UI via SSE.
- OpenAI Responses API performs extraction; there is no mock fallback path. Extraction failures produce explicit `FAIL` outcomes.

---

## System Diagram

```
Browser
  │
  ├── POST /upload          → FastAPI → local temp storage (tmp/uploads)
  │   returns image refs
  │
  ├── POST /verify/batch    → FastAPI
  │   (JSON: label groups)      ├── asyncio tasks + Semaphore(10)
  │                             ├── read images from temp storage
  │                             ├── OpenAI Responses API (per group)
  │                             ├── auto-detect beverage type (or manual override)
  │                             ├── validators (spirits / beer / wine)
  │                             └── yield SSE event per completed label
  │
  └── SSE stream ◄──────────── results stream as each label completes
```

---

## Project Structure

```
ttb-label-verifier/
├── api/
│   ├── main.py                     # FastAPI app, lifespan init, request-id logging middleware, static mount
│   ├── config.py                   # Pydantic settings
│   ├── routes/
│   │   ├── upload.py               # POST /upload
│   │   ├── labels.py               # POST /verify/batch (SSE), GET /verify/batch/{id}/export.csv
│   │   └── health.py               # GET /health
│   ├── services/
│   │   ├── openai_client.py        # OpenAI Responses API integration + structured parsing
│   │   ├── storage.py              # Local temp file validation/read/write
│   │   ├── verification.py         # Core verification flow + retry + status resolution
│   │   └── state.py                # In-memory batch snapshot store for CSV export
│   ├── validators/
│   │   ├── spirits.py
│   │   ├── beer.py
│   │   ├── wine.py
│   │   └── health_warning.py
│   └── models/
│       ├── label.py
│       ├── upload.py
│       └── batch.py
├── web/
│   ├── src/
│   │   ├── App.tsx                 # Upload/group/stream/export UI
│   │   ├── main.tsx
│   │   └── styles.css
│   ├── index.html
│   └── vite.config.ts
├── Dockerfile                      # Multi-stage: Bun build -> Python runtime
├── pyproject.toml
└── uv.lock
```

---

## Request Flows

### Upload Flow

```
1. User selects JPEG/PNG images in UI
2. POST /upload (multipart)
3. Backend validates MIME + extension, stores files in UPLOAD_DIR
4. Backend returns list of { id, filename, storage_key, content_type, size_bytes }
5. Frontend uses refs to create label groups
```

### Batch Verification Flow

```
1. POST /verify/batch with label groups (1-3 images per group)
2. FastAPI returns StreamingResponse (SSE)
3. One async task per label group, bounded by Semaphore(10)
4. Per label group:
     a. Load image bytes from local storage
     b. Call OpenAI Responses API (pass 1)
     c. If unreadable fields exist, retry with specialized OCR prompt (pass 2)
     d. Resolve beverage type:
        - if request beverage_type is auto: infer from extracted beverage_type or class_type heuristics
        - else use requested beverage_type directly
     e. Run validator set for resolved beverage type + government warning validator
     f. Return LabelVerificationResult
5. SSE emits { batch_id, completed, total, result } as tasks complete (out of submission order)
6. Final snapshot is stored in memory for CSV export endpoint
```

### CSV Export Flow

```
1. GET /verify/batch/{batch_id}/export.csv
2. Read in-memory batch snapshot
3. Flatten per-label field rows to CSV
4. Return text/csv attachment
```

---

## Libraries

### Backend

| Library | Purpose |
|---|---|
| `FastAPI` | API framework + SSE streaming |
| `uvicorn` | ASGI server |
| `openai` | Responses API (`AsyncOpenAI`) |
| `pydantic` | Request/response models |
| `pydantic-settings` | Environment configuration |
| `python-multipart` | File upload parsing |
| `loguru` | Structured app logging |

### Frontend

| Library | Purpose |
|---|---|
| `React` | UI |
| `TypeScript` | Type safety |
| `Vite` | Build/dev tooling |
| `Bun` | Package manager/runtime for frontend tasks |

### Infrastructure

| Service | Purpose |
|---|---|
| `Railway` | Single container deployment |
| `OpenAI API` | OCR extraction and structured field output |

---

## Key Data Models

```python
class BeverageType(str, Enum):
    AUTO = "auto"
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

class LabelVerificationResult(BaseModel):
    label_id: str
    label_name: str
    overall_status: OverallStatus
    beverage_type: BeverageType  # resolved type for auto mode
    fields: list[FieldResult]
    escalation_reason: str | None
    images_processed: int
```

---

## Verification & Escalation Logic

| Outcome | Condition |
|---|---|
| `PASS` | Required fields present and compliant |
| `FAIL` | Required field absent, warning mismatch, or extraction unavailable/error |
| `ESCALATE` | After OCR retry, unreadable/ambiguous fields remain |
| `ERROR` | Unexpected unhandled processing failure |

Government warning rule:
- Heading must be exactly `GOVERNMENT WARNING:` (all caps)
- Clauses `(1)` and `(2)` must exist in order
- Word-level comparison is used after whitespace/newline normalization

---

## Observability

- `loguru` is configured in app lifespan.
- All logs carry a `request_id` field.
- Middleware injects `X-Request-ID` in every response.
- Client can pass `x-request-id` header for end-to-end correlation.

---

## Deployment

Single container using root `Dockerfile` (multi-stage):

1. Build frontend with Bun (`web/dist`)
2. Install Python deps with `uv`
3. Run FastAPI with:

```bash
uv run uvicorn api.main:app --host 0.0.0.0 --port ${PORT:-8000}
```

Railway deploys the final Docker stage (`runtime`) as one container serving both API and frontend.

---

## Current Limits / Next Steps

- Batch snapshots are in-memory only (lost on restart).
- Temp image storage is local filesystem (not R2 yet).
- No background cleanup worker for old uploads.
- No persistent database/audit trail.

Potential next upgrades:
1. Replace local storage with Cloudflare R2 adapter.
2. Persist batch snapshots/results in DB.
3. Add lifecycle cleanup for uploads and batch records.
