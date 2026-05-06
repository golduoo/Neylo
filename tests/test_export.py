from pathlib import Path

import pyarrow.parquet as pq

from neylo.pipeline.export import DETECTIONS_SCHEMA, write_detections_parquet
from neylo.schemas import ClassName, DetectionRecord


def _make_record(frame_id: int = 0, **overrides) -> DetectionRecord:
    base = dict(
        video_id="v1",
        segment_id="seg_0",
        frame_id=frame_id,
        timestamp_ms=frame_id * 40.0,
        class_name=ClassName.PLAYER,
        conf=0.9,
        x1=10.0, y1=20.0, x2=30.0, y2=50.0,
        detector_name="ultralytics-yolo11",
        model_version="yolo11n.pt",
    )
    base.update(overrides)
    return DetectionRecord(**base)


def test_write_detections_parquet_round_trip(tmp_path: Path):
    records = [_make_record(i) for i in range(3)]
    out = tmp_path / "detections.parquet"
    n = write_detections_parquet(records, out)
    assert n == 3
    assert out.exists()

    table = pq.read_table(out)
    assert table.num_rows == 3
    # schema column order is preserved
    assert table.schema.names == DETECTIONS_SCHEMA.names

    rows = table.to_pylist()
    assert rows[0]["video_id"] == "v1"
    assert rows[0]["class_name"] == "player"
    assert rows[0]["frame_id"] == 0
    assert rows[2]["frame_id"] == 2
    assert rows[2]["timestamp_ms"] == 80.0


def test_write_empty_yields_empty_table(tmp_path: Path):
    out = tmp_path / "detections.parquet"
    n = write_detections_parquet(iter(()), out)
    assert n == 0
    assert out.exists()

    table = pq.read_table(out)
    assert table.num_rows == 0
    assert table.schema.names == DETECTIONS_SCHEMA.names


def test_write_creates_parent_dirs(tmp_path: Path):
    out = tmp_path / "nested" / "subdir" / "detections.parquet"
    n = write_detections_parquet([_make_record(0)], out)
    assert n == 1
    assert out.exists()


def test_write_no_tmp_file_left_behind(tmp_path: Path):
    out = tmp_path / "detections.parquet"
    write_detections_parquet([_make_record(0)], out)
    leftover = list(tmp_path.glob("*.tmp"))
    assert leftover == []
