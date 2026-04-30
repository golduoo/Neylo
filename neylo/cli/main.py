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

    return p


def app(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(app())
