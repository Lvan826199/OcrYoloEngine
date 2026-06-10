"""YOLO 训练脚本(基于 ultralytics)。与服务隔离,服务运行时不导入本文件。"""

from __future__ import annotations

import argparse
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description="训练 YOLO 模型")
    parser.add_argument("--data", required=True, help="数据集 yaml 路径")
    parser.add_argument("--weights", default="yolov8n.pt", help="预训练权重")
    parser.add_argument("--epochs", type=int, default=100)
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument(
        "--device",
        default=None,
        help="计算设备:GPU id(如 '0')或 'cpu';默认自动选择(有 GPU 用 GPU,否则 CPU)",
    )
    args = parser.parse_args()

    from ultralytics import YOLO  # 懒加载

    model = YOLO(args.weights)
    model.train(data=args.data, epochs=args.epochs, imgsz=args.imgsz, device=args.device)

    best = Path(str(model.trainer.best)).resolve()
    print("\n================ 训练完成 ================")
    print(f"最优权重:{best}")
    print("接入服务三步:")
    print(f"  1. 把权重放到服务可读路径,如:cp {best} models_store/my_model.pt")
    print("  2. 在 configs/models.yaml 登记(path/version/classes,类别索引与 data.yaml 一致)")
    print("  3. 服务已在跑则调 POST /v1/models/my_model/reload,否则直接启动服务即可")


if __name__ == "__main__":
    main()
