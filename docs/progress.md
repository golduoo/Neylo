# Neylo Implementation Progress

Living changelog of what has been built. Phase numbering follows
**`PLAN_v2.md` §12 推荐实现顺序** (the authoritative plan). Earlier
drafts of this file used a different "Stage" numbering — that is
deprecated.

## Phase Overview

| Phase | Scope                                              | Status        |
| ----- | -------------------------------------------------- | ------------- |
| 0     | 项目骨架: env, configs, Pydantic schemas, CLI     | ✅ Done       |
| 1     | 最小闭环: YOLO + BoT-SORT + Parquet + annotated MP4 | ⏳ Pending    |
| 2     | 数据与训练: 抽帧 / 伪标注 / CVAT / 训练 / 评估       | ⏳ Pending    |
| 3     | Tracking 稳定性: CMC + ReID 调参 + tracklet 拼接     | ⏳ Pending    |
| 4     | 批处理与评估: 多 clip + 长片段 + tracking metrics    | ⏳ Pending    |
| 5     | 企业级扩展: Prefect + Postgres + MinIO + Docker      | ⏳ Pending    |

---

## Phase 0 — 项目骨架 (done)

**Goal (per PLAN_v2 §12):** `env/requirements.txt`, `configs/pipeline.yaml`,
Pydantic schemas, and CLI skeleton.

### ✅ Done

#### Directory tree

Matches the target shape in `AGENTS.md`:

```text
neylo/
├── AGENTS.md
├── PLAN_v2.md
├── pyproject.toml
├── .gitignore
├── configs/
│   └── pipeline.yaml
├── data/                       # local-only, gitignored
├── docs/
│   ├── decisions/architecture.md
│   ├── requirements/{data,detection,evaluation,pipeline,tracking}.md
│   └── progress.md             # this file
├── docker/Dockerfile           # placeholder, finalized in Phase 5
├── env/
│   ├── environment.yml
│   └── requirements.txt
├── neylo/
│   ├── __init__.py
│   ├── pipeline/__init__.py
│   ├── schemas/__init__.py     # empty — to be filled in Phase 0
│   ├── services/
│   │   ├── detection/__init__.py
│   │   └── tracking/__init__.py
│   └── evaluation/__init__.py
└── tests/
    ├── conftest.py
    └── test_skeleton.py
```

#### Key files

- `env/environment.yml` — Conda env (Python 3.11, ffmpeg, pip layer).
  Pip section uses `-r env/requirements.txt` (repo-root-relative; assumes
  `conda env create -f env/environment.yml` is run from repo root).
- `env/requirements.txt` — pinned core deps:
  `ultralytics`, `sahi`, `torchreid`, `supervision`, `prefect`, `pyarrow`,
  `pandas`, `numpy`, `opencv-python`, `pydantic>=2.9`, `pyyaml`, `loguru`,
  `tqdm`, `pytest`, `pytest-cov`.
- `configs/pipeline.yaml` — central tunables; sections:
  `paths`, `ingest`, `decode`, `detection` (incl. SAHI), `tracking`
  (BoT-SORT + ReID + CMC + offline stitching), `export`, `runtime`.
- `pyproject.toml` — package metadata (`requires-python = ">=3.11"`),
  pytest config, ruff config.
- `.gitignore` — Python artifacts, model weights, `runs/`, `outputs/`,
  entire `data/` directory, `.claude/`.
- `docker/Dockerfile` — placeholder targeting CUDA 12.4 + ffmpeg + RTX
  5090 (finalized in Phase 5).
- `tests/conftest.py` — exposes `project_root`, `configs_dir`, `data_dir`
  fixtures.
- `tests/test_skeleton.py` — verifies package imports, subpackages
  exist, `pipeline.yaml` parses with all required top-level keys.

#### Conventions established

- Python ≥ 3.11. **Do not run on system 3.12.7** — use the conda env.
- Module boundary: `pipeline` orchestrates; `services/{detection,tracking}`
  hold the CV logic; `schemas` owns Pydantic data contracts; `evaluation`
  hosts metrics. No cross-imports between sibling services.
- Config read from `configs/pipeline.yaml`; no values hardcoded in code.
- Outputs land under `outputs/` (gitignored). Models under `models/`
  (gitignored).
- Pytest markers: `smoke` (sample-video end-to-end), `slow` (GPU/large
  fixtures).

### ✅ Pydantic v2 schemas

Modules in `neylo/schemas/`, all re-exported from the package root:

- `common.py` — `BBox` (frozen, with `width`/`height`/`area` and order
  validation), `ClassName` enum (`player`, `goalkeeper`, `referee`)
- `video.py` — `VideoAsset`, `VideoSegment`, `FrameInfo`
- `detection.py` — `DetectionRecord` (PLAN_v2 §6.1: video/segment/frame
  ids, timestamp, class, conf, x1/y1/x2/y2, detector_name, model_version)
- `track.py` — `TrackRecord` (PLAN_v2 §6.2: adds track_id,
  source_track_id, optional stitched_track_id, tracker_name)
- `run.py` — `StageStatus` enum, `StageRun` (idempotency key:
  video_id/segment_id/stage_name/config_hash/model_version),
  `PipelineRun`

All models use `ConfigDict(extra="forbid")` so unknown fields fail loudly.
Tests in `tests/test_schemas.py` cover bbox validation, conf bounds, enum
coercion, JSON round-trip, and unknown-field rejection.

### ✅ CLI skeleton

`neylo/cli/main.py` with stdlib `argparse` (no extra deps), wired in
`pyproject.toml` as `[project.scripts] neylo = "neylo.cli.main:app"`.

- `neylo run --input <video> [--config configs/pipeline.yaml]`
- `neylo run-batch --input-dir <dir> [--config configs/pipeline.yaml]`
- `neylo --version`

Phase 0 stubs only validate inputs and echo the planned stage chain;
real detect/track wiring lands in Phase 1. Tests in `tests/test_cli.py`
cover argument parsing, missing-input error path, and batch discovery.

### Open items / deferred

- **Conda env `cv_env` is created** with Python 3.11 and a manually
  installed GPU-matched PyTorch (`torch 2.11.0+cu130`,
  `torch.cuda.is_available() == True` on RTX 5090). All project work
  runs inside `cv_env`; do **not** use system Python 3.12.7.
  Project deps install with `pip install -r env/requirements.txt`
  followed by `pip install -e .` from the repo root. `requirements.txt`
  intentionally does not pin `torch` so the manual CUDA-matched build
  stays in place.
- `models/` directory not created yet; will be added when Phase 1 needs
  YOLO11 weights.
- `configs/botsort.yaml` is referenced by `pipeline.yaml`
  (`tracking.config_path`) but not written yet. Must be created when
  tracker integration starts (Phase 1 / Phase 3) — until then any code
  path that loads the tracker config will fail. Treated as a known
  entry-cost.

### Verification

Once a Conda env is created and deps installed:

```bash
conda activate cv_env
pip install -r env/requirements.txt
pip install -e .
pytest tests/test_skeleton.py -v
```

Expected: 3 passing tests (package importable, config loads, subpackages
present). Schema and CLI tests will be added as the remaining Phase 0
work lands.

---

## Phase 1 — 最小闭环 (next, after Phase 0 schemas + CLI)

End-to-end shortest path:

- input single video → YOLO inference → BoT-SORT tracking → Parquet +
  annotated MP4
- run on a 10–20 s sample clip to confirm shape and frame coverage
