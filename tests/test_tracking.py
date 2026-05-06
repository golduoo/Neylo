"""Unit tests for the tracking adapter — no GPU, no model load."""

from __future__ import annotations

import numpy as np
import pytest

from neylo.pipeline import run_tracking, probe_video, single_segment
from neylo.schemas import ClassName, FrameInfo, TrackRecord
from neylo.services.tracking import TRACKER_NAME, parse_track_results


@pytest.fixture
def frame_info() -> FrameInfo:
    return FrameInfo(
        video_id="v1",
        segment_id="seg_0",
        frame_id=10,
        timestamp_ms=400.0,
        width=1920,
        height=1080,
    )


def _arrs(boxes_xyxy, confs, clses, ids):
    return (
        np.asarray(boxes_xyxy, dtype=np.float32).reshape(-1, 4),
        np.asarray(confs, dtype=np.float32),
        np.asarray(clses, dtype=np.int64),
        np.asarray(ids, dtype=np.int64),
    )


# ---------- parse_track_results ----------

def test_parse_empty(frame_info):
    xyxy, conf, cls, ids = _arrs([], [], [], [])
    out = parse_track_results(
        xyxy=xyxy, conf=conf, cls=cls, track_ids=ids,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER},
        tracker_name=TRACKER_NAME,
    )
    assert out == []


def test_parse_filters_unmapped_class(frame_info):
    xyxy, conf, cls, ids = _arrs(
        [[10, 20, 30, 40], [50, 60, 70, 80]],
        [0.9, 0.8],
        [0, 32],   # 32 not in class map
        [7, 11],
    )
    out = parse_track_results(
        xyxy=xyxy, conf=conf, cls=cls, track_ids=ids,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER},
        tracker_name=TRACKER_NAME,
    )
    assert len(out) == 1
    assert out[0].track_id == 7
    assert out[0].source_track_id == 7
    assert out[0].stitched_track_id is None
    assert out[0].class_name == ClassName.PLAYER


def test_parse_filters_negative_track_id(frame_info):
    """Tracker may emit -1 for unconfirmed tracks; those rows must be dropped."""
    xyxy, conf, cls, ids = _arrs(
        [[10, 20, 30, 40], [50, 60, 70, 80]],
        [0.9, 0.8],
        [0, 0],
        [-1, 4],
    )
    out = parse_track_results(
        xyxy=xyxy, conf=conf, cls=cls, track_ids=ids,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER},
        tracker_name=TRACKER_NAME,
    )
    assert [r.track_id for r in out] == [4]


def test_parse_clamps_out_of_bound(frame_info):
    xyxy, conf, cls, ids = _arrs(
        [[-5, -10, 1925, 1090]],
        [0.7], [0], [3],
    )
    out = parse_track_results(
        xyxy=xyxy, conf=conf, cls=cls, track_ids=ids,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER},
        tracker_name=TRACKER_NAME,
    )
    assert len(out) == 1
    r = out[0]
    assert r.x1 == 0 and r.y1 == 0
    assert r.x2 == 1920 and r.y2 == 1080


def test_parse_drops_degenerate_after_clamp(frame_info):
    xyxy, conf, cls, ids = _arrs(
        [[2000, 100, 2100, 200]],
        [0.6], [0], [5],
    )
    out = parse_track_results(
        xyxy=xyxy, conf=conf, cls=cls, track_ids=ids,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER},
        tracker_name=TRACKER_NAME,
    )
    assert out == []


def test_parse_shape_mismatch_raises(frame_info):
    xyxy = np.zeros((3, 4), dtype=np.float32)
    conf = np.zeros((3,), dtype=np.float32)
    cls = np.zeros((3,), dtype=np.int64)
    ids = np.zeros((2,), dtype=np.int64)
    with pytest.raises(ValueError, match="shape mismatch"):
        parse_track_results(
            xyxy=xyxy, conf=conf, cls=cls, track_ids=ids,
            frame_info=frame_info,
            class_map={0: ClassName.PLAYER},
            tracker_name=TRACKER_NAME,
        )


def test_parse_full_record_fields(frame_info):
    xyxy, conf, cls, ids = _arrs(
        [[10, 20, 30, 40]],
        [0.95], [0], [42],
    )
    out = parse_track_results(
        xyxy=xyxy, conf=conf, cls=cls, track_ids=ids,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER},
        tracker_name="botsort",
    )
    assert len(out) == 1
    r = out[0]
    assert r.video_id == frame_info.video_id
    assert r.segment_id == frame_info.segment_id
    assert r.frame_id == frame_info.frame_id
    assert r.timestamp_ms == frame_info.timestamp_ms
    assert r.tracker_name == "botsort"
    assert r.track_id == 42
    assert r.source_track_id == 42
    assert r.stitched_track_id is None


# ---------- run_tracking via fake tracker ----------

class _FakeTracker:
    """Returns one TrackRecord per frame with a constant track_id."""

    def __init__(self) -> None:
        self.seen: list[int] = []

    def track(self, frame: np.ndarray, frame_info: FrameInfo) -> list[TrackRecord]:
        self.seen.append(frame_info.frame_id)
        return [
            TrackRecord(
                video_id=frame_info.video_id,
                segment_id=frame_info.segment_id,
                frame_id=frame_info.frame_id,
                timestamp_ms=frame_info.timestamp_ms,
                track_id=1,
                class_name=ClassName.PLAYER,
                conf=0.9,
                x1=0, y1=0, x2=10, y2=20,
                tracker_name="fake",
                source_track_id=1,
            )
        ]


def test_run_tracking_yields_per_frame(synthetic_video):
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)
    tracker = _FakeTracker()

    records = list(run_tracking(asset, seg, tracker))
    assert len(records) == len(tracker.seen)
    assert tracker.seen == sorted(tracker.seen)
    assert all(r.track_id == 1 for r in records)
    assert all(r.video_id == asset.video_id for r in records)
