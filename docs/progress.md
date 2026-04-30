# Neylo Implementation Progress

Living changelog of what has been built, by stage. Each stage maps to the
implementation plan in `AGENTS.md`.

## Stage Overview

| Stage | Module                     | Status      |
| ----- | -------------------------- | ----------- |
| 0     | Project skeleton           | ✅ Done     |
| 1     | Schemas (Pydantic v2)      | ⏳ Pending  |
| 2     | Pipeline orchestration     | ⏳ Pending  |
| 3     | Detection service          | ⏳ Pending  |
| 4     | Tracking service           | ⏳ Pending  |
| 5     | Export (Parquet + MP4)     | ⏳ Pending  |
| 6     | Evaluation                 | ⏳ Pending  |
| 7     | Docker / packaging         | ⏳ Pending  |

---

## Stage 0 — Project Skeleton

**Goal:** lay down directory structure, env spec, central config, package
boilerplate, and a minimal test harness so later stages have a stable scaffold.

### Directory tree

Matches the target shape in `AGENTS.md`:

```text
neylo/
├── AGENTS.md
├── PLAN.md
├── pyproject.toml
├── .gitignore
├── configs/
│   └── pipeline.yaml
├── data/                       # raw videos (gitignored)
├── docs/
│   ├── decisions/
│   │   └── architecture.md
│   ├── requirements/
│   │   ├── data.md
│   │   ├── detection.md
│   │   ├── evaluation.md
│   │   ├── pipeline.md
│   │   └── tracking.md
│   └── progress.md             # this file
├── docker/
│   └── Dockerfile              # placeholder, finalized in stage 7
├── env/
│   ├── environment.yml
│   └── requirements.txt
├── neylo/
│   ├── __init__.py
│   ├── pipeline/__init__.py
│   ├── schemas/__init__.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── detection/__init__.py
│   │   └── tracking/__init__.py
│   └── evaluation/__init__.py
└── tests/
    ├── __init__.py
    ├── conftest.py
    └── test_skeleton.py
```

### Key files

- `env/environment.yml` — Conda env (Python 3.11, ffmpeg, pip layer)
- `env/requirements.txt` — pinned core deps:
  `ultralytics`, `sahi`, `torchreid`, `supervision`, `prefect`, `pyarrow`,
  `pandas`, `numpy`, `opencv-python`, `pydantic>=2.9`, `pyyaml`, `loguru`,
  `tqdm`, `pytest`, `pytest-cov`
- `configs/pipeline.yaml` — central tunables; sections:
  `paths`, `ingest`, `decode`, `detection` (incl. SAHI), `tracking`
  (BoT-SORT + ReID + CMC + offline stitching), `export`, `runtime`
- `pyproject.toml` — package metadata, pytest config, ruff config
- `.gitignore` — Python artifacts, model weights (`*.pt`, `*.onnx`,
  `*.engine`), `runs/`, `outputs/`, video files under `data/`
- `docker/Dockerfile` — placeholder targeting CUDA 12.4 + ffmpeg + RTX 5090
- `tests/conftest.py` — exposes `project_root`, `configs_dir`, `data_dir`
  fixtures
- `tests/test_skeleton.py` — verifies package imports, subpackages exist,
  and `pipeline.yaml` parses with all required top-level keys

### Conventions established

- Python ≥ 3.11
- Module boundary: `pipeline` orchestrates; `services/{detection,tracking}`
  hold the CV logic; `schemas` owns Pydantic data contracts; `evaluation`
  hosts metrics and acceptance scripts. No cross-imports between sibling
  services.
- Config is read from `configs/pipeline.yaml`; no values hardcoded in code.
- Outputs land under `outputs/` (gitignored). Models under `models/`
  (gitignored).
- Pytest markers: `smoke` (sample-video end-to-end), `slow` (GPU/large
  fixtures).

### Verification

Once a Conda env is created and deps installed:

```bash
conda env create -f env/environment.yml
conda activate neylo
pip install -e .
pytest tests/test_skeleton.py -v
```

Expected: 3 passing tests (package importable, config loads, subpackages
present).

### Open items / deferred

- Conda env not yet created on this machine — deferred until the user
  confirms dependency list.
- `models/` directory not created yet; will be added when stage 3
  (detection) needs YOLO11 weights.
- `configs/botsort.yaml` referenced by `pipeline.yaml` but not yet
  written; will land in stage 4 (tracking).

---

## Stage 1 — Schemas (next)

Will define Pydantic v2 models in `neylo/schemas/`:

- `VideoAsset`, `VideoSegment`, `FrameInfo`
- `DetectionRecord`, `TrackRecord`
- `StageRun`, `PipelineRun`, `JobConfig`

`TrackRecord` minimum fields per `docs/requirements/pipeline.md`:
`video_id, segment_id, frame_id, timestamp_ms, track_id, class_name, conf,
x1, y1, x2, y2, source`.

Acceptance: unit tests for serialization, validation, round-trip through
JSON / dict.
