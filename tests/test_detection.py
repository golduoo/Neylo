"""Unit tests for the detection adapter — no GPU, no model load."""

from __future__ import annotations

import numpy as np
import pytest

from neylo.schemas import ClassName, FrameInfo
from neylo.services.detection import (
    DETECTOR_NAME,
    build_class_map,
    parse_results,
)


@pytest.fixture
def frame_info() -> FrameInfo:
    return FrameInfo(
        video_id="v1",
        segment_id="seg_0",
        frame_id=10,
        timestamp_ms=400.0,
        width=1920,
        height=1080,
    )


# ---------- build_class_map ----------

def test_class_map_coco_pretrained():
    coco_names = {0: "person", 1: "bicycle", 32: "sports ball"}
    m = build_class_map(coco_names)
    assert m == {0: ClassName.PLAYER}


def test_class_map_finetuned_neylo_classes():
    names = {0: "player", 1: "goalkeeper", 2: "referee"}
    m = build_class_map(names)
    assert m == {
        0: ClassName.PLAYER,
        1: ClassName.GOALKEEPER,
        2: ClassName.REFEREE,
    }


def test_class_map_finetuned_partial_drops_unknowns():
    names = {0: "player", 1: "goalkeeper", 2: "ball"}
    m = build_class_map(names)
    assert m == {0: ClassName.PLAYER, 1: ClassName.GOALKEEPER}


# ---------- parse_results ----------

def _arrs(boxes_xyxy, confs, clses):
    return (
        np.asarray(boxes_xyxy, dtype=np.float32).reshape(-1, 4),
        np.asarray(confs, dtype=np.float32),
        np.asarray(clses, dtype=np.int64),
    )


def test_parse_empty(frame_info):
    xyxy, conf, cls = _arrs([], [], [])
    out = parse_results(
        xyxy=xyxy, conf=conf, cls=cls,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER},
        detector_name=DETECTOR_NAME,
        model_version="yolo11n.pt",
    )
    assert out == []


def test_parse_filters_unmapped_classes(frame_info):
    xyxy, conf, cls = _arrs(
        [[10, 20, 30, 40], [50, 60, 70, 80]],
        [0.9, 0.8],
        [0, 32],  # 0 = player, 32 not in map
    )
    out = parse_results(
        xyxy=xyxy, conf=conf, cls=cls,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER},
        detector_name=DETECTOR_NAME,
        model_version="yolo11n.pt",
    )
    assert len(out) == 1
    assert out[0].class_name == ClassName.PLAYER
    assert out[0].conf == pytest.approx(0.9)
    assert out[0].x1 == 10 and out[0].y1 == 20
    assert out[0].x2 == 30 and out[0].y2 == 40
    assert out[0].frame_id == frame_info.frame_id
    assert out[0].timestamp_ms == frame_info.timestamp_ms
    assert out[0].detector_name == DETECTOR_NAME
    assert out[0].model_version == "yolo11n.pt"


def test_parse_clamps_out_of_bound_boxes(frame_info):
    # frame is 1920x1080; box exceeds bounds and has slight underflow
    xyxy, conf, cls = _arrs(
        [[-5, -10, 1925, 1090]],
        [0.7],
        [0],
    )
    out = parse_results(
        xyxy=xyxy, conf=conf, cls=cls,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER},
        detector_name=DETECTOR_NAME,
        model_version="yolo11n.pt",
    )
    assert len(out) == 1
    d = out[0]
    assert d.x1 == 0 and d.y1 == 0
    assert d.x2 == 1920 and d.y2 == 1080


def test_parse_drops_degenerate_after_clamp(frame_info):
    # box entirely off the right edge → degenerate after clamp
    xyxy, conf, cls = _arrs(
        [[2000, 100, 2100, 200]],
        [0.6],
        [0],
    )
    out = parse_results(
        xyxy=xyxy, conf=conf, cls=cls,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER},
        detector_name=DETECTOR_NAME,
        model_version="yolo11n.pt",
    )
    assert out == []


def test_parse_shape_mismatch_raises(frame_info):
    xyxy = np.zeros((3, 4), dtype=np.float32)
    conf = np.zeros((3,), dtype=np.float32)
    cls = np.zeros((2,), dtype=np.int64)  # mismatch
    with pytest.raises(ValueError, match="shape mismatch"):
        parse_results(
            xyxy=xyxy, conf=conf, cls=cls,
            frame_info=frame_info,
            class_map={0: ClassName.PLAYER},
            detector_name=DETECTOR_NAME,
            model_version="yolo11n.pt",
        )


def test_parse_propagates_class_map_mapping(frame_info):
    # finetuned model: ids 0/1/2 → player/goalkeeper/referee
    xyxy, conf, cls = _arrs(
        [[10, 20, 30, 40], [50, 60, 70, 80], [100, 110, 130, 150]],
        [0.9, 0.85, 0.7],
        [0, 1, 2],
    )
    out = parse_results(
        xyxy=xyxy, conf=conf, cls=cls,
        frame_info=frame_info,
        class_map={0: ClassName.PLAYER, 1: ClassName.GOALKEEPER, 2: ClassName.REFEREE},
        detector_name=DETECTOR_NAME,
        model_version="finetuned.pt",
    )
    assert [d.class_name for d in out] == [
        ClassName.PLAYER, ClassName.GOALKEEPER, ClassName.REFEREE,
    ]
