from pathlib import Path

import pytest

from neylo.pipeline import discover_videos, make_video_id, probe_video


def test_make_video_id_slugifies():
    assert make_video_id(Path("01 001124_-_Shot_on_goal.mp4")) == "01_001124_shot_on_goal"
    assert make_video_id(Path("clip.mp4")) == "clip"


def test_make_video_id_stable():
    p = Path("data/Veo highlights ANUFC vs WEFC 23s/1 001905_-_Goal.mp4")
    assert make_video_id(p) == make_video_id(p)


def test_probe_video_basic(synthetic_video):
    asset = probe_video(synthetic_video)
    assert asset.width == 64
    assert asset.height == 48
    assert 24.0 <= asset.fps <= 26.0
    assert asset.size_bytes > 0
    assert asset.duration_s > 0
    assert asset.video_id == "synthetic"


def test_probe_video_missing(tmp_path):
    with pytest.raises(FileNotFoundError):
        probe_video(tmp_path / "nope.mp4")


def test_discover_videos(tmp_path, synthetic_video_factory):
    synthetic_video_factory("a.mp4")
    (tmp_path / "sub").mkdir()
    synthetic_video_factory("sub/b.mp4")
    (tmp_path / "ignore.txt").write_text("x", encoding="utf-8")

    found = discover_videos(tmp_path)
    assert [p.name for p in found] == ["a.mp4", "b.mp4"]


def test_discover_videos_extension_filter(tmp_path, synthetic_video_factory):
    synthetic_video_factory("a.mp4")
    found = discover_videos(tmp_path, extensions=[".mov"])
    assert found == []
