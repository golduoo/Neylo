# Detection Requirements

## Purpose

Detection identifies football players, goalkeepers, referees, and the ball in each frame.

v1 prioritizes reliable player detection because tracking quality depends on detection quality.

## Owner

Shiyu

## Classes

Use exactly these class names in v1:

- `player`
- `goalkeeper`
- `referee`

v2 target (not in v1):

- `ball`

Class IDs should be configured in the dataset YAML and mirrored in code constants.

## Baseline

First milestone:

- use `yolo11x.pt` or another YOLO11 model to run inference end to end
- produce detection records compatible with the tracking module
- render a simple annotated debug video for manual review

## Fine-Tuning Plan

Target model:

- YOLO11l fine-tuned from SoccerNet-pretrained weights if available
- fallback: YOLO11l or YOLO11x pretrained weights

Training flow:

1. Extract frames at about 1 fps from existing Veo clips.
2. Remove near-duplicates with perceptual hashing.
3. Generate pseudo labels with a baseline model.
4. Correct labels manually in CVAT.
5. Train with video-level train/val split to avoid leakage.
6. Review low-confidence and high-error samples.
7. Iterate active learning for 2-3 rounds.
8. Export TensorRT FP16 engine when model quality is acceptable.

Recommended training command:

```bash
yolo detect train model=yolo11l_soccernet.pt data=data.yaml \
  imgsz=1280 epochs=100 batch=8 patience=20 \
  hsv_h=0.02 hsv_s=0.7 hsv_v=0.5 fliplr=0.0 \
  mosaic=1.0 close_mosaic=10 device=0
```

## Inference

Default inference:

- image size: 1280
- confidence threshold: configurable
- device: CUDA when available
- output: normalized internal `DetectionRecord`, not library-specific objects

SAHI inference:

- use for small distant players and ball detection
- starting config: `slice_size=640`, `overlap_ratio=0.2`
- preserve frame coordinates after merging sliced predictions

## Output Contract

Each detection must include:

```text
video_id, segment_id, frame_id, timestamp_ms,
class_name, conf, x1, y1, x2, y2, detector_name, model_version
```

Coordinates use pixel-space xyxy format.

## Quality Targets

Initial v1 targets:

- player mAP@0.5 greater than 0.90 on validation clips
- ball recall greater than 0.70
- false positives on background spectators, trees, flags, or field markings should be reviewed manually

## Known Risks

- existing clips are mostly highlights near the penalty area
- midfield samples are underrepresented
- distant ball and distant players are small targets
- outdoor shadows and exposure changes may reduce robustness

## Mitigations

- request 1-2 full match videos or representative midfield clips
- include hard negative background samples during fine-tuning
- use HSV augmentation
- evaluate SAHI for distant objects
- split train/val by video, not by frame

## Testing

Required tests:

- conversion from YOLO outputs to `DetectionRecord`
- class-name mapping
- coordinate clipping to frame bounds
- SAHI coordinate merge behavior

Manual verification:

- render 10 random clips with detections
- record common failure cases in `docs/decisions/architecture.md` or a dedicated evaluation note

