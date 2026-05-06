# Tracking Requirements

## Purpose

Tracking assigns stable IDs to detected objects across frames. For v1, stable player IDs are the most important success criterion.

## Owner

Chelsea

## Primary Tracker

Use BoT-SORT with ReID and camera motion compensation.

Starting config:

```yaml
tracker_type: botsort
with_reid: true
reid_model: osnet_x1_0_msmt17
proximity_thresh: 0.5
appearance_thresh: 0.25
gmc_method: sparseOptFlow
track_buffer: 60
match_thresh: 0.8
```

## Why CMC Is Required

Veo footage can pan and tilt. During camera motion, all bounding boxes drift in image coordinates. A pure IoU tracker can interpret this as object movement or new objects. Camera motion compensation estimates the frame-to-frame transform and improves matching under camera movement.

## Inputs

Tracking consumes:

- frame metadata
- detection records
- optional video frames for appearance embeddings and CMC
- tracker config

## Outputs

Tracking emits `TrackRecord` rows:

```text
video_id, segment_id, frame_id, timestamp_ms,
track_id, class_name, conf, x1, y1, x2, y2, tracker_name
```

For v1, `track_id` only needs to be stable within the match or processed video, not across different matches.

## Player Tracking

Requirements:

- track all detected `player` instances with stable IDs across the
  segment (v1 is single-class — see `docs/requirements/data.md`)
- handle short occlusions and dense player clusters
- preserve IDs through camera pan/tilt when possible
- expose tracker parameters in `configs/botsort.yaml` (referenced from
  `configs/pipeline.yaml`)

## Ball Tracking

Out of v1 scope. Will land in v2 alongside the dedicated ball detector.

## Offline Tracklet Stitching

Offline stitching is a v1 bonus feature and should be designed as a separate post-processing step.

Suggested approach:

1. Collect fragmented tracklets.
2. Compute average ReID embedding for each tracklet.
3. Candidate-match tracklets with time gap under 5 seconds.
4. Reject candidates with implausible position or velocity.
5. Use Hungarian matching or another global assignment strategy.
6. Emit a mapping from old track IDs to stitched track IDs.

Keep original track IDs available for debugging.

## Quality Targets

Initial v1 targets:

- average player track length at least 2 minutes on a 5-minute sample
- ID switches no more than 3 per player per match, where ground truth exists
- frame coverage at least 99% for processed frames

## Known Risks

- dense player clusters cause ID swaps
- occlusion around the box causes track fragmentation
- camera pan/tilt causes global motion
- similar jerseys reduce appearance discrimination

## Mitigations

- enable CMC by default
- use ReID embeddings
- increase `track_buffer` for longer occlusion tolerance
- add offline tracklet stitching
- keep debug visualizations for ID switches

## Testing

Required tests:

- tracker input schema validation
- detection-to-tracker adapter behavior
- stable ID output format
- tracklet stitching on synthetic tracks

Manual verification:

- render annotated video with large track IDs
- inspect at least 10 challenging clips with occlusion, camera movement, and crowded boxes

