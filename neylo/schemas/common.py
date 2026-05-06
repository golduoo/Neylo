from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ClassName(str, Enum):
    """v1 detector classes.

    Reduced to a single `player` class because the available training
    data is severely imbalanced (goalkeeper=33, referee=16,
    another-player=131 vs player-white=41418, ball=2110). The 49 total
    keeper+referee instances are too few to train a reliable
    discriminator. Ball is deferred to v2 (separate small-object model
    with SAHI). See PLAN_v2 §3 and AGENTS.md `v1 Scope`.
    """

    PLAYER = "player"


class BBox(BaseModel):
    """Axis-aligned bounding box in image coordinates (top-left origin)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    x1: float = Field(ge=0)
    y1: float = Field(ge=0)
    x2: float = Field(ge=0)
    y2: float = Field(ge=0)

    @model_validator(mode="after")
    def _check_order(self) -> BBox:
        if self.x2 <= self.x1 or self.y2 <= self.y1:
            raise ValueError(f"invalid bbox: x2>x1 and y2>y1 required, got {self}")
        return self

    @property
    def width(self) -> float:
        return self.x2 - self.x1

    @property
    def height(self) -> float:
        return self.y2 - self.y1

    @property
    def area(self) -> float:
        return self.width * self.height
