from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from neylo.schemas import (
    BBox,
    ClassName,
    DetectionRecord,
    FrameInfo,
    PipelineRun,
    StageRun,
    StageStatus,
    TrackRecord,
    VideoAsset,
    VideoSegment,
)


# ---------- BBox ----------

def test_bbox_valid():
    b = BBox(x1=10, y1=20, x2=30, y2=50)
    assert b.width == 20
    assert b.height == 30
    assert b.area == 600


@pytest.mark.parametrize("kwargs", [
    dict(x1=30, y1=10, x2=10, y2=50),  # x2 < x1
    dict(x1=10, y1=50, x2=30, y2=20),  # y2 < y1
    dict(x1=10, y1=10, x2=10, y2=20),  # zero width
])
def test_bbox_rejects_invalid_order(kwargs):
    with pytest.raises(ValidationError):
        BBox(**kwargs)


def test_bbox_rejects_negative():
    with pytest.raises(ValidationError):
        BBox(x1=-1, y1=0, x2=10, y2=10)


def test_bbox_frozen():
    b = BBox(x1=0, y1=0, x2=10, y2=10)
    with pytest.raises(ValidationError):
        b.x1 = 5  # type: ignore[misc]


# ---------- ClassName ----------

def test_class_name_values():
    assert ClassName.PLAYER == "player"
    assert {c.value for c in ClassName} == {"player", "goalkeeper", "referee"}


# ---------- DetectionRecord ----------

def _det_kwargs(**overrides):
    base = dict(
        video_id="v1",
        segment_id="s1",
        frame_id=0,
        timestamp_ms=0.0,
        class_name=ClassName.PLAYER,
        conf=0.8,
        x1=0, y1=0, x2=10, y2=20,
        detector_name="yolo11x",
        model_version="2026.04.30",
    )
    base.update(overrides)
    return base


def test_detection_round_trip():
    d = DetectionRecord(**_det_kwargs())
    payload = d.model_dump_json()
    d2 = DetectionRecord.model_validate_json(payload)
    assert d == d2


def test_detection_rejects_extra_field():
    with pytest.raises(ValidationError):
        DetectionRecord(**_det_kwargs(extra_thing="x"))


@pytest.mark.parametrize("conf", [-0.01, 1.01])
def test_detection_conf_bounds(conf):
    with pytest.raises(ValidationError):
        DetectionRecord(**_det_kwargs(conf=conf))


def test_detection_class_name_string_coercion():
    # str values in the enum should validate
    d = DetectionRecord(**_det_kwargs(class_name="goalkeeper"))
    assert d.class_name == ClassName.GOALKEEPER


def test_detection_rejects_unknown_class():
    with pytest.raises(ValidationError):
        DetectionRecord(**_det_kwargs(class_name="ball"))


# ---------- TrackRecord ----------

def _track_kwargs(**overrides):
    base = dict(
        video_id="v1",
        segment_id="s1",
        frame_id=0,
        timestamp_ms=0.0,
        track_id=42,
        class_name=ClassName.PLAYER,
        conf=0.9,
        x1=0, y1=0, x2=10, y2=20,
        tracker_name="botsort",
        source_track_id=42,
    )
    base.update(overrides)
    return base


def test_track_round_trip():
    t = TrackRecord(**_track_kwargs())
    t2 = TrackRecord.model_validate_json(t.model_dump_json())
    assert t == t2
    assert t.stitched_track_id is None


def test_track_with_stitched_id():
    t = TrackRecord(**_track_kwargs(stitched_track_id=7))
    assert t.stitched_track_id == 7


# ---------- Video / Frame ----------

def test_video_asset_minimal(tmp_path):
    p = tmp_path / "a.mp4"
    p.write_bytes(b"")
    a = VideoAsset(
        video_id="v1", path=p, size_bytes=0,
        duration_s=10.0, fps=25.0, width=1920, height=1080,
    )
    assert a.source is None


def test_video_segment_basic():
    s = VideoSegment(
        video_id="v1", segment_id="s1",
        start_frame=0, end_frame=250,
        start_ms=0.0, end_ms=10000.0, fps=25.0,
    )
    assert s.fps == 25.0


def test_frame_info_basic():
    f = FrameInfo(
        video_id="v1", segment_id="s1",
        frame_id=10, timestamp_ms=400.0,
        width=1920, height=1080,
    )
    assert f.frame_id == 10


# ---------- StageRun / PipelineRun ----------

def test_stage_run_defaults():
    sr = StageRun(
        video_id="v1", segment_id="s1",
        stage_name="detect", config_hash="abc", model_version="2026.04.30",
    )
    assert sr.status == StageStatus.PENDING
    assert sr.started_at is None
    assert sr.error is None


def test_pipeline_run_round_trip():
    pr = PipelineRun(
        pipeline_run_id="run-1",
        started_at=datetime(2026, 4, 30, tzinfo=timezone.utc),
        config_hash="abc",
        config_path="configs/pipeline.yaml",
        video_ids=["v1", "v2"],
        summary={"detections": 1234, "fps": 25.0, "note": "ok"},
    )
    pr2 = PipelineRun.model_validate_json(pr.model_dump_json())
    assert pr2.video_ids == ["v1", "v2"]
    assert pr2.summary["detections"] == 1234
