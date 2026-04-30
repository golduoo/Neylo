# Pipeline Requirements

## Purpose

The pipeline runs offline computer vision processing for football videos:

```text
ingest -> decode/segment -> detect -> track -> export
```

The pipeline should be reliable first, fast second. v1 can use the local filesystem before adding MinIO or PostgreSQL.

## Owner

Xiwen

## Inputs

- local video files from `data/`
- optional metadata such as match name, video source, and clip index
- pipeline config from `configs/pipeline.yaml`

## Outputs

- stage metadata for each `(video_id, segment_id, stage_name)`
- detection outputs per segment
- tracking outputs per segment
- final Parquet file with per-frame object tracks
- annotated MP4 with bbox, class label, confidence, and track_id

## Core Components

### Ingest

Responsibilities:

- discover local video files
- assign stable `video_id`
- collect file metadata: path, size, duration, fps, width, height
- write manifest records

### Decode And Segment

Responsibilities:

- split long videos into 1-2 minute segments
- preserve source timestamps and frame indices
- support FFmpeg-based decode
- leave room for NVDEC acceleration later

### Detect Task

Responsibilities:

- call detection service with the selected model and config
- save raw detections in a structured format
- make task reruns deterministic for the same input and model version

### Track Task

Responsibilities:

- call tracking service with detections and video/frame metadata
- save track records with stable local track IDs
- optionally run offline tracklet stitching

### Export Task

Responsibilities:

- write final Parquet
- render annotated MP4
- save summary JSON with counts, timing, warnings, and config hash

## Data Contracts

Use Pydantic v2 schemas for:

- `VideoAsset`
- `VideoSegment`
- `FrameInfo`
- `DetectionRecord`
- `TrackRecord`
- `StageRun`
- `PipelineRun`

Minimum `TrackRecord` fields:

```text
video_id, segment_id, frame_id, timestamp_ms, track_id, class_name,
conf, x1, y1, x2, y2, source
```

## Idempotency

Every stage output must be keyed by:

```text
video_id, segment_id, stage_name, config_hash, model_version
```

If a stage succeeds, rerunning should either reuse the output or overwrite it atomically.

## Configuration

Centralize tunable values in `configs/pipeline.yaml`:

- input/output directories
- segment length
- detection model path and image size
- SAHI slicing options
- tracker config path
- export visualization options
- device selection

## Testing

Required tests:

- schema serialization and validation
- ingest on a tiny fixture file
- pipeline dry run with mocked detection/tracking
- export writes a readable Parquet file

Smoke test:

- run a 10-20s sample video through the full pipeline
- confirm Parquet and MP4 outputs exist
- confirm frame coverage is at least 99%

