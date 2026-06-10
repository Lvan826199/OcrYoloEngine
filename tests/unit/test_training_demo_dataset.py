"""demo 数据集生成器单测:以真实 CLI 调用生成到临时目录,校验 YOLO 数据集合法性。

training/ 与 src 隔离(不打包、不被服务 import),故用 subprocess 真实执行脚本,
与用户在教程里的用法完全一致。
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import cv2
import yaml

_SCRIPT = Path(__file__).resolve().parents[2] / "training" / "make_demo_dataset.py"


def _generate(out: Path, train: int = 4, val: int = 2) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [
            sys.executable,
            str(_SCRIPT),
            "--out",
            str(out),
            "--train",
            str(train),
            "--val",
            str(val),
            "--seed",
            "7",
        ],
        capture_output=True,
        text=True,
        check=True,
    )


def test_demo_dataset_structure_and_labels(tmp_path):
    """生成的数据集:目录齐全、图可解码、标签为合法 YOLO 格式(坐标 0~1)。"""
    out = tmp_path / "ds"
    _generate(out, train=4, val=2)

    for split, count in (("train", 4), ("val", 2)):
        images = sorted((out / "images" / split).glob("*.png"))
        labels = sorted((out / "labels" / split).glob("*.txt"))
        assert len(images) == count
        assert len(labels) == count
        for img_path, label_path in zip(images, labels, strict=True):
            assert img_path.stem == label_path.stem, "图与标签应同名配对"
            img = cv2.imread(str(img_path))
            assert img is not None, "生成的图片应可解码"
            lines = label_path.read_text(encoding="utf-8").strip().splitlines()
            assert lines, "每张图至少应有一个目标"
            for line in lines:
                parts = line.split()
                assert len(parts) == 5, f"YOLO 标签应为 5 列:{line!r}"
                cls = int(parts[0])
                assert cls in (0, 1)
                cx, cy, w, h = (float(v) for v in parts[1:])
                assert 0 < cx < 1 and 0 < cy < 1
                assert 0 < w < 1 and 0 < h < 1
                # 框不得越界(中心 ± 半宽/半高仍在 0~1 内)。
                assert cx - w / 2 >= 0 and cx + w / 2 <= 1
                assert cy - h / 2 >= 0 and cy + h / 2 <= 1


def test_demo_dataset_data_yaml_matches_layout(tmp_path):
    """data.yaml:路径指向生成目录,names 为 enemy/coin 且索引连续。"""
    out = tmp_path / "ds"
    _generate(out)
    data = yaml.safe_load((out / "data.yaml").read_text(encoding="utf-8"))
    assert Path(data["path"]) == out.resolve()
    assert data["train"] == "images/train"
    assert data["val"] == "images/val"
    assert data["names"] == {0: "enemy", 1: "coin"}


def test_demo_dataset_deterministic_with_seed(tmp_path):
    """同 seed 两次生成的标签完全一致(可复现,便于教程对照)。"""
    a, b = tmp_path / "a", tmp_path / "b"
    _generate(a)
    _generate(b)
    labels_a = sorted((a / "labels" / "train").glob("*.txt"))
    labels_b = sorted((b / "labels" / "train").glob("*.txt"))
    for la, lb in zip(labels_a, labels_b, strict=True):
        assert la.read_text(encoding="utf-8") == lb.read_text(encoding="utf-8")
