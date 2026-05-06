# Architecture Decisions

This file records major decisions so future agents do not repeatedly reopen settled questions.

## ADR-001: Offline Batch First

Decision:

- v1 is an offline post-match batch pipeline, not a real-time livestream system.

Reason:

- current goal is stable detection and tracking
- offline processing allows heavier models, segment-level retries, and post-processing
- tracklet stitching benefits from seeing the full segment or match

Consequences:

- latency is less important than accuracy and reproducibility
- outputs should be persisted between stages
- future livestream support should be a separate v2 design

## ADR-002: YOLO11 For Detection

Decision:

- use YOLO11 through `ultralytics` as the primary detector.

Reason:

- strong object detection baseline
- simple training and export workflow
- integrates with common tracking workflows

Consequences:

- detection output must be converted into Neylo-owned schemas
- avoid leaking raw Ultralytics result objects across module boundaries

## ADR-003: BoT-SORT + ReID + CMC For Player Tracking

Decision:

- use BoT-SORT with ReID and camera motion compensation.

Reason:

- football clips include camera pan/tilt
- player ID stability is the v1 priority
- ReID plus CMC should reduce track fragmentation and ID swaps

Consequences:

- tracking needs access to frame data, not just detections
- tracker config must expose CMC options
- offline stitching should be kept as a separate post-processing step

## ADR-004: Defer Pitch Calibration

Decision:

- do not implement pitch homography, bird's-eye view, or real-world coordinates in v1.

Reason:

- far-side pitch lines may be occluded
- PTZ-like camera motion complicates calibration
- v1 does not need speed, distance, or event detection

Consequences:

- all v1 outputs are image-coordinate based
- analytics requiring real-world coordinates are v2 work

## ADR-005: Local Filesystem Before Services

Decision:

- v1 can use local filesystem outputs before adding MinIO and PostgreSQL.

Reason:

- current environment is a local GPU workstation
- simpler iteration matters during model and tracker development

Consequences:

- design path conventions cleanly
- keep storage adapters possible, but do not block v1 on service infrastructure

## ADR-006: Single-Worker Serial Job Processing For v1 API

Decision:

- The FastAPI backend (Phase 2) processes jobs **serially** in a single
  worker process.
- The YOLO model is loaded once at startup and reused across jobs.
- Concurrent uploads are queued and run one at a time. Queue position
  is exposed via `GET /api/v1/jobs/{id}`.
- Jobs are dispatched via FastAPI's `BackgroundTasks`. Job state
  (status, progress, output paths) lives in an in-process dict guarded
  by a single `asyncio.Lock`.

Reason:

- v1 runs on one local workstation with one GPU (RTX 5090); two
  concurrent jobs would compete for ~24 GB VRAM and slow each other
  down rather than parallelize.
- `BackgroundTasks` runs inside the same process as the request handler:
  no broker, no extra infrastructure.
- Reloading the YOLO model per job would add 1–3 s of latency per
  upload and waste GPU warmup time. One persistent instance is fine
  because we never run two `model.track()` calls at once.

Consequences and migration path to parallel processing:

When v1 grows beyond a single user, the system needs a real queue. The
migration is intentionally bounded and localized:

1. **Job state**: replace the in-process dict in `neylo/api/jobs.py`
   with a persistent store. Default choice: PostgreSQL (already in the
   Phase 7 plan) or Redis. Necessary because state must survive worker
   restarts and be visible to multiple workers.
2. **Queue**: replace `BackgroundTasks` with one of:
   - **Prefect** — already pinned in `env/requirements.txt`, was the
     intended target from day one (see PLAN_v2 §12 Phase 7).
   - **Celery** + Redis broker — the most common choice if Prefect's
     opinions don't fit.
   - **RQ** — simplest, Python-only, fewer features.
3. **Model lifecycle**: a single global `BotSortTracker` instance is
   not safe under concurrency. Either (a) one tracker per worker
   process (simple, costs 1× model VRAM per worker), or (b) a
   request-scoped `model.track(persist=True)` plus a per-job tracker
   id namespace (complex; not recommended). Pick (a).
4. **GPU memory**: with N parallel workers each holding their own YOLO
   instance + ultralytics tracker state, set N so that
   `N × peak_vram_per_job < total_vram - safety_margin`. For
   yolo11n at imgsz 1280 on RTX 5090, a conservative starting point
   is N=2.
5. **Status enum**: add `queued_pending_worker` to the
   `GET /api/v1/jobs/{id}` status field so the UI can distinguish
   "your job is in line" from "your job is currently running but on
   another worker".

Files affected when this migration happens:

- `neylo/api/main.py` — replace `BackgroundTasks` dispatch with the
  queue's enqueue call
- `neylo/api/jobs.py` — replace in-process registry with the persistent
  store adapter
- `neylo/api/lifespan.py` (Phase 2 file) — model loading moves from
  startup hook to per-worker init
- `env/requirements.txt` — pin the queue library (Celery / Prefect / RQ)
- `configs/pipeline.yaml` — add a `runtime.api` section with
  `workers`, `max_concurrent_jobs`, queue connection strings
- `docs/requirements/api.md` — update the "single-worker" notes and
  the status-enum table

The migration is approximately one focused PR per item above, in the
order listed. None of the v1 contracts (endpoint shapes, output
filenames, schema columns) need to change.

