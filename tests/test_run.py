"""Tests for run_detection_only using a fake detector — no GPU."""

from __future__ import annotations

import numpy as np

from neylo.pipeline import probe_video, run_detection_only, single_segment
from neylo.schemas import ClassName, DetectionRecord, FrameInfo


class _FakeDetector:
    """Returns one synthetic detection per frame, recording frame indices."""

    def __init__(self) -> None:
        self.seen: list[int] = []

    def detect(
        self, frame: np.ndarray, frame_info: FrameInfo
    ) -> list[DetectionRecord]:
        self.seen.append(frame_info.frame_id)
        return [
            DetectionRecord(
                video_id=frame_info.video_id,
                segment_id=frame_info.segment_id,
                frame_id=frame_info.frame_id,
                timestamp_ms=frame_info.timestamp_ms,
                class_name=ClassName.PLAYER,
                conf=0.9,
                x1=0, y1=0, x2=10, y2=20,
                detector_name="fake",
                model_version="fake-1",
            )
        ]


class _EmptyDetector:
    def detect(
        self, frame: np.ndarray, frame_info: FrameInfo
    ) -> list[DetectionRecord]:
        return []


def test_run_detection_yields_one_per_frame(synthetic_video):
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)
    detector = _FakeDetector()

    records = list(run_detection_only(asset, seg, detector))

    # synthetic video has 24-25 frames; one detection per frame
    assert len(records) == len(detector.seen)
    assert detector.seen == sorted(detector.seen)
    assert detector.seen[0] == 0
    assert all(r.video_id == asset.video_id for r in records)
    assert all(r.class_name == ClassName.PLAYER for r in records)


def test_run_detection_empty_detector_yields_nothing(synthetic_video):
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)
    records = list(run_detection_only(asset, seg, _EmptyDetector()))
    assert records == []


def test_run_detection_is_lazy(synthetic_video):
    """Iterator does not run until consumed; ensures FrameStream is reentrant."""
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)
    detector = _FakeDetector()

    gen = run_detection_only(asset, seg, detector)
    # Detector hasn't seen any frame yet
    assert detector.seen == []
    # Pull one record
    first = next(gen)
    assert first.frame_id == 0
    assert detector.seen == [0]
