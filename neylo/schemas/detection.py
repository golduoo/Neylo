from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from neylo.schemas.common import ClassName


class DetectionRecord(BaseModel):
    """One detection in one frame. Contract per PLAN_v2 §6.1."""

    model_config = ConfigDict(extra="forbid")

    video_id: str
    segment_id: str
    frame_id: int = Field(ge=0)
    timestamp_ms: float = Field(ge=0)
    class_name: ClassName
    conf: float = Field(ge=0.0, le=1.0)

    x1: float = Field(ge=0)
    y1: float = Field(ge=0)
    x2: float = Field(ge=0)
    y2: float = Field(ge=0)

    detector_name: str
    model_version: str
