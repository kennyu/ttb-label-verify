# TTB Label Verification Tool — Architecture

## Overview

Single-container Python application deployed on Railway. FastAPI handles the API layer and serves the compiled React frontend as static files. Images are temporarily stored in Cloudflare R2. Batch label verification runs fully async with results streamed to the client via SSE as each label completes.

---

## System Diagram

```
Browser
  │
  ├── POST /upload          → FastAPI → Cloudflare R2 (temp storage)
  │   returns image refs
  │
  ├── POST /verify/batch    → FastAPI
  │   (JSON: group refs)        ├── asyncio.gather() + Semaphore(10)
  │                             ├── fetch images from R2
  │                             ├── OpenAI Vision API (per group)
  │                             ├── validators (per beverage type)
  │                             └── yield SSE result per completed label
  │
  └── SSE stream ◄──────────── results stream as each label completes
```

---

## Project Structure

```
ttb-label-verifier/
├── api/
│   ├── main.py                     # App entrypoint, mounts static files, registers routes
│   ├── config.py                   # Pydantic Settings — env-based config
│   ├── routes/
│   │   ├── upload.py               # POST /upload — multipart → R2
│   │   ├── labels.py               # POST /verify, POST /verify/batch (SSE)
│   │   └── health.py
│   ├── services/
│   │   ├── verification.py         # Core verify logic — pure async functions
│   │   ├── ocr_retry.py            # Retry with specialized OCR prompt
│   │   ├── escalation.py           # Escalation decision logic
│   │   └── openai_client.py        # OpenAI async wrapper, prompt management
│   ├── validators/
│   │   ├── spirits.py              # 27 CFR Part 5 field rules
│   │   ├── beer.py                 # 27 CFR Part 7 field rules
│   │   ├── wine.py                 # 27 CFR Part 4 field rules
│   │   └── health_warning.py       # 27 CFR Part 16 — character-exact match
│   └── models/
│       ├── label.py                # LabelGroup, VerificationResult, FieldResult
│       ├── upload.py               # UploadedImage
│       └── batch.py                # BatchRequest, BatchStatus
├── web/                            # Vite + React (TypeScript)
│   ├── src/
│   │   ├── App.tsx
│   │   └── components/
│   │       ├── UploadPanel.tsx     # Single + batch upload, image grouping UI
│   │       ├── ResultsStream.tsx   # SSE consumer, renders results as they arrive
│   │       ├── LabelResult.tsx     # Per-label field-level result card
│   │       └── ProgressBar.tsx     # "12 of 100 processed"
│   ├── index.html
│   └── vite.config.ts
├── Dockerfile                      # Build web → copy dist/ → run uvicorn
└── pyproject.toml
```

---

## Request Flows

### Upload Flow

```
1. User selects and groups images in UI
2. POST /upload (multipart) → FastAPI
3. FastAPI streams files to Cloudflare R2 concurrently via aioboto3
4. Returns list of { id, filename, url } references
5. Frontend stores refs, activates Verify button
```

### Batch Verification Flow

```
1. POST /verify/batch (JSON: label groups with image refs)
2. FastAPI opens SSE stream (StreamingResponse)
3. asyncio.gather() spawns one coroutine per label group
4. Semaphore(10) limits concurrent OpenAI calls
5. Each coroutine:
     a. Fetches images from R2
     b. Calls OpenAI Vision API with all images in the group
     c. Parses extracted fields
     d. Runs beverage-type-specific validators
     e. Applies escalation logic
     f. Returns VerificationResult
6. asyncio.as_completed() yields each result as it finishes
7. SSE stream sends { result, completed, total } per label
8. Frontend renders result immediately, increments progress counter
9. Stream closes when all labels complete
```

---

## Libraries

### Backend

| Library | Purpose |
|---|---|
| `FastAPI` | API framework, SSE via `StreamingResponse` |
| `uvicorn` | ASGI server, async request handling |
| `aioboto3` | Async S3-compatible uploads/fetches to Cloudflare R2 |
| `openai` | Vision API calls — native async client |
| `pydantic` | Request/response validation, settings management |
| `python-multipart` | Multipart file upload parsing |

### Frontend

| Library | Purpose |
|---|---|
| `React` | Component-based UI |
| `TypeScript` | Type safety |
| `Vite` | Build tool — outputs `dist/` served by FastAPI |

### Infrastructure

| Service | Purpose |
|---|---|
| `Railway` | Single container deployment, no timeout ceiling |
| `Cloudflare R2` | Temp image storage — S3-compatible, no egress fees |
| `OpenAI Vision API` | OCR extraction + field validation reasoning |

---

## Key Data Models

```python
class BeverageType(str, Enum):
    SPIRITS = "spirits"
    BEER = "beer"
    WINE = "wine"

class FieldStatus(str, Enum):
    PASS = "pass"
    FAIL = "fail"
    UNREADABLE = "unreadable"

class FieldResult(BaseModel):
    field_name: str
    status: FieldStatus
    found_on_image: int | None       # image index within group
    extracted_value: str | None
    failure_reason: str | None       # plain English + CFR citation
    cfr_reference: str | None        # e.g. "27 CFR 5.32"

class LabelVerificationResult(BaseModel):
    label_id: str
    overall_status: str              # PASS | FAIL | ESCALATE | RETRY
    beverage_type: BeverageType
    fields: list[FieldResult]
    escalation_reason: str | None
    images_processed: int
```

---

## Escalation Logic

| Outcome | Condition |
|---|---|
| `PASS` | All required fields present, extracted, and compliant |
| `FAIL` | Required field absent, or Government Warning text does not match verbatim |
| `RETRY` | OCR could not extract a field — auto-retries with specialized OCR prompt |
| `ESCALATE` | After retry, extraction still fails; or extracted data is ambiguous and requires human judgment |

The Government Warning (27 CFR Part 16) is always `FAIL` on mismatch — never escalated. Character-exact, case-sensitive match required.

---

## Trade-offs

### Single container — FastAPI serves static frontend
- ✅ One deploy, no CORS, no cross-service coordination
- ✅ Simpler operationally for a prototype
- ❌ Frontend and backend scale together — cannot scale independently
- ❌ Frontend changes require a full container redeploy

### Two-step upload → verify
- ✅ Verification request is lightweight JSON — SSE stream starts immediately
- ✅ Upload and processing progress are separable in the UI
- ❌ Adds a round-trip before verification begins
- ❌ Requires temp storage and a cleanup strategy for uploaded files

### `asyncio.gather()` + `Semaphore(10)`
- ✅ 100 labels processed concurrently, not sequentially
- ✅ Semaphore prevents OpenAI rate limit errors (429s)
- ❌ Semaphore value (10) is a tunable starting point — requires monitoring to calibrate
- ❌ Per-label error handling must be explicit — an unhandled exception in one coroutine must not silently drop results

### `asyncio.as_completed()` for SSE ordering
- ✅ Results stream as each label finishes — fastest possible UI feedback
- ❌ Results arrive out of submission order — frontend matches results to labels by ID, not position

### OpenAI Vision API
- ✅ OCR extraction and validation reasoning in one call per label group
- ✅ Multi-image groups (2–3 images) passed in a single API call
- ❌ Non-deterministic — same label can return different extractions across runs
- ❌ Latency and cost are per-call and uncontrolled
- ❌ Prototype is dependent on OpenAI API availability and TTB network access to it

### Cloudflare R2 for temp storage
- ✅ No egress fees vs S3
- ✅ S3-compatible — `aioboto3` works without modification
- ❌ Images need explicit cleanup — no built-in TTL without a lifecycle rule or background task
- ❌ Adds an external dependency; images briefly live outside the request lifecycle

### Railway
- ✅ No function timeout — SSE stream stays open for the full batch duration
- ✅ Persistent process — no cold starts mid-batch
- ❌ No auto-scaling on base plan
- ❌ More ops responsibility than a managed platform — container runtime is self-managed

---

## Open Deployment Question

Confirm whether TTB's test network can reach Railway and the OpenAI API before committing to this stack. If network access is restricted, the backend may need to be deployed inside TTB's infrastructure, which changes the deployment target but not the application architecture.
