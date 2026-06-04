"""YOLO 训练脚本(基于 ultralytics)。与服务隔离,服务运行时不导入本文件。"""

from __future__ import annotations

import argparse


def main() -> None:
    parser = argparse.ArgumentParser(description="训练 YOLO 模型")
    parser.add_argument("--data", required=True, help="数据集 yaml 路径")
    parser.add_argument("--weights", default="yolov8n.pt", help="预训练权重")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--device", default="0", help="GPU id 或 'cpu'")
    args = parser.parse_args()

    from ultralytics import YOLO  # 懒加载

    model = YOLO(args.weights)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, device=args.device)


if __name__ == "__main__":
    main()
