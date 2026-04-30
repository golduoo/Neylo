from pathlib import Path

import cv2
import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


@pytest.fixture(scope="session")
def configs_dir(project_root: Path) -> Path:
    return project_root / "configs"


@pytest.fixture(scope="session")
def data_dir(project_root: Path) -> Path:
    return project_root / "data"


def _write_synthetic_mp4(
    path: Path,
    *,
    width: int = 64,
    height: int = 48,
    fps: float = 25.0,
    n_frames: int = 25,
) -> Path:
    """Write a deterministic tiny mp4 for tests using cv2.VideoWriter.

    Each frame is a solid color whose channels equal the frame index, so
    consumers can verify frame ordering without a heavy codec dependency.
    """
    fourcc = cv2.VideoWriter_fourcc(*"mp4v")
    writer = cv2.VideoWriter(str(path), fourcc, fps, (width, height))
    if not writer.isOpened():
        raise RuntimeError(f"cv2 VideoWriter failed to open: {path}")
    try:
        for i in range(n_frames):
            v = (i * 7) % 256
            frame = np.full((height, width, 3), v, dtype=np.uint8)
            writer.write(frame)
    finally:
        writer.release()
    if not path.exists() or path.stat().st_size == 0:
        raise RuntimeError(f"VideoWriter produced empty file: {path}")
    return path


@pytest.fixture
def synthetic_video(tmp_path: Path) -> Path:
    return _write_synthetic_mp4(tmp_path / "synthetic.mp4")


@pytest.fixture
def synthetic_video_factory(tmp_path: Path):
    """Build extra synthetic videos with custom params, in tmp_path."""

    def _factory(name: str = "v.mp4", **kwargs) -> Path:
        return _write_synthetic_mp4(tmp_path / name, **kwargs)

    return _factory
