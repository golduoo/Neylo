"""Decode: iterate frames from a VideoAsset as (ndarray, FrameInfo) pairs."""

from __future__ import annotations

from collections.abc import Iterator
from typing import Self

import cv2
import numpy as np

from neylo.schemas import FrameInfo, VideoAsset, VideoSegment


def single_segment(asset: VideoAsset, segment_id: str = "seg_0") -> VideoSegment:
    """Treat the whole video as one segment.

    Real 1–2 minute segmentation lands in Phase 4. Phase 1 inputs are
    short Veo highlight clips, so a single segment is sufficient.
    """
    end_frame = max(1, int(round(asset.duration_s * asset.fps)))
    return VideoSegment(
        video_id=asset.video_id,
        segment_id=segment_id,
        start_frame=0,
        end_frame=end_frame,
        start_ms=0.0,
        end_ms=asset.duration_s * 1000.0,
        fps=asset.fps,
    )


class FrameStream:
    """Context-managed iterator over (frame, FrameInfo) for one segment.

    Frame is a BGR uint8 ndarray straight from OpenCV. FrameInfo carries
    the frame index local to the video (not the segment) and a
    timestamp_ms derived from the segment fps. Phase 1 segments cover
    the whole video, so frame indices line up with absolute positions.
    """

    def __init__(self, asset: VideoAsset, segment: VideoSegment) -> None:
        if segment.video_id != asset.video_id:
            raise ValueError(
                f"segment.video_id={segment.video_id!r} does not match "
                f"asset.video_id={asset.video_id!r}"
            )
        self._asset = asset
        self._segment = segment
        self._cap: cv2.VideoCapture | None = None

    def __enter__(self) -> Self:
        cap = cv2.VideoCapture(str(self._asset.path))
        if not cap.isOpened():
            raise RuntimeError(f"cv2 failed to open video: {self._asset.path}")
        if self._segment.start_frame > 0:
            cap.set(cv2.CAP_PROP_POS_FRAMES, float(self._segment.start_frame))
        self._cap = cap
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        if self._cap is not None:
            self._cap.release()
            self._cap = None

    def __iter__(self) -> Iterator[tuple[np.ndarray, FrameInfo]]:
        if self._cap is None:
            raise RuntimeError("FrameStream must be used as a context manager")

        fps = self._segment.fps
        frame_id = self._segment.start_frame
        end = self._segment.end_frame

        while frame_id < end:
            ok, frame = self._cap.read()
            if not ok or frame is None:
                break
            info = FrameInfo(
                video_id=self._asset.video_id,
                segment_id=self._segment.segment_id,
                frame_id=frame_id,
                timestamp_ms=(frame_id / fps) * 1000.0,
                width=self._asset.width,
                height=self._asset.height,
            )
            yield frame, info
            frame_id += 1
