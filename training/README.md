# 训练入口（与服务隔离）

本目录用于训练 YOLO 模型,**服务运行时绝不 import 本目录**。
产出权重放到 `../models_store/`,再在 `../configs/models.yaml` 登记即可被服务加载。

## 用法

```bash
uv pip install ultralytics
python training/train.py --data training/configs/example.yaml --epochs 100 --weights yolov8n.pt
```

数据集与标注格式见 [`dataset.md`](dataset.md)。
