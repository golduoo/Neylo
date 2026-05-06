"""YOLO11 detection service via ultralytics."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np

from neylo.schemas import ClassName, DetectionRecord, FrameInfo

DETECTOR_NAME = "ultralytics-yolo11"

# COCO class id 0 is `person`. Phase 1 uses pretrained COCO weights, so all
# detected people collapse into `player`. Goalkeeper/referee separation
# requires a fine-tuned model (Phase 2).
COCO_PERSON_CLASS_ID = 0


@dataclass(frozen=True)
class YoloConfig:
    """Subset of pipeline.yaml `detection` section consumed by YoloDetector."""

    model_path: str
    device: str = "cuda:0"
    conf: float = 0.25
    iou: float = 0.6
    imgsz: int = 1280
    half: bool = True


def build_class_map(model_names: dict[int, str]) -> dict[int, ClassName]:
    """Map detector class ids to Neylo `ClassName`.

    v1 has a single class (`player`). Two cases handled:

    1. Model trained on our merged label set: any class named exactly
       `player` is mapped to `ClassName.PLAYER`. Other classes (e.g.
       `ball`, `referee` from a richer source dataset) are dropped.
    2. Otherwise (e.g. COCO pretrained): id 0 (`person`) is mapped to
       `player`; the rest are dropped.
    """
    matches = {i: name for i, name in model_names.items() if name == ClassName.PLAYER.value}
    if matches:
        return {i: ClassName.PLAYER for i in matches}
    return {COCO_PERSON_CLASS_ID: ClassName.PLAYER}


def parse_results(
    *,
    xyxy: np.ndarray,
    conf: np.ndarray,
    cls: np.ndarray,
    frame_info: FrameInfo,
    class_map: dict[int, ClassName],
    detector_name: str,
    model_version: str,
) -> list[DetectionRecord]:
    """Pure function: turn raw YOLO arrays into DetectionRecord list.

    Boxes outside the frame are clamped, and degenerate boxes (zero
    width or height after clamping) are dropped.
    """
    if xyxy.shape[0] == 0:
        return []
    if not (xyxy.shape[0] == conf.shape[0] == cls.shape[0]):
        raise ValueError(
            f"shape mismatch: xyxy={xyxy.shape}, conf={conf.shape}, cls={cls.shape}"
        )

    w = float(frame_info.width)
    h = float(frame_info.height)
    out: list[DetectionRecord] = []

    for i in range(xyxy.shape[0]):
        cls_id = int(cls[i])
        cn = class_map.get(cls_id)
        if cn is None:
            continue

        x1, y1, x2, y2 = (float(v) for v in xyxy[i])
        x1 = max(0.0, min(x1, w))
        y1 = max(0.0, min(y1, h))
        x2 = max(0.0, min(x2, w))
        y2 = max(0.0, min(y2, h))
        if x2 <= x1 or y2 <= y1:
            continue

        out.append(
            DetectionRecord(
                video_id=frame_info.video_id,
                segment_id=frame_info.segment_id,
                frame_id=frame_info.frame_id,
                timestamp_ms=frame_info.timestamp_ms,
                class_name=cn,
                conf=float(conf[i]),
                x1=x1,
                y1=y1,
                x2=x2,
                y2=y2,
                detector_name=detector_name,
                model_version=model_version,
            )
        )
    return out


class YoloDetector:
    """Stateful wrapper around ultralytics YOLO. One instance per pipeline run.

    Loads weights eagerly in `__init__` (so the cost is paid once and
    visible in logs). For tests, parsing logic is exposed as the
    standalone `parse_results` function — no model needed.
    """

    def __init__(self, config: YoloConfig) -> None:
        from ultralytics import YOLO  # heavy import; defer to construction

        self._cfg = config
        self._model = YOLO(config.model_path)
        # `model.names` may be a dict[int,str] or a list[str] depending on
        # ultralytics version; normalize to dict.
        raw_names = self._model.names
        if isinstance(raw_names, dict):
            names_dict = {int(k): str(v) for k, v in raw_names.items()}
        else:
            names_dict = dict(enumerate(raw_names))
        self._class_map = build_class_map(names_dict)
        self._detector_name = DETECTOR_NAME
        self._model_version = Path(config.model_path).name

    @property
    def detector_name(self) -> str:
        return self._detector_name

    @property
    def model_version(self) -> str:
        return self._model_version

    @property
    def class_map(self) -> dict[int, ClassName]:
        return dict(self._class_map)

    def detect(self, frame: np.ndarray, frame_info: FrameInfo) -> list[DetectionRecord]:
        """Run inference on a single BGR frame and return DetectionRecords."""
        results = self._model.predict(
            frame,
            conf=self._cfg.conf,
            iou=self._cfg.iou,
            imgsz=self._cfg.imgsz,
            device=self._cfg.device,
            half=self._cfg.half,
            verbose=False,
        )
        if not results:
            return []
        boxes = results[0].boxes
        if boxes is None or len(boxes) == 0:
            return []
        return parse_results(
            xyxy=boxes.xyxy.cpu().numpy(),
            conf=boxes.conf.cpu().numpy(),
            cls=boxes.cls.cpu().numpy(),
            frame_info=frame_info,
            class_map=self._class_map,
            detector_name=self._detector_name,
            model_version=self._model_version,
        )
