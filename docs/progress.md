# Neylo Implementation Progress

Living changelog of what has been built. Phase numbering follows
**`PLAN_v2.md` §12 推荐实现顺序** (the authoritative plan).

## Phase Overview

| Phase | Scope                                              | Status      |
| ----- | -------------------------------------------------- | ----------- |
| 0     | 项目骨架: env, configs, Pydantic schemas, CLI       | ✅ Done     |
| 1     | 最小闭环: YOLO + BoT-SORT + Parquet + annotated MP4 | ⏳ Next     |
| 2     | 数据与训练: 抽帧 / 伪标注 / CVAT / 训练 / 评估       | ⏳ Pending  |
| 3     | Tracking 稳定性: CMC + ReID 调参 + tracklet 拼接     | ⏳ Pending  |
| 4     | 批处理与评估: 多 clip + 长片段 + tracking metrics    | ⏳ Pending  |
| 5     | 企业级扩展: Prefect + Postgres + MinIO + Docker      | ⏳ Pending  |

## Commit Timeline

| Commit    | Phase | Summary                                                    |
| --------- | ----- | ---------------------------------------------------------- |
| `b128863` | 0     | Project skeleton: dirs, env, configs, gitignore, tests     |
| `300900c` | 0     | Fix stale `PLAN.md` refs, env path, align to Phase numbers |
| `eddc6e1` | 0     | Pydantic schemas + CLI skeleton (28 tests pass)            |
| `b603776` | 0     | Update progress.md with current state and Phase 1 plan     |
| _next_    | 1.1   | Ingest + Decode (probe_video, FrameStream) — 39 tests pass |

---

## Phase 0 — 项目骨架 (done)

**Goal (per PLAN_v2 §12):** `env/requirements.txt`, `configs/pipeline.yaml`,
Pydantic schemas, and CLI skeleton.

### Directory tree (current)

```text
neylo/
├── AGENTS.md
├── PLAN_v2.md
├── pyproject.toml             # neylo CLI entry point + pytest/ruff config
├── .gitignore                 # excludes data/, models/, outputs/, .claude/
├── configs/
│   └── pipeline.yaml
├── data/                      # local-only, gitignored
├── docker/Dockerfile          # placeholder, finalized in Phase 5
├── docs/
│   ├── decisions/architecture.md
│   ├── requirements/{data,detection,evaluation,pipeline,tracking}.md
│   └── progress.md            # this file
├── env/
│   ├── environment.yml        # name: cv_env, torch excluded
│   └── requirements.txt
├── neylo/
│   ├── __init__.py            # __version__ = "0.1.0"
│   ├── cli/
│   │   ├── __init__.py
│   │   └── main.py            # `neylo run` / `run-batch` (stub)
│   ├── pipeline/__init__.py
│   ├── schemas/
│   │   ├── __init__.py        # re-exports all models
│   │   ├── common.py          # BBox, ClassName
│   │   ├── video.py           # VideoAsset, VideoSegment, FrameInfo
│   │   ├── detection.py       # DetectionRecord
│   │   ├── track.py           # TrackRecord
│   │   └── run.py             # StageStatus, StageRun, PipelineRun
│   ├── services/
│   │   ├── detection/__init__.py
│   │   └── tracking/__init__.py
│   └── evaluation/__init__.py
└── tests/
    ├── conftest.py            # project_root / configs_dir / data_dir fixtures
    ├── test_skeleton.py       # 3 tests: package + config + subpackages
    ├── test_schemas.py        # 20 tests: validation, JSON round-trip, enums
    └── test_cli.py            # 5 tests: CLI parsing + stub behavior
```

### Pydantic v2 schemas

Modules in `neylo/schemas/`, all re-exported from the package root:

- `common.py` — `BBox` (frozen, with `width`/`height`/`area` and order
  validation), `ClassName` enum (`player`, `goalkeeper`, `referee`)
- `video.py` — `VideoAsset`, `VideoSegment`, `FrameInfo`
- `detection.py` — `DetectionRecord` per PLAN_v2 §6.1
  (video/segment/frame ids, timestamp, class, conf, x1/y1/x2/y2,
  detector_name, model_version)
- `track.py` — `TrackRecord` per PLAN_v2 §6.2 (adds `track_id`,
  `source_track_id`, optional `stitched_track_id`, `tracker_name`)
- `run.py` — `StageStatus` enum, `StageRun` (idempotency key:
  `video_id/segment_id/stage_name/config_hash/model_version`),
  `PipelineRun`

All models use `ConfigDict(extra="forbid")` so unknown fields fail loudly.

### CLI skeleton

`neylo/cli/main.py` with stdlib `argparse` (no extra deps), wired in
`pyproject.toml` as `[project.scripts] neylo = "neylo.cli.main:app"`.

- `neylo run --input <video> [--config configs/pipeline.yaml]`
- `neylo run-batch --input-dir <dir> [--config configs/pipeline.yaml]`
- `neylo --version`

Phase 0 stubs only validate inputs and echo the planned stage chain;
real detect/track wiring lands in Phase 1.

### Conventions established

- Python 3.11 inside conda env `cv_env`. **Do not run on system
  Python 3.12.7.**
- PyTorch is manually installed (`torch 2.11.0+cu130`, RTX 5090 CUDA
  build). `requirements.txt` intentionally does not pin `torch`.
- Module boundary: `pipeline` orchestrates; `services/{detection,tracking}`
  hold the CV logic; `schemas` owns Pydantic data contracts; `evaluation`
  hosts metrics. No cross-imports between sibling services.
- Config read from `configs/pipeline.yaml`; no values hardcoded in code.
- Outputs land under `outputs/` (gitignored). Models under `models/`
  (gitignored).
- Pytest markers: `smoke` (sample-video end-to-end), `slow` (GPU/large
  fixtures).

### Open items / deferred

- **`models/` directory not created yet.** Will be added when Phase 1
  step 1.2 needs YOLO11 weights (downloaded by ultralytics on first
  run).
- **`configs/botsort.yaml` is referenced by `pipeline.yaml`
  (`tracking.config_path`) but not written yet.** Must be created in
  Phase 1 step 1.3 (tracking integration). Until then any code path
  that loads the tracker config will fail. Treated as a known
  entry-cost.

### Verification (run inside `cv_env`)

```bash
conda activate cv_env
pip install -r env/requirements.txt
pip install -e .
pytest -v
neylo --version
```

Expected: **28 tests pass** (3 skeleton + 20 schemas + 5 CLI),
and `neylo --version` prints `neylo 0.1.0`.

---

## Phase 1 — 最小闭环 (in progress)

### ✅ 1.1 Ingest + Decode

`neylo/pipeline/ingest.py`:

- `probe_video(path) → VideoAsset` — uses `cv2.VideoCapture` to read
  fps / width / height / frame count, fails loudly on bad metadata
- `discover_videos(root, extensions) → list[Path]` — recursive scan,
  sorted, filtered by extension
- `make_video_id(path)` — slug from filename stem
  (`"01 001124_-_Shot_on_goal.mp4"` → `"01_001124_shot_on_goal"`)

`neylo/pipeline/decode.py`:

- `single_segment(asset) → VideoSegment` — Phase 1 treats whole video
  as one segment; real 1–2 minute segmentation deferred to Phase 4
- `FrameStream(asset, segment)` — context manager iterating
  `(bgr_ndarray, FrameInfo)`. Validates video_id match between asset
  and segment, releases `cv2.VideoCapture` on exit, refuses use
  outside `with` block.

Tests in `tests/test_ingest.py` (6) and `tests/test_decode.py` (5) use
a synthetic `cv2.VideoWriter` mp4 fixture (no dependency on `data/`).
Total project test count: **39 pass**.



End-to-end shortest path on a single 10–20 s clip:
**ingest → decode → detect → track → export**.

Planned breakdown (each step independently runnable + testable):

| Step | Scope                                                                | Output                                       |
| ---- | -------------------------------------------------------------------- | -------------------------------------------- |
| 1.1  | Ingest + Decode: probe `VideoAsset`, frame iterator (OpenCV) ✅      | `VideoAsset` + `FrameInfo` stream            |
| 1.2  | Detection service: ultralytics YOLO11 wrapper                        | `DetectionRecord[]` per frame                |
| 1.3  | Tracking service: BoT-SORT via ultralytics, `configs/botsort.yaml`   | `TrackRecord[]` per frame                    |
| 1.4  | Export: pyarrow Parquet writer + supervision MP4 annotator           | `outputs/<video_id>/{tracks.parquet,vis.mp4}`|
| 1.5  | CLI wiring: replace `neylo run` stub with the 1.1–1.4 chain          | working `neylo run --input <clip>`           |
| 1.6  | Smoke test on a real Veo highlight clip from `data/`                 | acceptance: ≥99% frame coverage, MP4 plays   |

Phase 1 entry-costs:

- YOLO11 weights download (~40–250 MB, into `models/`, gitignored)
- Write `configs/botsort.yaml` (BoT-SORT params, ReID + CMC toggles)
