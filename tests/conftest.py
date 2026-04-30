from pathlib import Path

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
