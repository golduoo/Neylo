from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

from neylo import __version__


def _load_config(config_path: Path) -> dict:
    if not config_path.exists():
        raise FileNotFoundError(f"config not found: {config_path}")
    with config_path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def cmd_run(args: argparse.Namespace) -> int:
    input_path = Path(args.input).resolve()
    config_path = Path(args.config).resolve()
    cfg = _load_config(config_path)

    if not input_path.exists():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 2

    # Phase 0 stub: just echo the plan. Real stages land in Phase 1.
    print(f"neylo run (Phase 0 stub)")
    print(f"  input:  {input_path}")
    print(f"  config: {config_path}")
    print(f"  device: {cfg.get('runtime', {}).get('device', 'unset')}")
    print(f"  stages: ingest -> segment -> detect -> track -> export (not wired yet)")
    return 0


def _build_yolo_config(detection_cfg: dict):
    """Convert pipeline.yaml `detection` section to a YoloConfig."""
    from neylo.services.detection import YoloConfig  # lazy: avoids ultralytics import on every CLI call

    return YoloConfig(
        model_path=str(detection_cfg["model_path"]),
        device=str(detection_cfg.get("device", "cuda:0")),
        conf=float(detection_cfg.get("conf", 0.25)),
        iou=float(detection_cfg.get("iou", 0.6)),
        imgsz=int(detection_cfg.get("imgsz", 1280)),
        half=bool(detection_cfg.get("half", True)),
    )


def cmd_detect_only(args: argparse.Namespace) -> int:
    """Phase 1.3 smoke: ingest -> decode -> detect -> Parquet.

    No tracking. Validates the GPU inference + Parquet plumbing on a
    real video before Phase 1.4 adds BoT-SORT.
    """
    # Lazy imports keep `neylo --version` and `neylo run-batch` fast,
    # and avoid forcing torch/ultralytics import in tests that don't need it.
    from neylo.pipeline import (
        FrameStream,  # noqa: F401 -- re-exported for completeness
        probe_video,
        run_detection_only,
        single_segment,
        write_detections_parquet,
    )
    from neylo.services.detection import YoloDetector

    input_path = Path(args.input).resolve()
    config_path = Path(args.config).resolve()
    output_root = Path(args.output_dir).resolve() if args.output_dir else Path("outputs").resolve()

    if not input_path.is_file():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 2

    cfg = _load_config(config_path)
    detection_cfg = cfg.get("detection")
    if not detection_cfg or "model_path" not in detection_cfg:
        print("error: pipeline.yaml is missing detection.model_path", file=sys.stderr)
        return 2

    asset = probe_video(input_path)
    segment = single_segment(asset)
    yolo_cfg = _build_yolo_config(detection_cfg)

    print(f"neylo detect-only")
    print(f"  input:        {input_path}")
    print(f"  video_id:     {asset.video_id}")
    print(f"  fps:          {asset.fps:.3f}")
    print(f"  frames:       {segment.end_frame}")
    print(f"  resolution:   {asset.width}x{asset.height}")
    print(f"  model_path:   {yolo_cfg.model_path}")
    print(f"  device:       {yolo_cfg.device}")
    print(f"  imgsz / conf: {yolo_cfg.imgsz} / {yolo_cfg.conf}")

    detector = YoloDetector(yolo_cfg)

    out_dir = output_root / asset.video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = out_dir / "detections.parquet"

    n = write_detections_parquet(
        run_detection_only(asset, segment, detector),
        parquet_path,
    )
    print(f"  wrote:        {parquet_path}")
    print(f"  rows:         {n}")
    return 0


def _build_botsort_config(detection_cfg: dict, tracking_cfg: dict):
    """Construct a BotSortConfig from pipeline.yaml.

    Tracker shares model_path / device / conf / iou / imgsz / half with
    the detection section because ultralytics couples det+track.
    """
    from neylo.services.tracking import BotSortConfig

    return BotSortConfig(
        model_path=str(detection_cfg["model_path"]),
        tracker_path=str(tracking_cfg["config_path"]),
        device=str(detection_cfg.get("device", "cuda:0")),
        conf=float(detection_cfg.get("conf", 0.25)),
        iou=float(detection_cfg.get("iou", 0.6)),
        imgsz=int(detection_cfg.get("imgsz", 1280)),
        half=bool(detection_cfg.get("half", True)),
    )


def cmd_track_only(args: argparse.Namespace) -> int:
    """Phase 1.4 smoke: ingest -> decode -> detect+track -> tracks.parquet."""
    from neylo.pipeline import (
        probe_video,
        run_tracking,
        single_segment,
        write_tracks_parquet,
    )
    from neylo.services.tracking import BotSortTracker

    input_path = Path(args.input).resolve()
    config_path = Path(args.config).resolve()
    output_root = Path(args.output_dir).resolve() if args.output_dir else Path("outputs").resolve()

    if not input_path.is_file():
        print(f"error: input not found: {input_path}", file=sys.stderr)
        return 2

    cfg = _load_config(config_path)
    detection_cfg = cfg.get("detection")
    tracking_cfg = cfg.get("tracking")
    if not detection_cfg or "model_path" not in detection_cfg:
        print("error: pipeline.yaml is missing detection.model_path", file=sys.stderr)
        return 2
    if not tracking_cfg or "config_path" not in tracking_cfg:
        print("error: pipeline.yaml is missing tracking.config_path", file=sys.stderr)
        return 2

    asset = probe_video(input_path)
    segment = single_segment(asset)
    bot_cfg = _build_botsort_config(detection_cfg, tracking_cfg)

    print(f"neylo track-only")
    print(f"  input:        {input_path}")
    print(f"  video_id:     {asset.video_id}")
    print(f"  fps:          {asset.fps:.3f}")
    print(f"  frames:       {segment.end_frame}")
    print(f"  resolution:   {asset.width}x{asset.height}")
    print(f"  model_path:   {bot_cfg.model_path}")
    print(f"  tracker_path: {bot_cfg.tracker_path}")
    print(f"  device:       {bot_cfg.device}")
    print(f"  imgsz / conf: {bot_cfg.imgsz} / {bot_cfg.conf}")

    tracker = BotSortTracker(bot_cfg)
    out_dir = output_root / asset.video_id
    out_dir.mkdir(parents=True, exist_ok=True)
    parquet_path = out_dir / "tracks.parquet"

    n = write_tracks_parquet(run_tracking(asset, segment, tracker), parquet_path)
    print(f"  wrote:        {parquet_path}")
    print(f"  rows:         {n}")
    return 0


def cmd_run_batch(args: argparse.Namespace) -> int:
    input_dir = Path(args.input_dir).resolve()
    config_path = Path(args.config).resolve()
    cfg = _load_config(config_path)

    if not input_dir.is_dir():
        print(f"error: input dir not found: {input_dir}", file=sys.stderr)
        return 2

    exts = set(cfg.get("ingest", {}).get("video_extensions", [".mp4"]))
    videos = sorted(p for p in input_dir.rglob("*") if p.suffix.lower() in exts)

    print(f"neylo run-batch (Phase 0 stub)")
    print(f"  input_dir: {input_dir}")
    print(f"  config:    {config_path}")
    print(f"  found {len(videos)} video(s) matching {sorted(exts)}")
    for v in videos[:10]:
        print(f"    - {v.relative_to(input_dir)}")
    if len(videos) > 10:
        print(f"    ... and {len(videos) - 10} more")
    return 0


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="neylo", description="Neylo CV pipeline CLI")
    p.add_argument("--version", action="version", version=f"neylo {__version__}")
    sub = p.add_subparsers(dest="command", required=True)

    run = sub.add_parser("run", help="Run pipeline on a single video")
    run.add_argument("--input", required=True, help="path to a video file")
    run.add_argument("--config", default="configs/pipeline.yaml")
    run.set_defaults(func=cmd_run)

    runb = sub.add_parser("run-batch", help="Run pipeline on a directory of videos")
    runb.add_argument("--input-dir", required=True)
    runb.add_argument("--config", default="configs/pipeline.yaml")
    runb.set_defaults(func=cmd_run_batch)

    detect = sub.add_parser(
        "detect-only",
        help="Phase 1.3 smoke: detect on a single video and write detections.parquet (no tracking)",
    )
    detect.add_argument("--input", required=True, help="path to a video file")
    detect.add_argument("--config", default="configs/pipeline.yaml")
    detect.add_argument(
        "--output-dir",
        default=None,
        help="directory for outputs/<video_id>/detections.parquet (default: outputs/)",
    )
    detect.set_defaults(func=cmd_detect_only)

    track = sub.add_parser(
        "track-only",
        help="Phase 1.4 smoke: detect+track on a single video and write tracks.parquet",
    )
    track.add_argument("--input", required=True, help="path to a video file")
    track.add_argument("--config", default="configs/pipeline.yaml")
    track.add_argument(
        "--output-dir",
        default=None,
        help="directory for outputs/<video_id>/tracks.parquet (default: outputs/)",
    )
    track.set_defaults(func=cmd_track_only)

    return p


def app(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(app())
