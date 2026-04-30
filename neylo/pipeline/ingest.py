"""Ingest: probe local video files and produce VideoAsset records."""

from __future__ import annotations

import re
from collections.abc import Iterable
from pathlib import Path

import cv2

from neylo.schemas import VideoAsset

DEFAULT_VIDEO_EXTENSIONS = (".mp4", ".mov", ".mkv", ".avi")

_SLUG_RE = re.compile(r"[^a-zA-Z0-9]+")


def make_video_id(path: Path) -> str:
    """Derive a slug-style id from a file stem.

    Stable across runs for the same filename. Phase 1 assumes filenames
    are unique within a job; collision handling is deferred.
    """
    slug = _SLUG_RE.sub("_", path.stem).strip("_").lower()
    return slug or "video"


def probe_video(path: Path) -> VideoAsset:
    """Read width / height / fps / duration / size from a video file."""
    path = Path(path)
    if not path.is_file():
        raise FileNotFoundError(f"video not found: {path}")

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cv2 failed to open video: {path}")
    try:
        fps = float(cap.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
    finally:
        cap.release()

    if fps <= 0 or width <= 0 or height <= 0 or frame_count <= 0:
        raise RuntimeError(
            f"invalid video metadata for {path}: "
            f"fps={fps}, w={width}, h={height}, frames={frame_count}"
        )

    duration_s = frame_count / fps

    return VideoAsset(
        video_id=make_video_id(path),
        path=path,
        size_bytes=path.stat().st_size,
        duration_s=duration_s,
        fps=fps,
        width=width,
        height=height,
        source=None,
    )


def discover_videos(
    root: Path,
    extensions: Iterable[str] = DEFAULT_VIDEO_EXTENSIONS,
) -> list[Path]:
    """Return all video files under `root`, sorted by relative path."""
    root = Path(root)
    if not root.is_dir():
        raise NotADirectoryError(f"not a directory: {root}")
    exts = {e.lower() for e in extensions}
    return sorted(p for p in root.rglob("*") if p.is_file() and p.suffix.lower() in exts)
