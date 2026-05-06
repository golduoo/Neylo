# Neylo Agent Guide

This repository builds the Neylo computer vision subsystem for outdoor 11-a-side football video analysis.

## Product Goal

v1 ships an interactive web app for post-match clip review.

The core deliverable is:

- a **browser UI** where the user uploads a video, scrubs to any frame to see player detections, clicks one player to follow, then plays the video with that player's track highlighted (other detections toggleable).
- a **FastAPI backend** wrapping the CV pipeline (upload → detect → track → query) with REST endpoints for the UI and any other client.
- a **CLI** (`neylo run`) as a non-UI entry point that produces the same per-frame artifacts headlessly.
- per-frame Parquet records (`video_id`, `segment_id`, `frame_id`, `track_id`, `class`, `bbox`, `conf`) plus a track index for fast UI queries.
- stable player track IDs within continuous segments. Cross-segment re-identification is best-effort and not a v1 acceptance criterion.

## v1 Scope

Implement only:

- Detection of a single class: **`player`**. Goalkeeper / referee labels are too sparse in the available data (49 instances combined) to train discrimination; ball is deferred to v2 (separate small-object model with SAHI).
- Tracking for same-player association across frames within a continuous segment (BoT-SORT + ReID + CMC).
- A FastAPI backend serving upload, job-status, frame-detection, and track-by-id endpoints. See `docs/requirements/api.md`.
- A web UI (Vite + React + TypeScript + Tailwind + shadcn/ui) implementing the upload → process → interactive review flow. See `docs/requirements/ui.md`.
- A CLI entry point (`neylo run`) that runs the same pipeline without the UI.
- Evaluation scripts for detection / tracking quality and pipeline smoke tests.

Do not implement in v1:

- multi-class detection (goalkeeper / referee / ball)
- pitch homography, bird's-eye view, or real-world coordinates
- event detection such as pass, shot, goal
- team identification or cross-match ReID
- speed, distance, heatmap
- live streaming or per-frame on-demand inference (architecture is precompute-then-render)
- multi-tenancy, auth, or saved sessions in the web app

## Runtime Assumptions

- Primary environment: local Windows workstation with RTX 5090 24GB VRAM.
- Python: conda env `cv_env` (Python 3.11) with manually installed `torch 2.11.0+cu130`. System Python 3.12.7 is not used.
- `env/requirements.txt` does not pin torch, so the manual CUDA-matched build stays in place.
- Pipeline configuration is centralized in `configs/pipeline.yaml`.
- Long videos are processed as segments. v1 inputs are short Veo highlights so a single-segment-per-video shortcut is acceptable; real 1–2 minute segmentation is in Phase 6.
- Prefer deterministic, restartable stages over hidden mutable state.
- Storage is local filesystem (`uploads/`, `outputs/`); object storage is Phase 7.

## Engineering Principles

- Keep module boundaries explicit: pipeline orchestration, detection, tracking, data contracts, export, evaluation, and the API/UI surface should stay separable.
- Use Pydantic v2 schemas for stage inputs and outputs and (where it fits) for API request/response models.
- Prefer existing libraries for core CV logic: `ultralytics`, `sahi`, `torchreid`, `supervision`, `prefect`, `pyarrow`.
- Every pipeline stage is idempotent. Re-running a failed stage must not corrupt previous outputs.
- Make outputs inspectable: save intermediate metadata, logs, and sample visualizations.
- Add focused tests for contracts, task behavior, and small end-to-end samples. API endpoints have contract tests; UI components have unit tests.
- Keep code clear and boring. Avoid large abstractions until duplication or complexity requires them.

## Directory Targets

Expected project shape:

```text
neylo/
├── AGENTS.md
├── PLAN_v2.md
├── configs/
│   └── pipeline.yaml
├── data/                       # local-only, gitignored
├── docs/
│   ├── requirements/
│   │   ├── pipeline.md
│   │   ├── detection.md
│   │   ├── tracking.md
│   │   ├── data.md
│   │   ├── evaluation.md
│   │   ├── api.md              # Phase 2
│   │   └── ui.md               # Phase 3
│   └── decisions/
├── env/
│   ├── environment.yml
│   └── requirements.txt
├── neylo/                      # Python package
│   ├── api/                    # Phase 2: FastAPI app
│   ├── cli/
│   ├── pipeline/
│   ├── services/
│   │   ├── detection/
│   │   └── tracking/
│   ├── schemas/
│   └── evaluation/
├── web/                        # Phase 3: React + Vite + TS frontend
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── docker/
└── tests/                      # Python tests; web tests live under web/
```

## Requirement Files

Before implementing a module, read the matching requirement file:

- `docs/requirements/pipeline.md` for orchestration, decode, stages, export, and jobs
- `docs/requirements/detection.md` for YOLO11, SAHI, training, inference, and detection outputs
- `docs/requirements/tracking.md` for BoT-SORT, ReID, CMC, and offline tracklet stitching
- `docs/requirements/data.md` for raw data, annotations, splits, labels, and dataset layout
- `docs/requirements/evaluation.md` for KPIs, tests, metrics, and acceptance criteria
- `docs/requirements/api.md` for FastAPI endpoints, job lifecycle, and storage layout (Phase 2)
- `docs/requirements/ui.md` for the React UI state machine, components, and interaction model (Phase 3)
- `docs/decisions/architecture.md` for major architecture decisions and tradeoffs

## Acceptance Bar

A change is not complete unless it includes the relevant verification path:

- unit tests for schemas and pure logic
- smoke test on a short sample video when touching the pipeline
- exported sample Parquet (and optional annotated MP4) when touching inference or tracking
- contract tests on every endpoint when touching the API
- component or e2e tests when touching the UI
- metric output when touching evaluation
