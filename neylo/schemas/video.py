from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field


class VideoAsset(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_id: str = Field(min_length=1)
    path: Path
    size_bytes: int = Field(ge=0)
    duration_s: float = Field(ge=0)
    fps: float = Field(gt=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
    source: str | None = None


class VideoSegment(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_id: str
    segment_id: str
    start_frame: int = Field(ge=0)
    end_frame: int = Field(gt=0)
    start_ms: float = Field(ge=0)
    end_ms: float = Field(ge=0)
    fps: float = Field(gt=0)


class FrameInfo(BaseModel):
    model_config = ConfigDict(extra="forbid")

    video_id: str
    segment_id: str
    frame_id: int = Field(ge=0)
    timestamp_ms: float = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)
