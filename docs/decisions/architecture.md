# Architecture Decisions

This file records major decisions so future agents do not repeatedly reopen settled questions.

## ADR-001: Offline Batch First

Decision:

- v1 is an offline post-match batch pipeline, not a real-time livestream system.

Reason:

- current goal is stable detection and tracking
- offline processing allows heavier models, segment-level retries, and post-processing
- tracklet stitching benefits from seeing the full segment or match

Consequences:

- latency is less important than accuracy and reproducibility
- outputs should be persisted between stages
- future livestream support should be a separate v2 design

## ADR-002: YOLO11 For Detection

Decision:

- use YOLO11 through `ultralytics` as the primary detector.

Reason:

- strong object detection baseline
- simple training and export workflow
- integrates with common tracking workflows

Consequences:

- detection output must be converted into Neylo-owned schemas
- avoid leaking raw Ultralytics result objects across module boundaries

## ADR-003: BoT-SORT + ReID + CMC For Player Tracking

Decision:

- use BoT-SORT with ReID and camera motion compensation.

Reason:

- football clips include camera pan/tilt
- player ID stability is the v1 priority
- ReID plus CMC should reduce track fragmentation and ID swaps

Consequences:

- tracking needs access to frame data, not just detections
- tracker config must expose CMC options
- offline stitching should be kept as a separate post-processing step

## ADR-004: Defer Pitch Calibration

Decision:

- do not implement pitch homography, bird's-eye view, or real-world coordinates in v1.

Reason:

- far-side pitch lines may be occluded
- PTZ-like camera motion complicates calibration
- v1 does not need speed, distance, or event detection

Consequences:

- all v1 outputs are image-coordinate based
- analytics requiring real-world coordinates are v2 work

## ADR-005: Local Filesystem Before Services

Decision:

- v1 can use local filesystem outputs before adding MinIO and PostgreSQL.

Reason:

- current environment is a local GPU workstation
- simpler iteration matters during model and tracker development

Consequences:

- design path conventions cleanly
- keep storage adapters possible, but do not block v1 on service infrastructure

