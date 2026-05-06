"""Pipeline runners. Each function composes lower-level modules into a stage.

Phase 1.3 ships only `run_detection_only` to validate the
ingest → decode → detect plumbing on real GPU + real video before
adding tracking. Tracking-aware runners land in Phase 1.4+.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import Protocol

import numpy as np

from neylo.pipeline.decode import FrameStream
from neylo.schemas import DetectionRecord, FrameInfo, VideoAsset, VideoSegment


class DetectorProtocol(Protocol):
    """Structural type for a detector. Lets tests pass in a fake detector
    without depending on YoloDetector / ultralytics."""

    def detect(
        self, frame: np.ndarray, frame_info: FrameInfo
    ) -> list[DetectionRecord]: ...


def run_detection_only(
    asset: VideoAsset,
    segment: VideoSegment,
    detector: DetectorProtocol,
) -> Iterator[DetectionRecord]:
    """Iterate frames in `segment` and yield DetectionRecords from `detector`.

    Generator-based so the caller controls memory: stream the records to
    Parquet writer or buffer them as desired. The caller is responsible
    for opening / closing the detector's underlying model.
    """
    with FrameStream(asset, segment) as stream:
        for frame, info in stream:
            yield from detector.detect(frame, info)
