from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from neylo.schemas.common import ClassName


class TrackRecord(BaseModel):
    """One tracked object in one frame. Contract per PLAN_v2 §6.2.

    `source_track_id` is the tracker's raw output. `stitched_track_id` is the
    offline-stitched ID; if no stitching ran, leave it None and consumers
    should fall back to `source_track_id`.
    """

    model_config = ConfigDict(extra="forbid")

    video_id: str
    segment_id: str
    frame_id: int = Field(ge=0)
    timestamp_ms: float = Field(ge=0)

    track_id: int = Field(ge=0)
    class_name: ClassName
    conf: float = Field(ge=0.0, le=1.0)

    x1: float = Field(ge=0)
    y1: float = Field(ge=0)
    x2: float = Field(ge=0)
    y2: float = Field(ge=0)

    tracker_name: str
    source_track_id: int = Field(ge=0)
    stitched_track_id: int | None = None
