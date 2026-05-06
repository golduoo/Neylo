# Backend API Requirements (Phase 2)

## Purpose

Wrap the Phase 1 CV pipeline (ingest → decode → detect → track) behind a
FastAPI service so the web UI can drive video processing and consume
results. The CLI (`neylo run`) remains the non-UI entry point and shares
the same core library.

## Owner

Xiwen

## Stack

- Framework: **FastAPI** (Python 3.11, runs in `cv_env`)
- ASGI server: `uvicorn` for dev, `uvicorn` + `gunicorn` workers for
  later deployment
- Background jobs: in-process task runner for v1 (single worker,
  `asyncio.create_task` or `BackgroundTasks`); replaced by Prefect /
  Celery in Phase 7
- Storage: local filesystem (`uploads/`, `outputs/`) for v1; object
  storage in Phase 7
- Schemas: existing `neylo.schemas.*` Pydantic v2 models, reused as
  request/response types where possible

## Surface

All endpoints under `/api/v1`. CORS allow-listed for the dev frontend
origin.

### Job lifecycle

- `POST /api/v1/jobs`
  - body: `multipart/form-data` with the video file
  - returns: `{ job_id, status: "queued" }`
  - side effects: writes to `uploads/<job_id>/<original_filename>`
- `GET /api/v1/jobs/{job_id}`
  - returns: `{ job_id, status, progress: 0..1, error?, video: VideoAsset, segments: [...] }`
  - statuses: `queued | decoding | detecting | tracking | exporting | ready | failed`
- `GET /api/v1/jobs` (admin/debug)
  - returns: list of jobs with status

### Result queries (only valid when status == ready)

- `GET /api/v1/jobs/{job_id}/frames/{frame_id}`
  - returns: `{ frame_id, timestamp_ms, detections: [...], tracks: [...] }`
  - both lists scoped to the requested frame
- `GET /api/v1/jobs/{job_id}/tracks/{track_id}`
  - returns: `{ track_id, class_name, frames: [{frame_id, timestamp_ms, x1,y1,x2,y2, conf}, ...] }`
  - used by the UI to render a continuous highlight when the user
    selects a player
- `GET /api/v1/jobs/{job_id}/tracks`
  - returns: track index `{ track_id, class_name, first_frame, last_frame, n_frames, sample_thumb_url? }`
- `GET /api/v1/jobs/{job_id}/video`
  - returns: streamed MP4 (the original or a transcoded web-friendly
    version) for the `<video>` tag

### Health

- `GET /api/v1/health` → `{ status: "ok", gpu: bool, model_loaded: bool }`

## Storage layout

```
uploads/
  <job_id>/
    source.mp4
outputs/
  <job_id>/
    detections.parquet     # one row per (frame, detection)
    tracks.parquet         # one row per (frame, track)
    track_index.json       # { track_id: {first_frame, last_frame, n_frames, class} }
    job.json               # mirrors the GET /jobs/{job_id} response
```

`job_id` is a uuid4. Filenames are derived from `job_id` not the
original upload to avoid collisions and make paths predictable.

## Idempotency and resumability

- A job is identified by its `job_id`. Re-running the pipeline on the
  same `job_id` overwrites outputs atomically (write to temp file, then
  rename).
- If the API process crashes mid-job, the next call to
  `GET /api/v1/jobs/{job_id}` reports the last persisted status; the
  user can re-trigger with a separate endpoint (Phase 7 detail) or
  re-upload.

## Performance targets (v1)

- API process loads YOLO model on startup (or lazily on first job).
  Model stays warm across jobs.
- For a 10–20 s Veo highlight (≈300–500 frames at 25 fps) on RTX 5090:
  end-to-end (decode + yolo11n detect + BoT-SORT track + export) under
  30 s. Surfaced as a progress percentage.

## Testing

Required:

- contract tests on every endpoint using FastAPI's `TestClient`
- a job-lifecycle integration test against a synthetic mp4 (reuse the
  existing test fixture) — `slow` marker, opt-in
- pure unit tests on the storage adapter (write/read parquet, json)

## Out of scope for v1

- Auth / multi-tenancy
- Job cancellation / pause
- Cross-process job queue (single-worker FastAPI is enough)
- Object storage (S3 / MinIO)
- Webhook callbacks
- Live progress over WebSocket — polling `GET /jobs/{id}` is fine for v1
