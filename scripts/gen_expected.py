"""对 tests/fixtures 样例图跑真实识别,生成 expected.json 草稿。

期望值必须出自真实运行(规范见 tests/fixtures/README.md):本脚本负责
「跑真实识别 → 输出草稿 JSON」,容差与 min_confidence 由人工审定后入库。

用法示例:
  uv run python scripts/gen_expected.py tests/fixtures/game_race.jpg --ocr --yolo yolov8n
  uv run python scripts/gen_expected.py tests/fixtures/game_menu.png \
      --template-crop 662,348,96,112 --template-name game_button
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile

import cv2

from ocr_yolo_engine.recognizers.base import InferContext

# 草稿默认容差(像素),与 fixtures README 的起步值一致;入库前人工审定。
DEFAULT_TOL = {"template": 3, "ocr": 15, "yolo": 40}


def _center(bbox: list[float]) -> list[float]:
    return [round((bbox[0] + bbox[2]) / 2, 1), round((bbox[1] + bbox[3]) / 2, 1)]


def gen_ocr(scene_bgr) -> list[dict]:  # type: ignore[no-untyped-def]
    from ocr_yolo_engine.recognizers.ocr import OcrRecognizer

    rgb = cv2.cvtColor(scene_bgr, cv2.COLOR_BGR2RGB)
    out = OcrRecognizer().infer(rgb, InferContext(conf_threshold=0.5))
    return [
        {
            "text_contains": d.text,
            "center": _center(d.bbox),
            "tolerance_px": DEFAULT_TOL["ocr"],
        }
        for d in out
    ]


def gen_yolo(scene_bgr, model: str) -> list[dict]:  # type: ignore[no-untyped-def]
    from ocr_yolo_engine.config_loader import load_model_specs
    from ocr_yolo_engine.models.registry import ModelRegistry
    from ocr_yolo_engine.recognizers.yolo import YoloRecognizer, load_yolo_model
    from ocr_yolo_engine.settings import get_settings

    specs = load_model_specs(get_settings().models_config_path)
    if model not in specs:
        sys.exit(f"模型 {model} 未在 configs/models.yaml(.example) 登记")
    registry = ModelRegistry(specs, loader_fn=load_yolo_model, cache_size=1)
    out = YoloRecognizer(registry=registry).infer(
        scene_bgr, InferContext(conf_threshold=0.25, model=model)
    )
    return [
        {
            "model": model,
            "label": d.label,
            "center": _center(d.bbox),
            "tolerance_px": DEFAULT_TOL["yolo"],
            "min_confidence": round(d.confidence, 2),
        }
        for d in out
    ]


def gen_template(scene_bgr, crop: tuple[int, int, int, int], name: str) -> list[dict]:  # type: ignore[no-untyped-def]
    from ocr_yolo_engine.preprocessing.pipeline import to_rgb
    from ocr_yolo_engine.recognizers.template import TemplateRecognizer
    from ocr_yolo_engine.templates.store import TemplateSpec, TemplateStore

    x, y, w, h = crop
    tpl = scene_bgr[y : y + h, x : x + w]
    with tempfile.TemporaryDirectory(prefix="oye_gen_expected_") as tmp:
        tpl_path = os.path.join(tmp, f"{name}.png")
        cv2.imwrite(tpl_path, tpl)
        spec = TemplateSpec(name=name, path=tpl_path, version="draft", params={"threshold": 0.97})
        store = TemplateStore({name: spec})
        out = TemplateRecognizer(store=store).infer(
            to_rgb(scene_bgr), InferContext(conf_threshold=0.25, templates=[name])
        )
    if not out:
        sys.exit("模板在场景中未找回(threshold=0.97),请检查裁剪框")
    best = max(out, key=lambda d: d.confidence)
    return [
        {
            "name": name,
            "crop": {"x": x, "y": y, "w": w, "h": h},
            "center": _center(best.bbox),
            "tolerance_px": DEFAULT_TOL["template"],
            "min_confidence": round(best.confidence, 2),
        }
    ]


def main() -> int:
    parser = argparse.ArgumentParser(description="对样例图跑真实识别,生成 expected.json 草稿")
    parser.add_argument("scene", help="样例图路径(tests/fixtures/ 下)")
    parser.add_argument("--ocr", action="store_true", help="生成 OCR 期望(需 paddleocr)")
    parser.add_argument(
        "--yolo", metavar="MODEL", help="生成 YOLO 期望(需 ultralytics 与已登记模型)"
    )
    parser.add_argument("--template-crop", metavar="X,Y,W,H", help="从场景裁模板并生成模板期望")
    parser.add_argument("--template-name", default="patch", help="模板名(配合 --template-crop)")
    args = parser.parse_args()

    scene_bgr = cv2.imread(args.scene, cv2.IMREAD_COLOR)
    if scene_bgr is None:
        sys.exit(f"无法读取样例图:{args.scene}")
    h, w = scene_bgr.shape[:2]

    expectations: dict[str, list[dict]] = {}
    if args.template_crop:
        crop = tuple(int(v) for v in args.template_crop.split(","))
        if len(crop) != 4:
            sys.exit("--template-crop 需要 X,Y,W,H 四个整数")
        expectations["template"] = gen_template(scene_bgr, crop, args.template_name)
    if args.ocr:
        expectations["ocr"] = gen_ocr(scene_bgr)
    if args.yolo:
        expectations["yolo"] = gen_yolo(scene_bgr, args.yolo)
    if not expectations:
        parser.error("至少指定一种期望:--ocr / --yolo MODEL / --template-crop X,Y,W,H")

    draft = {
        "scene": os.path.basename(args.scene),
        "scene_size": [w, h],
        "description": (
            "草稿:由 scripts/gen_expected.py 真实运行生成;"
            "入库前人工审定容差与 min_confidence,并补充场景说明。"
        ),
        "expectations": expectations,
    }
    print(json.dumps(draft, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
