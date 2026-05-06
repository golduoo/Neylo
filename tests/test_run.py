"""Tests for runner functions using fake detectors / trackers — no GPU."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pyarrow.parquet as pq

from neylo.pipeline import (
    build_track_index,
    probe_video,
    run_detect_and_track,
    run_detection_only,
    single_segment,
    write_detections_parquet,
    write_track_index,
    write_tracks_parquet,
)
from neylo.schemas import ClassName, DetectionRecord, FrameInfo, TrackRecord


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


# ---------- run_detect_and_track integration ----------

class _FakeCombinedTracker:
    """Returns 2 detections + 1 confirmed track per frame.

    Simulates the realistic case where some detections do not yet have
    confirmed track ids, so detection rows >= track rows.
    """

    def __init__(self) -> None:
        self.calls: list[int] = []

    def track_and_detect(
        self, frame: np.ndarray, frame_info: FrameInfo
    ) -> tuple[list[DetectionRecord], list[TrackRecord]]:
        self.calls.append(frame_info.frame_id)
        det_kwargs = dict(
            video_id=frame_info.video_id,
            segment_id=frame_info.segment_id,
            frame_id=frame_info.frame_id,
            timestamp_ms=frame_info.timestamp_ms,
            class_name=ClassName.PLAYER,
            conf=0.8,
            x1=0, y1=0, x2=10, y2=20,
            detector_name="fake-yolo",
            model_version="fake-1",
        )
        det1 = DetectionRecord(**det_kwargs)
        det2 = DetectionRecord(**{**det_kwargs, "x1": 50, "y1": 60, "x2": 80, "y2": 100})

        trk = TrackRecord(
            video_id=frame_info.video_id,
            segment_id=frame_info.segment_id,
            frame_id=frame_info.frame_id,
            timestamp_ms=frame_info.timestamp_ms,
            track_id=42,
            class_name=ClassName.PLAYER,
            conf=0.8,
            x1=0, y1=0, x2=10, y2=20,
            tracker_name="fake-tracker",
            source_track_id=42,
        )
        return [det1, det2], [trk]


def test_run_detect_and_track_yields_per_frame_pair(synthetic_video):
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)
    tracker = _FakeCombinedTracker()

    pairs = list(run_detect_and_track(asset, seg, tracker))
    assert len(pairs) == len(tracker.calls)
    assert tracker.calls == sorted(tracker.calls)
    # Each frame yields (2 detections, 1 track)
    for dets, trks in pairs:
        assert len(dets) == 2
        assert len(trks) == 1


def test_run_detect_and_track_full_pipeline_artifacts(synthetic_video, tmp_path: Path):
    """End-to-end: drive run_detect_and_track with a fake tracker and
    verify all three artifacts (detections.parquet, tracks.parquet,
    track_index.json) are produced with expected shape."""
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)
    tracker = _FakeCombinedTracker()

    detections: list[DetectionRecord] = []
    tracks: list[TrackRecord] = []
    for dets, trks in run_detect_and_track(asset, seg, tracker):
        detections.extend(dets)
        tracks.extend(trks)

    out_dir = tmp_path / asset.video_id
    out_dir.mkdir(parents=True)

    n_det = write_detections_parquet(detections, out_dir / "detections.parquet")
    n_trk = write_tracks_parquet(tracks, out_dir / "tracks.parquet")
    n_idx = write_track_index(build_track_index(tracks), out_dir / "track_index.json")

    n_frames = len(tracker.calls)
    assert n_det == n_frames * 2
    assert n_trk == n_frames * 1
    assert n_idx == 1  # single track id 42

    # readability check
    det_table = pq.read_table(out_dir / "detections.parquet")
    trk_table = pq.read_table(out_dir / "tracks.parquet")
    assert det_table.num_rows == n_det
    assert trk_table.num_rows == n_trk

    import json
    idx = json.loads((out_dir / "track_index.json").read_text(encoding="utf-8"))
    assert "42" in idx
    assert idx["42"]["n_frames"] == n_frames
    assert idx["42"]["first_frame"] == 0
