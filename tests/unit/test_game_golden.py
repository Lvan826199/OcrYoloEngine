"""真实游戏截图回归:从入库的 SuperTuxKart 菜单截图裁真实按钮图标,再用模板匹配找回。

最贴近本服务的实际使用场景(游戏自动化测试找按钮点击)。样例图来源与许可见
tests/fixtures/README.md;期望结果在 game_menu.expected.json。
全部真实数据 + 真实 TemplateRecognizer,无 mock。
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import cv2
import numpy as np

from ocr_yolo_engine.preprocessing.pipeline import finalize_detections, to_rgb
from ocr_yolo_engine.recognizers.base import InferContext
from ocr_yolo_engine.recognizers.template import TemplateRecognizer
from ocr_yolo_engine.templates.store import TemplateSpec, TemplateStore

_FIXTURES = Path(__file__).resolve().parent.parent / "fixtures"


def _load_expected() -> dict:
    with (_FIXTURES / "game_menu.expected.json").open(encoding="utf-8") as f:
        return json.load(f)


def _build_store(tmp_path: Path, expected: dict, params: dict) -> tuple[TemplateStore, np.ndarray]:
    """从入库菜单截图按 expected 的裁剪框裁出真实按钮图标,落盘注册为模板。"""
    scene = cv2.imread(str(_FIXTURES / expected["scene"]), cv2.IMREAD_COLOR)
    assert scene is not None, "游戏菜单样例图应可读取"
    h, w = scene.shape[:2]
    assert [w, h] == expected["scene_size"]

    crop = expected["template_crop"]
    tpl = scene[crop["y"] : crop["y"] + crop["h"], crop["x"] : crop["x"] + crop["w"]]
    tpl_path = tmp_path / "game_button.png"
    assert cv2.imwrite(str(tpl_path), tpl)
    store = TemplateStore(
        {
            "game_button": TemplateSpec(
                name="game_button", path=str(tpl_path), version="v1", params=params
            )
        }
    )
    return store, scene


def test_game_menu_button_template_match(tmp_path):
    """高阈值(0.97)下应精确找回按钮:中心在期望点 ±3px,置信度 ≥0.99。

    真实画面打分偏高(深色背景区域可达 ~0.96),0.97 阈值能把真命中(≈1.0)
    与"长得有点像"的区域拉开——这也是使用文档建议的模板配置方式。
    """
    expected = _load_expected()
    store, scene = _build_store(tmp_path, expected, params={"threshold": 0.97})
    recognizer = TemplateRecognizer(store=store)

    full_h, full_w = scene.shape[:2]
    raws = recognizer.infer(
        to_rgb(scene), InferContext(conf_threshold=0.25, templates=["game_button"])
    )
    dets = finalize_detections(list(raws), offset=(0, 0), full_w=full_w, full_h=full_h)

    assert dets, "应在菜单截图中找回裁出的按钮"
    best = max(dets, key=lambda d: d.confidence)
    tol = expected["tolerance_px"]
    assert abs(best.center[0] - expected["center"][0]) <= tol
    assert abs(best.center[1] - expected["center"][1]) <= tol
    assert best.confidence >= expected["min_confidence"]


def test_game_menu_template_fallback_is_bounded(tmp_path):
    """模板未配 threshold + 低请求阈值:真实复杂画面上防爆炸保护必须兜住。

    回退阈值有 0.5 下限、每尺度候选 top-200 截断——结果数有界、秒级返回,
    且最高分仍是真命中位置(防护不伤正确性)。
    """
    expected = _load_expected()
    store, scene = _build_store(tmp_path, expected, params={})
    recognizer = TemplateRecognizer(store=store)

    started = time.perf_counter()
    raws = recognizer.infer(
        to_rgb(scene), InferContext(conf_threshold=0.25, templates=["game_button"])
    )
    elapsed = time.perf_counter() - started

    assert elapsed < 10, f"防爆炸保护下应秒级返回,实际 {elapsed:.1f}s"
    assert len(raws) <= 1000, "结果数应被每尺度候选上限约束"
    best = max(raws, key=lambda d: d.confidence)
    cx = (best.bbox[0] + best.bbox[2]) / 2
    cy = (best.bbox[1] + best.bbox[3]) / 2
    tol = expected["tolerance_px"]
    assert abs(cx - expected["center"][0]) <= tol
    assert abs(cy - expected["center"][1]) <= tol
