import pytest

from neylo.pipeline import FrameStream, probe_video, single_segment


def test_single_segment_covers_whole_video(synthetic_video):
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)
    assert seg.video_id == asset.video_id
    assert seg.start_frame == 0
    assert seg.end_frame >= 1
    assert seg.start_ms == 0.0
    assert seg.end_ms == pytest.approx(asset.duration_s * 1000.0)
    assert seg.fps == asset.fps


def test_frame_stream_yields_expected_count_and_shape(synthetic_video):
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)

    frames = []
    with FrameStream(asset, seg) as stream:
        for arr, info in stream:
            frames.append((arr, info))

    # Synthetic video was written with 25 frames; codec round-trip can drop
    # at most one frame at the boundary, but we expect almost-perfect coverage.
    assert 24 <= len(frames) <= 25
    arr0, info0 = frames[0]
    assert arr0.shape == (asset.height, asset.width, 3)
    assert info0.frame_id == 0
    assert info0.timestamp_ms == 0.0
    assert info0.video_id == asset.video_id
    assert info0.segment_id == seg.segment_id


def test_frame_stream_timestamps_monotonic(synthetic_video):
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)
    with FrameStream(asset, seg) as stream:
        timestamps = [info.timestamp_ms for _, info in stream]
    assert timestamps == sorted(timestamps)
    assert all(t1 - t0 == pytest.approx(1000.0 / asset.fps)
               for t0, t1 in zip(timestamps, timestamps[1:]))


def test_frame_stream_requires_context_manager(synthetic_video):
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)
    stream = FrameStream(asset, seg)
    with pytest.raises(RuntimeError):
        next(iter(stream))


def test_frame_stream_rejects_mismatched_video(synthetic_video):
    asset = probe_video(synthetic_video)
    seg = single_segment(asset)
    bad_seg = seg.model_copy(update={"video_id": "different"})
    with pytest.raises(ValueError, match="does not match"):
        FrameStream(asset, bad_seg)
