# Data Requirements

## Purpose

This file defines how Neylo v1 should organize video, frame, annotation, and model-output data.

## Current Data

Available data:

- 4 ANUFC matches against opponents
- Veo highlight clips
- each match contains about 20-30 clips
- each clip is about 10-20 seconds

Known limitation:

- highlight clips overrepresent penalty-area attacks
- midfield and buildup play are underrepresented

## Raw Data Layout

Suggested layout:

```text
data/
├── raw/
│   ├── match_001/
│   └── match_002/
├── frames/
├── annotations/
├── datasets/
├── models/
└── outputs/
```

Do not modify raw videos in place. Derived assets should go under `data/frames`, `data/datasets`, or `data/outputs`.

## Frame Extraction

Initial extraction strategy:

- extract around 1 fps for labeling candidates
- preserve source video path, frame index, and timestamp
- remove near-duplicate frames with perceptual hashing

Expected first labeling pool:

- about 1500-2000 candidate frames after de-duplication

## Annotation

Use CVAT locally for manual correction.

Required labels:

- `player`
- `goalkeeper`
- `referee`
- `ball`

Rules:

- label visible body extent for people
- label the visible ball, even if small, when reasonably identifiable
- use `goalkeeper` only when visually clear from kit or position
- use `referee` only when visually clear
- ambiguous far people can stay `player` unless project labeling policy changes

## Dataset Splits

Split by video or match, not by individual frame.

Reason:

- adjacent frames are highly correlated
- frame-level random splits leak validation examples and inflate metrics

Recommended split:

- train: majority of matches/clips
- validation: held-out clips from different videos
- test/regression: small curated set with hard examples

## Pseudo Labeling

Pseudo labels can accelerate annotation:

- run baseline model with `conf=0.3`
- import predictions into CVAT
- manually correct all required classes

Pseudo labels are not ground truth until reviewed.

## Additional Data Request

Ask the company for:

- 1-2 full match videos
- or representative clips from midfield transitions, throw-ins, corners, and defensive buildup

This is important because current highlight clips may not cover the deployment distribution.

## Data Versioning

At minimum, record:

- dataset version
- source videos included
- annotation date
- label schema version
- train/val/test split file
- model trained from this dataset

## Testing

Required checks:

- annotation class names match code constants
- YOLO dataset YAML points to existing paths
- train/val split does not mix frames from the same source video unless explicitly allowed
- bounding boxes are inside image bounds

