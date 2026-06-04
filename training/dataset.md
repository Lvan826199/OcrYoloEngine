# 数据集与标注约定（YOLO 格式）

```
dataset/
├── images/{train,val}/*.jpg
├── labels/{train,val}/*.txt   # 每行: <cls> <cx> <cy> <w> <h>（归一化 0~1）
└── data.yaml                  # train/val 路径 + names 类别表
```

`data.yaml` 中的 `names` 顺序必须与服务端 `configs/models.yaml` 的 `classes` 索引一致。
