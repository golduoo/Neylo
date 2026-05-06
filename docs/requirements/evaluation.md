# Evaluation Requirements

## Purpose

Evaluation defines whether v1 is good enough to ship for internal review.

The most important v1 question is: can Neylo detect every player and keep stable track IDs over time?

## Detection Metrics

v1 is single-class; metrics are reported for `player` only.

Track:

- mAP@0.5 for `player`
- mAP@0.5:0.95 for `player`
- false positives per minute
- missed players per sampled frame

Initial targets:

- player mAP@0.5 greater than 0.90 on the external dataset's `test` split
  (`ball-player-gk-scoreboard-ref`, see `docs/requirements/data.md`)
- player mAP@0.5 greater than 0.85 on a small Veo holdout (added in
  late Phase 4 if domain gap is observed)

Ball / goalkeeper / referee metrics are out of v1 scope.

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
- `detections.parquet` and `tracks.parquet` are readable
- `track_index.json` is valid
- frame count is plausible
- required columns exist

### Manual Visual QA

For every major model or tracker change:

- export overlay video (or render via the web UI)
- inspect 10 challenging clips
- note ID switches, missed players, false positives

## Regression Set

Maintain a small curated regression set:

- 5 clips with ground truth when possible
- include camera pan/tilt
- include crowded penalty box
- include midfield distant players
- include shadow or exposure changes

## Acceptance Checklist

Before considering v1 complete:

- detection model has validation metrics on both the external dataset
  test split and a Veo holdout (if labeled)
- tracking has at least one visual QA pass on Veo footage via the
  web UI
- full pipeline can run end-to-end on a sample video via both CLI
  (`neylo run`) and the FastAPI endpoint (`POST /api/v1/jobs`)
- Parquet schemas (`detections`, `tracks`) are stable and documented
- web UI completes the upload → process → select track → playback
  loop on at least 3 clips without manual intervention
- known failure cases are documented

