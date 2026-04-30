from pathlib import Path

import yaml


def test_package_importable():
    import neylo

    assert neylo.__version__


def test_pipeline_config_loads(configs_dir: Path):
    cfg_path = configs_dir / "pipeline.yaml"
    assert cfg_path.exists()
    cfg = yaml.safe_load(cfg_path.read_text(encoding="utf-8"))
    for key in ("paths", "ingest", "decode", "detection", "tracking", "export", "runtime"):
        assert key in cfg, f"missing top-level key: {key}"


def test_expected_subpackages_present():
    from neylo import evaluation, pipeline, schemas, services  # noqa: F401
    from neylo.services import detection, tracking  # noqa: F401
