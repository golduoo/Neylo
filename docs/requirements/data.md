# Data Requirements

## Purpose

Defines how Neylo v1 organizes video, frame, annotation, training, and
output data. This file is the source of truth for dataset versions and
class merging — code and configs must agree with what is stated here.

## v1 Class Schema

v1 has a **single detector class: `player`**. See PLAN_v2 §3.5 for the
data-driven justification (severe label imbalance, sparse non-player
classes). Code reflects this in `neylo.schemas.ClassName` and
`neylo.services.detection.yolo.build_class_map`.

## Data Inventory

### A. Neylo Veo data (own, unlabeled)

- 4 ANUFC matches against opponents
- Veo-style camera (single elevated wide angle, AI pan-tilt simulation)
- ~20–30 highlight clips per match, ~10–20 s each
- Total: ~80–100 short clips
- **All currently unlabeled.** Used as inference targets and as a
  small future hand-labeled holdout for final tuning.
- Limitations: highlights overrepresent penalty-area attacks; midfield,
  buildup, throw-ins, corners are underrepresented.

### B. External training dataset (locked)

| Field | Value |
| --- | --- |
| Slug | `ball-player-gk-scoreboard-ref` |
| Source | Roboflow Universe (downloaded locally by Xiwen) |
| Image count | ~11000 |
| Source classes | `ball`, `player`, `goalkeeper`, `scoreboard` (4) |
| Format | YOLO (Roboflow export) |
| License | Commercial use permitted (confirmed by Xiwen, 2026-05-07) |
| Domain mix | Veo-style and TV broadcast (mixed) |
| Local path | `data/external/ball-player-gk-scoreboard-ref/` (see "Layout" below) |

The mixed domain (Veo + broadcast) is desirable for generalization but
implies a residual sim-to-real gap on Veo footage. Plan to do a final
small-scale hand-label pass on Veo clips (~200–500 frames) in late
Phase 4 if validation shows the gap matters.

### v1 Class Re-mapping

When training on dataset B, classes are remapped to the single v1
class:

| Source class | v1 mapping |
| --- | --- |
| `player` | → `player` |
| `goalkeeper` | → `player` (merged) |
| `ball` | dropped (deferred to v2 small-object model) |
| `scoreboard` | dropped (out of v1 scope) |

The remap is implemented as a preprocessing step that rewrites the YOLO
label files (or via an ultralytics dataset YAML override) when
training begins in Phase 4. No code remap is needed at inference time —
`build_class_map` reads model class names; if the trained model exposes
a single `player` class, mapping is direct.

## Local Layout

```text
data/                              # root (gitignored)
├── Veo highlights ANUFC vs ...    # raw match clips, do not modify
├── external/                      # third-party datasets
│   └── ball-player-gk-scoreboard-ref/
│       ├── data.yaml              # Roboflow's class/path manifest
│       ├── train/
│       │   ├── images/
│       │   └── labels/
│       ├── valid/
│       │   ├── images/
│       │   └── labels/
│       └── test/
│           ├── images/
│           └── labels/
└── derived/                       # produced by pipeline / training
    ├── frames/                    # extracted frames for labeling (Phase 4)
    ├── datasets/                  # remapped + merged training set (Phase 4)
    └── outputs/                   # Phase 1 pipeline outputs (Parquet)
```

`data/` and everything under it stays local-only (gitignored). Raw
videos and the external dataset are not committed to the repo.

## Frame Extraction (Phase 4)

For any future hand-labeling on Veo footage:

- extract around 1 fps as labeling candidates
- preserve source video path, frame index, and timestamp
- remove near-duplicate frames with perceptual hashing
- expected pool size: ~1500–2000 candidates after dedup

## Annotation (Phase 4, optional)

If a Veo hand-labeling pass becomes necessary:

- use CVAT locally
- the only required label is `player`
- label visible body extent
- ambiguous far people stay `player` (single-class — no goalkeeper /
  referee distinction)

## Dataset Splits

Split by video or match, not by individual frame, to avoid leakage
from temporally adjacent frames. For dataset B, use Roboflow's
provided `train` / `valid` / `test` split as-is.

## Pseudo Labeling

Pseudo labels can accelerate any later Veo labeling pass:

- run the Phase 4 baseline model with `conf=0.3`
- import predictions into CVAT
- manually correct
- pseudo labels are not ground truth until reviewed

## Versioning Discipline

For every training run, record:

- dataset slug + Roboflow version hash (or local checksum)
- source videos included (if mixing Veo)
- annotation date / source
- label schema version (this file's commit hash is acceptable)
- train / val / test split file or Roboflow export id
- the model checkpoint produced

Recorded inside `outputs/<run_id>/training_run.json` (Phase 4).

## Testing

Required checks:

- annotation class names after remap match `ClassName` enum (only
  `player`)
- YOLO dataset YAML points to paths that exist
- train / val split does not mix frames from the same source video
  unless explicitly allowed
- all bounding boxes inside image bounds
- ball / scoreboard / goalkeeper labels were correctly handled by the
  remap step (drop / merge)

## Data Requests (open)

Ask the company for:

- 1–2 full match videos
- or representative Veo clips from midfield transitions, throw-ins,
  corners, defensive buildup

These cover the deployment distribution in ways the highlight clips do
not.
