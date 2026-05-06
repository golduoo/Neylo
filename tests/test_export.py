import json
from pathlib import Path

import pyarrow.parquet as pq

from neylo.pipeline.export import (
    DETECTIONS_SCHEMA,
    TRACKS_SCHEMA,
    build_track_index,
    write_detections_parquet,
    write_track_index,
    write_tracks_parquet,
)
from neylo.schemas import ClassName, DetectionRecord, TrackRecord


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


# ---------- tracks ----------

def _make_track(frame_id: int = 0, track_id: int = 1, **overrides) -> TrackRecord:
    base = dict(
        video_id="v1",
        segment_id="seg_0",
        frame_id=frame_id,
        timestamp_ms=frame_id * 40.0,
        track_id=track_id,
        class_name=ClassName.PLAYER,
        conf=0.9,
        x1=10.0, y1=20.0, x2=30.0, y2=50.0,
        tracker_name="botsort",
        source_track_id=track_id,
    )
    base.update(overrides)
    return TrackRecord(**base)


def test_write_tracks_round_trip(tmp_path: Path):
    records = [_make_track(i, track_id=1 + (i % 3)) for i in range(6)]
    out = tmp_path / "tracks.parquet"
    n = write_tracks_parquet(records, out)
    assert n == 6
    assert out.exists()

    table = pq.read_table(out)
    assert table.num_rows == 6
    assert table.schema.names == TRACKS_SCHEMA.names

    rows = table.to_pylist()
    assert rows[0]["track_id"] == 1
    assert rows[0]["source_track_id"] == 1
    assert rows[0]["stitched_track_id"] is None
    assert rows[0]["tracker_name"] == "botsort"


def test_write_tracks_empty_yields_empty_table(tmp_path: Path):
    out = tmp_path / "tracks.parquet"
    n = write_tracks_parquet(iter(()), out)
    assert n == 0
    table = pq.read_table(out)
    assert table.num_rows == 0
    assert table.schema.names == TRACKS_SCHEMA.names


def test_write_tracks_preserves_stitched_id(tmp_path: Path):
    records = [_make_track(0, track_id=5, stitched_track_id=99)]
    out = tmp_path / "tracks.parquet"
    write_tracks_parquet(records, out)
    rows = pq.read_table(out).to_pylist()
    assert rows[0]["stitched_track_id"] == 99


# ---------- track index ----------

def test_track_index_empty():
    assert build_track_index([]) == {}


def test_track_index_single_track_single_frame():
    idx = build_track_index([_make_track(frame_id=0, track_id=1)])
    assert set(idx.keys()) == {1}
    e = idx[1]
    assert e["track_id"] == 1
    assert e["class"] == "player"
    assert e["first_frame"] == e["last_frame"] == 0
    assert e["first_timestamp_ms"] == e["last_timestamp_ms"] == 0.0
    assert e["n_frames"] == 1


def test_track_index_single_track_multiple_frames():
    records = [_make_track(frame_id=i, track_id=7) for i in (3, 5, 8, 12)]
    idx = build_track_index(records)
    e = idx[7]
    assert e["first_frame"] == 3
    assert e["last_frame"] == 12
    assert e["n_frames"] == 4
    assert e["first_timestamp_ms"] == 120.0  # 3 * 40
    assert e["last_timestamp_ms"] == 480.0   # 12 * 40


def test_track_index_multiple_tracks():
    records = [
        _make_track(0, 1),
        _make_track(0, 2),
        _make_track(1, 1),
        _make_track(1, 2),
        _make_track(2, 2),  # track 2 outlives track 1
    ]
    idx = build_track_index(records)
    assert idx[1]["n_frames"] == 2
    assert idx[1]["last_frame"] == 1
    assert idx[2]["n_frames"] == 3
    assert idx[2]["last_frame"] == 2


def test_track_index_order_independent():
    """Records arriving in non-frame-order still produce correct extrema."""
    records = [
        _make_track(frame_id=10, track_id=1),
        _make_track(frame_id=2, track_id=1),
        _make_track(frame_id=7, track_id=1),
    ]
    idx = build_track_index(records)
    e = idx[1]
    assert e["first_frame"] == 2
    assert e["last_frame"] == 10
    assert e["n_frames"] == 3


def test_write_track_index_round_trip(tmp_path: Path):
    records = [_make_track(0, 1), _make_track(1, 1), _make_track(0, 2)]
    idx = build_track_index(records)

    out = tmp_path / "track_index.json"
    n = write_track_index(idx, out)
    assert n == 2
    assert out.exists()

    loaded = json.loads(out.read_text(encoding="utf-8"))
    # JSON keys are stringified
    assert set(loaded.keys()) == {"1", "2"}
    assert loaded["1"]["n_frames"] == 2
    assert loaded["2"]["track_id"] == 2


def test_write_track_index_creates_parent_dirs(tmp_path: Path):
    out = tmp_path / "nested" / "subdir" / "track_index.json"
    n = write_track_index({1: {"track_id": 1, "n_frames": 1}}, out)
    assert n == 1
    assert out.exists()


def test_write_track_index_no_tmp_left_behind(tmp_path: Path):
    out = tmp_path / "track_index.json"
    write_track_index({1: {"track_id": 1, "n_frames": 1}}, out)
    leftover = list(tmp_path.glob("*.tmp"))
    assert leftover == []


def test_write_track_index_empty(tmp_path: Path):
    out = tmp_path / "track_index.json"
    n = write_track_index({}, out)
    assert n == 0
    assert json.loads(out.read_text(encoding="utf-8")) == {}
