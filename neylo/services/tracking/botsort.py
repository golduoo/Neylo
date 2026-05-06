"""BoT-SORT tracking service via ultralytics.

ultralytics couples detection and tracking — there is no public API to feed
externally produced detections into its tracker. So `BotSortTracker`
internally loads its own YOLO model (same weights as the detection stage)
and calls `model.track(...)` per frame. The detector wrapper from 1.2 is
therefore not reused here; both classes load the same `.pt` file
independently. That is acceptable for v1 — Phase 5 may revisit if memory
becomes a concern.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from neylo.schemas import ClassName, FrameInfo, TrackRecord
from neylo.services.detection.yolo import build_class_map

TRACKER_NAME = "botsort"


@dataclass(frozen=True)
class BotSortConfig:
    """Tracker config derived from `pipeline.yaml`.

    Shares `model_path` / `device` / `conf` / `iou` / `imgsz` / `half`
    with `YoloConfig` because ultralytics couples detect + track.
    """

    model_path: str
    tracker_path: str  # path to the BoT-SORT yaml
    device: str = "cuda:0"
    conf: float = 0.25
    iou: float = 0.6
    imgsz: int = 1280
    half: bool = True


def parse_track_results(
    *,
    xyxy: np.ndarray,
    conf: np.ndarray,
    cls: np.ndarray,
    track_ids: np.ndarray,
    frame_info: FrameInfo,
    class_map: dict[int, ClassName],
    tracker_name: str,
) -> list[TrackRecord]:
    """Pure function: turn a frame's tracked-box arrays into TrackRecords.

    Behaviour mirrors `detection.parse_results` (clamp + degenerate drop)
    and additionally requires a valid integer track id. Detections without
    a confirmed track id should be filtered out by the caller before
    invoking this function (see `BotSortTracker.track`).
    """
    n = xyxy.shape[0]
    if n == 0:
        return []
    if not (n == conf.shape[0] == cls.shape[0] == track_ids.shape[0]):
        raise ValueError(
            "shape mismatch: "
            f"xyxy={xyxy.shape}, conf={conf.shape}, "
            f"cls={cls.shape}, track_ids={track_ids.shape}"
        )

    w = float(frame_info.width)
    h = float(frame_info.height)
    out: list[TrackRecord] = []

    for i in range(n):
        cls_id = int(cls[i])
        cn = class_map.get(cls_id)
        if cn is None:
            continue
        tid = int(track_ids[i])
        if tid < 0:
            continue

        x1, y1, x2, y2 = (float(v) for v in xyxy[i])
        x1 = max(0.0, min(x1, w))
        y1 = max(0.0, min(y1, h))
        x2 = max(0.0, min(x2, w))
        y2 = max(0.0, min(y2, h))
        if x2 <= x1 or y2 <= y1:
            continue

        out.append(
            TrackRecord(
                video_id=frame_info.video_id,
                segment_id=frame_info.segment_id,
                frame_id=frame_info.frame_id,
                timestamp_ms=frame_info.timestamp_ms,
                track_id=tid,
                class_name=cn,
                conf=float(conf[i]),
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                tracker_name=tracker_name,
                source_track_id=tid,
                stitched_track_id=None,
            )
        )
    return out


class BotSortTracker:
    """Stateful wrapper around ultralytics' `model.track(...)` per-frame API.

    One instance per video. State is held inside the underlying ultralytics
    predictor; `persist=True` is sent on every call after the first so the
    tracker keeps assigning ids continuously across frames.
    """

    def __init__(self, config: BotSortConfig) -> None:
        from ultralytics import YOLO

        self._cfg = config
        self._model = YOLO(config.model_path)

        raw_names = self._model.names
        if isinstance(raw_names, dict):
            names_dict = {int(k): str(v) for k, v in raw_names.items()}
        else:
            names_dict = dict(enumerate(raw_names))
        self._class_map = build_class_map(names_dict)

        self._tracker_name = TRACKER_NAME
        self._model_path_basename = Path(config.model_path).name
        self._first_call = True

    @property
    def tracker_name(self) -> str:
        return self._tracker_name

    @property
    def class_map(self) -> dict[int, ClassName]:
        return dict(self._class_map)

    def reset(self) -> None:
        """Force the next call to (re)initialize the underlying tracker."""
        self._first_call = True

    def track(self, frame: np.ndarray, frame_info: FrameInfo) -> list[TrackRecord]:
        results = self._model.track(
            frame,
            persist=not self._first_call,
            tracker=self._cfg.tracker_path,
            conf=self._cfg.conf,
            iou=self._cfg.iou,
            imgsz=self._cfg.imgsz,
            device=self._cfg.device,
            half=self._cfg.half,
            verbose=False,
        )
        self._first_call = False

        if not results:
            return []
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0 or boxes.id is None:
            return []

        return parse_track_results(
            xyxy=boxes.xyxy.cpu().numpy(),
            conf=boxes.conf.cpu().numpy(),
            cls=boxes.cls.cpu().numpy(),
            track_ids=boxes.id.cpu().numpy().astype(np.int64),
            frame_info=frame_info,
            class_map=self._class_map,
            tracker_name=self._tracker_name,
        )
