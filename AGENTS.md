# Neylo Agent Guide

This repository builds the Neylo computer vision subsystem for outdoor 11-a-side football video analysis.

## Product Goal

v1 must reliably detect and track players in post-match offline videos.

The core deliverable is:

- annotated MP4 with bbox and track_id overlay
- per-frame Parquet records with `video_id`, `segment_id`, `frame_id`, `track_id`, `class`, `bbox`, `conf`
- stable player track IDs across a match segment

## v1 Scope

Implement only:

- Detection for `player`, `goalkeeper`, `referee` (ball deferred to v2)
- Tracking for same-player association across frames
- Offline batch pipeline from local video input to Parquet and annotated MP4 output
- Evaluation scripts for detection/tracking quality and pipeline smoke tests

Do not implement in v1:

- pitch homography, bird's-eye view, or real-world coordinates
- event detection such as pass, shot, goal
- team identification or cross-match ReID
- speed, distance, heatmap, or live streaming

## Runtime Assumptions

- Primary environment: local Windows workstation with RTX 5090 24GB VRAM
- Development environment: Conda plus `env/requirements.txt`
- Pipeline configuration should be centralized in YAML files
- Long videos should be processed as segments, then merged or stitched offline
- Prefer deterministic, restartable stages over hidden mutable state

## Engineering Principles

- Keep module boundaries explicit: pipeline orchestration, detection, tracking, data contracts, export, and evaluation should stay separable.
- Use Pydantic v2 schemas for stage inputs and outputs.
- Prefer existing libraries for core CV logic: `ultralytics`, `sahi`, `torchreid`, `supervision`, `prefect`, `pyarrow`.
- Every pipeline stage should be idempotent. Re-running a failed stage must not corrupt previous outputs.
- Make outputs inspectable: save intermediate metadata, logs, and sample visualizations.
- Add focused tests for contracts, task behavior, and small end-to-end samples.
- Keep code clear and boring. Avoid large abstractions until duplication or complexity requires them.

## Directory Targets

Expected project shape:

```text
neylo/
├── AGENTS.md
├── PLAN_v2.md
├── configs/
│   └── pipeline.yaml
├── data/
├── docs/
│   ├── requirements/
│   └── decisions/
├── env/
│   ├── environment.yml
│   └── requirements.txt
├── neylo/
│   ├── pipeline/
│   ├── services/
│   │   ├── detection/
│   │   └── tracking/
│   ├── schemas/
│   └── evaluation/
├── docker/
└── tests/
```

## Requirement Files

Before implementing a module, read the matching requirement file:

- `docs/requirements/pipeline.md` for orchestration, decode, stages, export, and jobs
- `docs/requirements/detection.md` for YOLO11, SAHI, training, inference, and detection outputs
- `docs/requirements/tracking.md` for BoT-SORT, ReID, CMC, and offline tracklet stitching
- `docs/requirements/data.md` for raw data, annotations, splits, labels, and dataset layout
- `docs/requirements/evaluation.md` for KPIs, tests, metrics, and acceptance criteria
- `docs/decisions/architecture.md` for major architecture decisions and tradeoffs

## Acceptance Bar

A change is not complete unless it includes the relevant verification path:

- unit tests for schemas and pure logic
- smoke test on a short sample video when touching the pipeline
- exported sample Parquet and annotated MP4 when touching inference or tracking
- metric output when touching evaluation

