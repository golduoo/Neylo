# Evaluation Requirements

## Purpose

Evaluation defines whether v1 is good enough to ship for internal review.

The most important v1 question is: can Neylo detect every player and keep stable track IDs over time?

## Detection Metrics

Track:

- mAP@0.5 for `player`, `goalkeeper`, `referee`, `ball`
- recall for `ball`
- false positives per minute
- missed players per sampled frame

Initial targets:

- player mAP@0.5 greater than 0.90
- ball recall greater than 0.70

## Tracking Metrics

Track:

- IDF1
- MOTA where ground truth exists
- ID switches per player
- average player track length
- track fragmentation count

Initial targets:

- average player track length at least 2 minutes on a 5-minute sample
- ID switches no more than 3 per player per match where ground truth exists
- detection/tracking frame coverage at least 99%

## Pipeline Metrics

Track:

- total runtime
- per-stage runtime
- processed frames per second
- GPU utilization where available
- failed or skipped segments

Performance target:

- process 1 hour of 1080p footage in under 15 minutes on RTX 5090 if practical
- early v1 may miss this target, but runtime should be measured

## Test Levels

### Unit Tests

Use for:

- schemas
- path and manifest logic
- dataset split validation
- detection output conversion
- tracklet stitching logic
- export format validation

### Integration Tests

Use a 10-20s sample video.

Assert:

- pipeline completes
- Parquet is readable
- annotated MP4 exists
- frame count is plausible
- required columns exist

### Manual Visual QA

For every major model or tracker change:

- export annotated video
- inspect 10 challenging clips
- note ID switches, missed players, false positives, and ball misses

## Regression Set

Maintain a small curated regression set:

- 5 clips with ground truth when possible
- include camera pan/tilt
- include crowded penalty box
- include midfield distant players
- include shadow or exposure changes

## Acceptance Checklist

Before considering v1 complete:

- detection model has validation metrics
- tracking has at least one annotated visual QA pass
- full pipeline can run on a sample video
- Parquet output schema is stable
- annotated MP4 is readable
- known failure cases are documented

