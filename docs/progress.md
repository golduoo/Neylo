# Neylo Implementation Progress

Living changelog of what has been built. Phase numbering follows
**`PLAN_v2.md` §12 推荐实现顺序** (the authoritative plan).

## Phase Overview

Plan was revised after Phase 1.2 to (a) reduce detector to single-class
`player` (data was severely imbalanced: keeper=33, referee=16,
another-player=131 vs player-white=41418), and (b) add an interactive
web UI as the primary v1 surface. Original PLAN_v2 phases shifted: data
+ training + tracking-stability moved to Phase 4–6; Phase 2 and 3 are
now Backend API and Frontend UI. Architecture is **precompute then
render** — upload → Phase 1 pipeline runs offline → UI fetches per-frame
results.

| Phase | Scope                                                        | Status        |
| ----- | ------------------------------------------------------------ | ------------- |
| 0     | 项目骨架: env, configs, Pydantic schemas, CLI                  | ✅ Done       |
| 1     | CLI 最小闭环: ingest → detect → track → Parquet + 帧/track 索引 | 🟡 In progress (1.1, 1.2 done) |
| **2** | **Backend API (FastAPI): upload / job status / frame & track queries** | ⏳ Pending |
| **3** | **Frontend Web UI (Vite + React + TS + Tailwind + shadcn/ui)** | ⏳ Pending  |
| 4     | 数据与训练: 单类 player 微调                                  | ⏳ Pending   |
| 5     | Tracking 稳定性: CMC + ReID 调参 + tracklet stitching         | ⏳ Pending   |
| 6     | 批处理与评估: 多 clip + 长片段 + tracking metrics              | ⏳ Pending   |
| 7     | 企业级扩展: Prefect + Postgres + MinIO + Docker + WebSocket    | ⏳ Pending   |

## Commit Timeline

| Commit    | Phase | Summary                                                    |
| --------- | ----- | ---------------------------------------------------------- |
| `b128863` | 0     | Project skeleton: dirs, env, configs, gitignore, tests     |
| `300900c` | 0     | Fix stale `PLAN.md` refs, env path, align to Phase numbers |
| `eddc6e1` | 0     | Pydantic schemas + CLI skeleton (28 tests pass)            |
| `b603776` | 0     | Update progress.md with current state and Phase 1 plan     |
| `c14d8fa` | 1.1   | Ingest + Decode (probe_video, FrameStream) — 39 tests pass |
| `545fbbe` | 1.2   | Detection adapter (YoloDetector + parse_results) — 48 tests pass |
| `c24824f` | plan  | Pivot: single-class `player`, add Backend API + Web UI as v1 surface |
| `a4572f3` | plan  | Lock external dataset; propagate single-class across all plan docs |
| `363f01a` | 1.3   | Detection end-to-end smoke: export.py + run.py + `neylo detect-only` — 61 tests pass |
| `2859307` | 1.4   | BoT-SORT tracking: configs/botsort.yaml + tracking service + `neylo track-only` — 75 tests pass |
| `1a1c3fb` | —     | Untrack stray test.py from previous commit |
| `493ebab` | 1.4   | Record GPU smoke results (8304 rows / 32 tracks / median 361 frames) |
| `3bc821e` | 1.5   | Track index: build_track_index + write_track_index — 84 tests pass |
| _next_    | 1.6   | Unified `neylo run`: detect+track in one inference pass + 3 artifacts — 87 tests pass |

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
  validation), `ClassName` enum (single `player` value; v1 is
  single-class — see plan pivot below)
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

### ✅ 1.2 Detection adapter

`neylo/services/detection/yolo.py`:

- `YoloConfig` — frozen dataclass mirroring `pipeline.yaml` `detection`
  section (model_path, device, conf, iou, imgsz, half).
- `build_class_map(model.names)` — auto-adapts: a fine-tuned model
  exposing a `player` class is mapped by name; otherwise (e.g. COCO
  pretrained) id 0 (`person`) → `player` and the rest are dropped.
  Phase 4 fine-tuning can drop in a new single-class model with no
  code change.
- `parse_results(xyxy, conf, cls, frame_info, class_map, ...)` — pure
  function turning raw YOLO arrays into `DetectionRecord[]`. Clamps
  out-of-bound boxes to the frame, drops degenerate boxes after clamp,
  raises on shape mismatch. Tested with hand-crafted numpy fixtures
  (no GPU, no model load).
- `YoloDetector(config)` — stateful wrapper. Loads weights eagerly in
  `__init__` (cost paid once per pipeline run), calls
  `model.predict(...)` on each frame, then delegates to
  `parse_results`. Exposes `detector_name`, `model_version`,
  `class_map` as read-only properties.

`configs/pipeline.yaml`: `detection.model_path` switched from
`models/yolo11x.pt` to `yolo11n.pt` for Phase 1 — bare name triggers
ultralytics auto-download. Will switch to `yolo11m`/`yolo11x` (with
SAHI enabled) after the pipeline is end-to-end working.

Tests in `tests/test_detection.py` (9): `build_class_map` strategies,
`parse_results` filtering / clamping / degenerate-drop / shape
mismatch. **No GPU dependency.**

### ✅ 1.3 Detection end-to-end (no tracking yet)

`neylo/pipeline/export.py`:

- `DETECTIONS_SCHEMA` — explicit pyarrow schema; columns match
  `DetectionRecord` 1:1, with `class_name` serialized as string for
  forward compatibility.
- `write_detections_parquet(records, path)` — materializes the iterable
  to a `pa.Table` with the explicit schema (works for empty input),
  writes via tmp-file + atomic rename, creates parent dirs as needed.
  Returns row count.

`neylo/pipeline/run.py`:

- `DetectorProtocol` — structural type so tests can pass a fake
  detector without importing ultralytics.
- `run_detection_only(asset, segment, detector)` — generator. Iterates
  `FrameStream`, yields the records `detector.detect()` returns per
  frame. Memory stays flat at one frame at a time.

`neylo/cli/main.py` adds `neylo detect-only`:

- `--input <video>`, `--config configs/pipeline.yaml`,
  `--output-dir outputs` (default)
- Probes asset, builds `single_segment`, constructs `YoloConfig` from
  `pipeline.yaml.detection`, instantiates `YoloDetector`, streams
  detections to `outputs/<video_id>/detections.parquet`
- Lazy imports `YoloDetector` so `neylo --version` and other
  subcommands stay fast and tests don't pull torch/ultralytics
  unless they need to.

Tests:

- `tests/test_export.py` (4): round-trip read, empty → empty Parquet
  with schema, parent-dir creation, no `.tmp` leftover.
- `tests/test_run.py` (3): per-frame yield count via fake detector,
  empty detector path, lazy-evaluation check.
- `tests/test_cli.py` (3 new): subcommand registered, missing input
  exits 2, missing `detection.model_path` exits 2.

**No GPU dependency in any unit test.** GPU verification is the manual
step below.

Total project test count: **61 pass**.

#### Manual GPU smoke (run in `cv_env`)

```bash
neylo detect-only \
  --input "data/Veo highlights ANUFC vs WEFC 23s/3 010545_-_Attack.mp4" \
  --config configs/pipeline.yaml
```

First run downloads `yolo11n.pt` (~5 MB) into the working directory.
Expected output: `outputs/3_010545_attack/detections.parquet` with
roughly `(visible_players_per_frame) × (n_frames)` rows. Inspect with:

```python
import pyarrow.parquet as pq
t = pq.read_table("outputs/3_010545_attack/detections.parquet")
print(t.num_rows, t.schema.names)
print(t.to_pandas().describe())
```

Sanity checks: row count is plausible, `conf` distribution is non-
trivial (not all 1.0 or 0.0), bboxes lie inside frame bounds, no nulls.

**1.3 GPU smoke result (recorded):** `3 010545_-_Attack.mp4`
(13s, 392 frames, 1920×1080, 29.97 fps) → 8304 rows
(~21.2 detections/frame, plausible for football scene). PNG overlay
confirmed boxes hug players; off-pitch false positives present but
expected for COCO-pretrained nano model.

### ✅ 1.4 BoT-SORT tracking

`configs/botsort.yaml` — v1 baseline:

- BoT-SORT with `gmc_method: sparseOptFlow` for camera motion
  compensation (required for Veo pan/tilt — see ADR-003)
- `track_buffer: 60` (~2s @ 30fps) for short-occlusion tolerance
- `with_reid: False` for Phase 1 baseline; ReID + appearance tuning
  is Phase 5 territory

`neylo/services/tracking/botsort.py`:

- `BotSortConfig` — frozen dataclass; shares `model_path` + inference
  knobs with `YoloConfig` because ultralytics couples det+track.
- `parse_track_results(...)` — pure function, mirrors
  `detection.parse_results` (clamp + degenerate drop) plus a track-id
  filter that drops detections without a confirmed track id (the
  tracker emits `id=None` or negative for unmatched boxes).
- `BotSortTracker` — stateful wrapper. Holds an ultralytics `YOLO`
  instance and calls `model.track(frame, persist=...)` per frame.
  `persist=False` on the first call (initialize tracker), `persist=
  True` thereafter. `reset()` exposed for manual re-initialization.

`neylo/pipeline/run.py`:

- `TrackerProtocol` — structural type so tests can pass a fake tracker.
- `run_tracking(asset, segment, tracker)` — generator; mirrors
  `run_detection_only` but yields `TrackRecord`.

`neylo/pipeline/export.py`:

- `TRACKS_SCHEMA` — pyarrow schema matching `TrackRecord`.
- `write_tracks_parquet(records, path)` — same atomic-write pattern
  as detections.

`neylo/cli/main.py`:

- New `neylo track-only --input <video>` subcommand. Same shape as
  `detect-only`; writes `outputs/<video_id>/tracks.parquet`.

`configs/pipeline.yaml`:

- Tracking section simplified to just `tracker` + `config_path`. The
  old aspirational ReID / CMC / stitching subsections were misleading
  — those knobs live in `configs/botsort.yaml` now, and stitching is
  Phase 5 work that doesn't need a config flag yet.

Tests (14 new):

- `tests/test_tracking.py` (8): `parse_track_results` empty / unmapped
  class drop / negative track id drop / clamp / degenerate drop /
  shape mismatch / full record fields / `run_tracking` per-frame yield
  via fake tracker.
- `tests/test_export.py` (3 added): tracks round-trip / empty tracks /
  stitched id round-trip.
- `tests/test_cli.py` (3 added): `track-only` parser registered,
  missing input → 2, missing `tracking.config_path` → 2.

**No GPU dependency in any unit test.** GPU verification is the
manual step below.

Total project test count: **75 pass**.

#### Manual GPU smoke (run in `cv_env`)

```bash
neylo track-only \
  --input "data/Veo highlights ANUFC vs WEFC 23s/3 010545_-_Attack.mp4" \
  --config configs/pipeline.yaml
```

Expected: `outputs/3_010545_attack/tracks.parquet`. Row count typically
slightly lower than `detections.parquet` (some detections have no
confirmed track id yet, especially in early frames). Sanity check:

```python
import pyarrow.parquet as pq
t = pq.read_table("outputs/3_010545_attack/tracks.parquet").to_pandas()
print("rows:", len(t), "frames:", t.frame_id.nunique(),
      "unique track ids:", t.track_id.nunique())
print(t.groupby("track_id").size().describe())  # track length distribution
```

Expect: 10–30 unique track ids on a busy football clip; longest tracks
last most of the clip; many short fragmented tracks if occlusions /
camera motion are heavy (the latter is what Phase 5 will tune away).

**1.4 GPU smoke result (recorded):** same `3 010545_-_Attack.mp4` clip:

- **8304 rows / 390 frames / 32 unique track ids**
- median track length: 361 frames (out of 390 — ~93% of the clip)
- top 10 track ids all ≥ 385 frames — i.e. main on-pitch players have
  fully stable identities throughout the clip
- min track length: 1 frame (transient false-positive "ghost" tracks)

Two observations:

- **No tracker warmup gap.** `track_high_thresh=0.25` /
  `new_track_thresh=0.25` are aggressive: every detection gets an id
  immediately. That's why row count matches detection-only almost
  exactly. Phase 5 may raise these thresholds to filter transient
  ids — at the cost of ~1–2 frames of latency on legitimate new
  tracks.
- **32 unique ids vs. ~23 expected on-pitch people.** The extra
  ~9 ids come from sideline people the COCO `person` class still
  matches (coaches, spectators). Phase 4 single-class fine-tuning
  on football-only data will cut these dramatically without
  touching the tracker.

### ✅ 1.5 Track index

`neylo/pipeline/export.py`:

- `build_track_index(records)` — pure function. Walks records once,
  groups by `track_id`, computes `first_frame` / `last_frame` /
  `first_timestamp_ms` / `last_timestamp_ms` / `n_frames` / `class`.
  Order-independent (uses min/max).
- `write_track_index(index, path)` — atomic JSON write. Track ids
  are stringified for JSON compatibility (no int keys in JSON).

The Phase 2 API uses this to satisfy `GET /api/v1/jobs/{id}/tracks`
without scanning the full Parquet. Frontend reads the whole file
once on entering the player screen (a few KB even for long videos).

Tests in `tests/test_export.py` (9 added): empty, single-track,
multi-frame, multi-track, order-independence, JSON round-trip,
parent-dir creation, no .tmp leftover, empty dict serialization.

### ✅ 1.6 Unified `neylo run`

Replaces the Phase 0 stub with the full pipeline. Architecture
decision: **single inference pass produces both detections and
tracks** — `BotSortTracker.track_and_detect` runs `model.track(...)`
once per frame and parses the result into both `DetectionRecord[]`
and `TrackRecord[]`. No double model load, no double GPU pass.

`neylo/services/tracking/botsort.py`:

- factored shared `_run_track(frame)` helper; old `track()` and new
  `track_and_detect()` both call it
- `track_and_detect()` reuses `parse_results` from the detection
  module (cross-service import is acceptable here because we are
  consciously combining the two outputs of one inference call)

`neylo/pipeline/run.py`:

- `CombinedTrackerProtocol` structural type
- `run_detect_and_track(asset, segment, tracker)` generator yielding
  `(detections, tracks)` per frame

`neylo/cli/main.py` `cmd_run`:

- validates input + `detection.model_path` + `tracking.config_path`
- loads `BotSortTracker` once
- accumulates detections + tracks in memory (Phase 1 short clips;
  streaming Parquet writes deferred to Phase 6)
- writes three artifacts:
  `outputs/<video_id>/detections.parquet`,
  `outputs/<video_id>/tracks.parquet`,
  `outputs/<video_id>/track_index.json`
- new `--output-dir` flag (defaults to `outputs/`)

Tests:

- `tests/test_cli.py` replaces the old "Phase 0 stub" test with two
  config-validation tests (missing `detection.model_path`, missing
  `tracking.config_path`).
- `tests/test_run.py` adds 2 new tests using a `_FakeCombinedTracker`
  (returns 2 detections + 1 track per frame): per-frame yield shape
  + full pipeline integration (writes all 3 artifacts to tmp_path,
  reads them back, verifies row counts and track index content).

Total project test count: **87 pass**.

#### Manual GPU smoke (Phase 1 acceptance)

```bash
neylo run \
  --input "data/Veo highlights ANUFC vs WEFC 23s/3 010545_-_Attack.mp4" \
  --config configs/pipeline.yaml
```

Expected three artifacts under `outputs/3_010545_attack/`:

- `detections.parquet` (~8300 rows, matches `detect-only` output)
- `tracks.parquet` (~8300 rows, matches `track-only` output)
- `track_index.json` (~32 entries — main on-pitch players + sideline
  false positives from COCO `person`)

If counts roughly match the standalone `detect-only` and `track-only`
runs from 1.3 / 1.4 GPU smokes, **Phase 1 is complete** and the
foundation for Phase 2 (Backend API) and Phase 3 (Web UI) is in place.



End-to-end shortest path on a single 10–20 s clip:
**ingest → decode → detect → track → export**.

Planned breakdown (each step independently runnable + testable):

| Step | Scope                                                                            | Output                                                |
| ---- | -------------------------------------------------------------------------------- | ----------------------------------------------------- |
| 1.1  | Ingest + Decode: probe `VideoAsset`, frame iterator (OpenCV) ✅                  | `VideoAsset` + `FrameInfo` stream                     |
| 1.2  | Detection service: ultralytics YOLO11 wrapper ✅                                 | `DetectionRecord[]` per frame                         |
| 1.3  | Detection end-to-end smoke (no tracking yet): export + runner + CLI ✅           | `outputs/<video_id>/detections.parquet`               |
| 1.4  | Tracking service: BoT-SORT via ultralytics, `configs/botsort.yaml` ✅            | `outputs/<video_id>/tracks.parquet`                   |
| 1.5  | Track index: `build_track_index` + `write_track_index` ✅                        | `outputs/<job>/track_index.json` for fast UI/API lookup |
| 1.6  | Unified `neylo run`: single-pass detect+track → 3 artifacts ✅                   | working `neylo run --input <clip>`                    |

**Phase 1 entry-costs:**

- YOLO11 weights download (~40–250 MB, into `models/`, gitignored — first run downloads automatically via ultralytics)
- Write `configs/botsort.yaml` (BoT-SORT params, ReID + CMC toggles)

**Note on the plan pivot (post-1.2):**

- v1 detector is now **single-class `player`** (data-driven; see PLAN_v2 §3.5). Goalkeeper / referee removed from `ClassName` enum, configs, and tests; 48 tests still green after the change.
- v1 deliverable is now **interactive web UI** (Phase 3) backed by **FastAPI** (Phase 2). Annotated MP4 from 1.4 is demoted to an optional CLI flag — the UI will render overlays on the original video using per-frame Parquet queries instead.
- All Phase 1 work remains valid and is the foundation for Phase 2/3.
