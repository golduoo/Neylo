from __future__ import annotations

from datetime import datetime
from enum import Enum
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class StageStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    SKIPPED = "skipped"


class StageRun(BaseModel):
    """Idempotency key + status for one (video, segment, stage) execution.

    Per pipeline.md the idempotency key is
    (video_id, segment_id, stage_name, config_hash, model_version).
    """

    model_config = ConfigDict(extra="forbid")

    video_id: str
    segment_id: str
    stage_name: str
    config_hash: str
    model_version: str

    status: StageStatus = StageStatus.PENDING
    started_at: datetime | None = None
    finished_at: datetime | None = None

    output_path: Path | None = None
    error: str | None = None


class PipelineRun(BaseModel):
    model_config = ConfigDict(extra="forbid")

    pipeline_run_id: str = Field(min_length=1)
    started_at: datetime
    finished_at: datetime | None = None

    config_hash: str
    config_path: Path
    video_ids: list[str] = Field(default_factory=list)
    status: StageStatus = StageStatus.PENDING

    summary: dict[str, int | float | str] = Field(default_factory=dict)
