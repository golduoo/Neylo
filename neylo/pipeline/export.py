"""Export pipeline outputs to disk (Parquet, JSON)."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from neylo.schemas import DetectionRecord

DETECTIONS_SCHEMA = pa.schema(
    [
        ("video_id", pa.string()),
        ("segment_id", pa.string()),
        ("frame_id", pa.int64()),
        ("timestamp_ms", pa.float64()),
        ("class_name", pa.string()),
        ("conf", pa.float32()),
        ("x1", pa.float32()),
        ("y1", pa.float32()),
        ("x2", pa.float32()),
        ("y2", pa.float32()),
        ("detector_name", pa.string()),
        ("model_version", pa.string()),
    ]
)


def _detection_to_row(d: DetectionRecord) -> dict:
    return {
        "video_id": d.video_id,
        "segment_id": d.segment_id,
        "frame_id": d.frame_id,
        "timestamp_ms": d.timestamp_ms,
        "class_name": d.class_name.value,
        "conf": d.conf,
        "x1": d.x1,
        "y1": d.y1,
        "x2": d.x2,
        "y2": d.y2,
        "detector_name": d.detector_name,
        "model_version": d.model_version,
    }


def write_detections_parquet(
    records: Iterable[DetectionRecord],
    path: Path,
    *,
    compression: str = "snappy",
) -> int:
    """Materialize records and write a Parquet file. Returns the row count.

    Phase 1 expects short clips, so in-memory materialization is fine.
    Streaming writes can be added in Phase 6 batch processing.
    """
    path = Path(path)
    rows = [_detection_to_row(r) for r in records]
    table = pa.Table.from_pylist(rows, schema=DETECTIONS_SCHEMA)

    path.parent.mkdir(parents=True, exist_ok=True)
    # Atomic write: tmp file then rename, so partial files are never visible.
    tmp = path.with_suffix(path.suffix + ".tmp")
    pq.write_table(table, tmp, compression=compression)
    tmp.replace(path)

    return len(rows)
