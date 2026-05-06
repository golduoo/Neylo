from __future__ import annotations

from pathlib import Path

import pytest

from neylo.cli.main import app, build_parser


def _write_min_config(path: Path) -> Path:
    path.write_text(
        "ingest:\n"
        "  video_extensions: ['.mp4']\n"
        "runtime:\n"
        "  device: cuda:0\n",
        encoding="utf-8",
    )
    return path


def test_parser_requires_subcommand():
    parser = build_parser()
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_run_missing_input(tmp_path, capsys):
    cfg = _write_min_config(tmp_path / "pipeline.yaml")
    rc = app(["run", "--input", str(tmp_path / "missing.mp4"), "--config", str(cfg)])
    assert rc == 2
    err = capsys.readouterr().err
    assert "input not found" in err


def test_run_stub_succeeds(tmp_path, capsys):
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"")
    cfg = _write_min_config(tmp_path / "pipeline.yaml")
    rc = app(["run", "--input", str(video), "--config", str(cfg)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "Phase 0 stub" in out
    assert "cuda:0" in out


def test_run_batch_lists_videos(tmp_path, capsys):
    (tmp_path / "a.mp4").write_bytes(b"")
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "b.mp4").write_bytes(b"")
    (tmp_path / "ignore.txt").write_text("x", encoding="utf-8")
    cfg = _write_min_config(tmp_path / "pipeline.yaml")

    rc = app(["run-batch", "--input-dir", str(tmp_path), "--config", str(cfg)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "found 2 video(s)" in out


def test_run_batch_missing_dir(tmp_path, capsys):
    cfg = _write_min_config(tmp_path / "pipeline.yaml")
    rc = app(["run-batch", "--input-dir", str(tmp_path / "nope"), "--config", str(cfg)])
    assert rc == 2
    assert "input dir not found" in capsys.readouterr().err


def test_detect_only_parser_accepts_args():
    """detect-only is a registered subcommand with required --input."""
    parser = build_parser()
    # missing --input should fail
    with pytest.raises(SystemExit):
        parser.parse_args(["detect-only"])

    args = parser.parse_args([
        "detect-only",
        "--input", "clip.mp4",
        "--config", "configs/pipeline.yaml",
        "--output-dir", "outputs",
    ])
    assert args.command == "detect-only"
    assert args.input == "clip.mp4"
    assert args.output_dir == "outputs"


def test_detect_only_missing_input(tmp_path, capsys):
    cfg = _write_min_config(tmp_path / "pipeline.yaml")
    # No `detection` block in this minimal config; the missing-input check
    # runs first and returns 2 before any model load.
    rc = app([
        "detect-only",
        "--input", str(tmp_path / "missing.mp4"),
        "--config", str(cfg),
    ])
    assert rc == 2
    assert "input not found" in capsys.readouterr().err


def test_detect_only_missing_detection_section(tmp_path, capsys):
    """If pipeline.yaml lacks detection.model_path, fail with a clear message."""
    cfg = _write_min_config(tmp_path / "pipeline.yaml")  # no `detection:` block
    video = tmp_path / "clip.mp4"
    video.write_bytes(b"")
    rc = app([
        "detect-only",
        "--input", str(video),
        "--config", str(cfg),
    ])
    assert rc == 2
    assert "detection.model_path" in capsys.readouterr().err
