from neylo.schemas.common import BBox, ClassName
from neylo.schemas.detection import DetectionRecord
from neylo.schemas.run import PipelineRun, StageRun, StageStatus
from neylo.schemas.track import TrackRecord
from neylo.schemas.video import FrameInfo, VideoAsset, VideoSegment

__all__ = [
    "BBox",
    "ClassName",
    "DetectionRecord",
    "FrameInfo",
    "PipelineRun",
    "StageRun",
    "StageStatus",
    "TrackRecord",
    "VideoAsset",
    "VideoSegment",
]
