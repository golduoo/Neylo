# Detection Requirements

## Purpose

Detection identifies on-field people in each frame so the tracking
stage can assemble per-player tracks. v1 is single-class — see
`docs/requirements/data.md` and PLAN_v2 §3.5 for the data-driven
justification.

## Owner

Shiyu

## Classes

v1 produces a single class:

- `player`

v2 targets (out of scope):

- `ball` (separate small-object model with SAHI)
- role discrimination such as `goalkeeper` and `referee` (deferred until
  data supports it)

Class names are defined exactly once in `neylo.schemas.ClassName`. The
training dataset uses richer source labels which are merged at training
time per `docs/requirements/data.md`.

## Baseline

First milestone (Phase 1.3 detection smoke):

- use COCO pretrained `yolo11n.pt` (auto-downloaded by ultralytics on
  first call)
- run inference on a Veo highlight clip end to end
- produce `DetectionRecord` rows and a `detections.parquet` file
- visual sanity check: bounding boxes look plausible on overlay

This baseline does not need any fine-tuning or external dataset; it
exercises the GPU + parquet plumbing only.

## Fine-Tuning Plan (Phase 4)

Target model: `yolo11m` or `yolo11l` fine-tuned on the locked external
dataset (see `docs/requirements/data.md` §B):

- source: Roboflow `ball-player-gk-scoreboard-ref`, ~11k images
- mixed Veo and broadcast domain
- merged to single `player` class at training time

Training flow:

1. Verify local copy under `data/external/ball-player-gk-scoreboard-ref/`
   matches expected layout (`data.yaml`, `train/`, `valid/`, `test/`).
2. Apply class re-mapping per `docs/requirements/data.md`:
   `player` and `goalkeeper` → `player`; drop `ball` and `scoreboard`.
3. Train with the dataset's provided `train` / `valid` split.
4. Evaluate on the dataset's `test` split.
5. Optionally do a second-stage fine-tune on a small hand-labeled Veo
   subset (200–500 frames) if validation shows a domain gap.
6. Export TensorRT FP16 engine when model quality is acceptable.

Recommended training command (subject to revision in Phase 4):

```bash
yolo detect train model=yolo11m.pt data=data/external/.../data.yaml \
  imgsz=1280 epochs=100 batch=16 patience=20 \
  hsv_h=0.02 hsv_s=0.7 hsv_v=0.5 fliplr=0.0 \
  mosaic=1.0 close_mosaic=10 device=0
```

## Inference

Default inference (configured via `configs/pipeline.yaml`):

- image size: 1280
- confidence threshold: configurable, default 0.25
- device: CUDA when available
- output: `neylo.schemas.DetectionRecord`, not raw ultralytics objects

SAHI inference:

- not used in v1 (single-class player detection at imgsz 1280 is
  sufficient on RTX 5090)
- enable in v2 for ball detection (small distant target)
- starting config: `slice_size=640`, `overlap_ratio=0.2`

## Output Contract

Each detection includes:

```text
video_id, segment_id, frame_id, timestamp_ms,
class_name, conf, x1, y1, x2, y2, detector_name, model_version
```

Coordinates are pixel-space xyxy. Out-of-bound boxes are clamped to the
frame; degenerate boxes after clamp are dropped (see
`neylo.services.detection.yolo.parse_results`).

## Quality Targets

Initial v1 targets (single-class):

- player mAP@0.5 greater than 0.90 on the held-out `test` split of the
  external dataset
- player mAP@0.5 greater than 0.85 on a small hand-labeled Veo holdout
  (added late in Phase 4 if domain gap is observed)
- false positives on background spectators, trees, flags, or field
  markings reviewed manually

Ball recall is not a v1 metric.

## Known Risks

- Veo highlight clips overrepresent the penalty area; midfield is
  underrepresented
- distant players are small targets, especially in wide Veo shots
- outdoor shadow and exposure shifts reduce robustness
- TV broadcast portion of the training set has different camera
  characteristics from Veo (sim-to-real gap)

## Mitigations

- request additional Veo midfield/buildup clips from the company
- include hard negative background samples during fine-tuning
- use HSV augmentation
- split train / val by video, not by frame
- consider a second-stage Veo-only fine-tune if domain gap is seen on
  the Veo holdout

## Testing

Required tests:

- conversion from YOLO outputs to `DetectionRecord`
  (`tests/test_detection.py`)
- class-name mapping including the COCO fallback path
- coordinate clamping to frame bounds; degenerate-after-clamp drop

Manual verification (Phase 1.3 smoke):

- run `neylo detect-only` on at least one short Veo clip
- inspect `outputs/<video_id>/detections.parquet` row count and
  confidence distribution
- render an overlay video and review for obvious failure cases
