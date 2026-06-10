"""生成合成「游戏风格」demo 数据集(YOLO 格式),供训练教程零标注成本走通全流程。

两类目标随机散布在深色噪点背景上(模拟游戏画面):
- enemy(类别 0):红色方块(带亮边框);
- coin(类别 1):金黄色圆(带高光点)。

同时写出归一化 YOLO 标签与 data.yaml。仅依赖 numpy/cv2,CPU 秒级完成。

用法:
  uv run python training/make_demo_dataset.py --out training/demo_dataset
"""

from __future__ import annotations

import argparse
from pathlib import Path

import cv2
import numpy as np

NAMES = {0: "enemy", 1: "coin"}


def _draw_enemy(img: np.ndarray, x: int, y: int, size: int) -> None:
    cv2.rectangle(img, (x, y), (x + size, y + size), (40, 40, 200), -1)
    cv2.rectangle(img, (x, y), (x + size, y + size), (80, 80, 255), 2)


def _draw_coin(img: np.ndarray, x: int, y: int, size: int) -> None:
    r = size // 2
    center = (x + r, y + r)
    cv2.circle(img, center, r, (40, 200, 230), -1)
    cv2.circle(img, center, r, (20, 150, 180), 2)
    cv2.circle(img, (center[0] - r // 3, center[1] - r // 3), max(2, r // 4), (160, 240, 255), -1)


def _make_image(rng: np.random.Generator, imgsz: int) -> tuple[np.ndarray, list[str]]:
    """生成一张含 1~4 个目标的图,返回 (BGR 图, YOLO 标签行)。"""
    # 深色噪点背景,模拟游戏场景纹理。
    img = rng.integers(20, 70, size=(imgsz, imgsz, 3), dtype=np.uint8).astype(np.uint8)
    labels: list[str] = []
    occupied: list[tuple[int, int, int, int]] = []
    for _ in range(int(rng.integers(1, 5))):
        size = int(rng.integers(imgsz // 10, imgsz // 4))
        for _attempt in range(20):  # 简单避让:与已放目标不重叠才落位
            x = int(rng.integers(0, imgsz - size))
            y = int(rng.integers(0, imgsz - size))
            if all(
                x + size <= ox or x >= ox + ow or y + size <= oy or y >= oy + oh
                for ox, oy, ow, oh in occupied
            ):
                break
        else:
            continue
        occupied.append((x, y, size, size))
        cls = int(rng.integers(0, 2))
        if cls == 0:
            _draw_enemy(img, x, y, size)
        else:
            _draw_coin(img, x, y, size)
        cx = (x + size / 2) / imgsz
        cy = (y + size / 2) / imgsz
        w = size / imgsz
        labels.append(f"{cls} {cx:.6f} {cy:.6f} {w:.6f} {w:.6f}")
    return img, labels


def generate(out: Path, train: int, val: int, imgsz: int, seed: int) -> None:
    rng = np.random.default_rng(seed)
    for split, count in (("train", train), ("val", val)):
        img_dir = out / "images" / split
        label_dir = out / "labels" / split
        img_dir.mkdir(parents=True, exist_ok=True)
        label_dir.mkdir(parents=True, exist_ok=True)
        for i in range(count):
            while True:  # 个别图可能避让失败导致零目标,重新生成保证每图至少一个
                img, labels = _make_image(rng, imgsz)
                if labels:
                    break
            stem = f"{split}_{i:03d}"
            cv2.imwrite(str(img_dir / f"{stem}.png"), img)
            (label_dir / f"{stem}.txt").write_text("\n".join(labels) + "\n", encoding="utf-8")

    names_lines = "\n".join(f"  {idx}: {name}" for idx, name in NAMES.items())
    (out / "data.yaml").write_text(
        f"path: {out.resolve()}\ntrain: images/train\nval: images/val\nnames:\n{names_lines}\n",
        encoding="utf-8",
    )
    print(f"demo 数据集已生成:{out.resolve()}")
    print(f"  train={train} 张,val={val} 张,类别:{NAMES}")
    print(f"  下一步训练:uv run python training/train.py --data {out / 'data.yaml'} --epochs 5")


def main() -> None:
    parser = argparse.ArgumentParser(description="生成 YOLO demo 数据集(合成游戏风格)")
    parser.add_argument("--out", default="training/demo_dataset", help="输出目录")
    parser.add_argument("--train", type=int, default=40, help="训练集张数")
    parser.add_argument("--val", type=int, default=10, help="验证集张数")
    parser.add_argument("--imgsz", type=int, default=320, help="图片边长(像素)")
    parser.add_argument("--seed", type=int, default=42, help="随机种子(可复现)")
    args = parser.parse_args()
    generate(Path(args.out), args.train, args.val, args.imgsz, args.seed)


if __name__ == "__main__":
    main()
