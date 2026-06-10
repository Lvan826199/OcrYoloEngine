# 自定义 YOLO 模型训练教程（端到端）

> 目标：从「一堆游戏截图」走到「服务能通过 `/v1/detect` 找到你的目标」。
> 本目录与服务**严格隔离**：服务运行时绝不 import `training/`（有测试 `test_training_isolation.py` 守门）。
> 教程中的每条命令都在 CPU 环境真实跑通过（2026-06-10），文中数字为真实运行结果。

## 0. 环境准备

```bash
uv sync --extra dev --extra yolo     # 安装 ultralytics(YOLO 训练与推理框架)
```

## 1. 五分钟 demo：先把全流程跑通（零标注）

不用准备任何数据，先用仓库自带的合成数据集体验「生成数据 → 训练 → 上线服务」闭环，
确认环境没问题，再投入真实数据。

### 1.1 生成 demo 数据集

```bash
uv run python training/make_demo_dataset.py --out training/demo_dataset
```

生成 40 训练 + 10 验证张「游戏风格」图：深色噪点背景上随机散布两类目标——
`enemy`（红方块）和 `coin`（金币圆），标签自动写好（YOLO 格式）。

### 1.2 训练

```bash
uv run python training/train.py --data training/demo_dataset/data.yaml --epochs 40 --imgsz 320
```

CPU 上约 3 分钟。训练完脚本会打印最优权重路径与接入服务的三步提示。

### 1.3 上线到服务并验证

```bash
mkdir -p models_store && cp runs/detect/train/weights/best.pt models_store/demo_game.pt
cp configs/models.yaml.example configs/models.yaml   # 已有则跳过
```

在 `configs/models.yaml` 追加登记（**classes 索引必须与 data.yaml 的 names 一致**）：

```yaml
  demo_game:
    path: models_store/demo_game.pt
    version: v1
    classes:
      0: enemy
      1: coin
```

启动服务并发一张验证图：

```bash
uv run ocr-yolo serve &
uv run python - <<'EOF'
import base64, json, urllib.request
with open("training/demo_dataset/images/val/val_000.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()
req = urllib.request.Request(
    "http://localhost:8000/v1/detect",
    data=json.dumps({"image": {"base64": b64}, "methods": ["yolo"],
                     "model": "demo_game", "conf_threshold": 0.5}).encode(),
    headers={"Content-Type": "application/json"})
print(json.load(urllib.request.urlopen(req)))
EOF
```

能看到 `enemy` / `coin` 的检测框和坐标，闭环就通了。

真实运行结果参考（CPU，40 轮训练 2.2 分钟，验证集 mAP50:enemy 0.995 / coin 0.995）：

```text
enemy conf=0.86 center_norm=[0.565, 0.389]   # 真值 (0.563, 0.388)
enemy conf=0.68 center_norm=[0.241, 0.736]   # 真值 (0.239, 0.733)
coin  conf=0.63 center_norm=[0.621, 0.706]   # 真值 (0.620, 0.708)
```

检出坐标与数据集生成时的真值偏差 <0.005——训练、上线、识别整条链路工作正常。

## 2. 真实业务流程（用你自己的游戏截图）

### 2.1 采集截图

- 用你的自动化脚本**批量截图**，分辨率与生产环境一致（识别时是什么样，训练时就喂什么样）。
- 数量参考：**每个类别 100~300 个实例**起步；覆盖目标的不同状态（大小、位置、被遮挡、不同场景背景）。
- 负样本（不含目标的纯背景图）也放一些，能显著降低误报。

### 2.2 标注（YOLO 格式）

推荐标注工具（任选其一，导出格式选 **YOLO**）：

| 工具 | 特点 |
|---|---|
| [labelImg](https://github.com/HumanSignal/labelImg) | 经典桌面工具，简单直接 |
| [X-AnyLabeling](https://github.com/CVHub520/X-AnyLabeling) | 支持模型辅助预标注，量大时省力 |
| [Roboflow](https://roboflow.com/) | 在线平台，团队协作方便 |

YOLO 标签格式：每张图配一个**同名 `.txt`**，每行一个目标：

```
<类别索引> <中心x> <中心y> <宽> <高>     # 均为 0~1 归一化值
```

### 2.2.1 标注量大怎么办：预标注自举（强烈推荐）

几千张截图全靠手画框不现实。正确姿势是**让模型替你画初稿，人只做修正**，
每循环一轮人工成本就降一截：

1. **先人工标一小批**（每类 50~100 个实例），按 2.3/2.4 训出第一版模型——质量不用高，能用就行。
2. **用第一版模型批量预标注**剩下的截图（实测可用，输出就是标准 YOLO 标签）：

   ```bash
   uv run yolo predict model=runs/detect/train/weights/best.pt \
       source=/path/to/未标注截图目录 save_txt conf=0.4
   # 标签输出在 runs/detect/predict/labels/*.txt(与图同名,5 列 YOLO 格式)
   ```

   `conf` 故意设低一点（0.4），宁可多框让人删，也别漏框让人补——删比画快得多。
3. **导入标注工具只做修正**：把预标签和图片一起载入 labelImg / X-AnyLabeling，
   人工只负责删误框、补漏框、修边界，不再从零画。
4. **合入训练集重训**，回到第 2 步用新模型预标注下一批。模型越练越准，预标越准，人改得越少。

> 实测参考：用 demo 数据集 40 轮的模型预标注验证集，预标坐标与人工真值偏差 <0.003，
> 基本只剩"过目确认"的工作量。X-AnyLabeling 还支持直接挂载你的 `best.pt` 在标注界面内实时辅助，效果等价。

### 2.3 组织数据集

```
dataset/
├── images/
│   ├── train/*.png        # 训练集(约 80%)
│   └── val/*.png          # 验证集(约 20%,不参与训练,用来检验效果)
├── labels/
│   ├── train/*.txt        # 与图片同名配对
│   └── val/*.txt
└── data.yaml
```

`data.yaml`（可参考 demo 生成的 `training/demo_dataset/data.yaml`）：

```yaml
path: /绝对路径/dataset    # 写绝对路径最稳
train: images/train
val: images/val
names:
  0: boss        # ⚠️ 这里的索引顺序就是日后服务端 classes 的索引顺序
  1: coin
```

### 2.4 训练

```bash
uv run python training/train.py --data /path/to/dataset/data.yaml --epochs 100 --imgsz 640
```

| 参数 | 说明 | 经验值 |
|---|---|---|
| `--epochs` | 训练轮数 | 真实数据 100 起步；验证指标不再涨就可以停 |
| `--imgsz` | 训练分辨率 | 与截图短边接近即可；640 是常用值，目标很小用 960 |
| `--weights` | 预训练底座 | 默认 `yolov8n.pt`(最快)；要更准可换 `yolov8s.pt` |
| `--device` | 计算设备 | 默认自动选（有 GPU 用 GPU）；显式指定用 `0` 或 `cpu` |

> GPU 训练参数同样适用（`--device 0`），速度通常快一个数量级；本教程在 CPU 环境实测。

### 2.5 看懂训练结果

产物在 `runs/detect/train/`：

- `weights/best.pt`：验证集表现最好的权重（**上线用这个**）；`last.pt` 是最后一轮。
- `results.png`：损失与 mAP 曲线。曲线还在明显下降/上升说明轮数不够。
- `val_batch*_pred.jpg`：验证集预测可视化，肉眼检查检出框对不对。
- 终端末尾的指标表：重点看 **mAP50**（≥0.9 通常够自动化测试用）。每类一行，哪类弱一目了然——
  demo 数据集 5 轮时 coin 只有 0.10，40 轮后两类都到 0.99+，轮数的作用就在这。

### 2.6 上线到服务

与 1.3 相同：权重放 `models_store/`，`configs/models.yaml` 登记（classes 与 `data.yaml` 的
names **逐索引一致**），服务在跑则 `POST /v1/models/<名字>/reload` 热加载，不用重启。

### 2.7 迭代改进

1. 生产中漏检/误检的截图收集回来 → 标注 → 加入训练集 → 重训。
2. `models.yaml` 里 `version` 递增（如 v1 → v2），方便从响应的 `model_version` 字段确认生效。
3. 换权重文件后调一次 `reload` 即可热替换，识别请求无需中断。

## 3. 常见问题

- **服务返回的 label 是数字不是名字？** `configs/models.yaml` 的 `classes` 没登记或索引与训练时的 `names` 对不上。
- **训练很慢？** 用 GPU（`--device 0`）；或先把 `--imgsz` 降到 320~480 做快速实验，定稿再用大分辨率。
- **检出框抖动/置信度忽高忽低？** 训练数据里该状态的样本不足，按 2.7 补样本重训。
- **`models.yaml` 改了不生效？** 服务启动时读取一次；改配置文件后需重启服务（改权重文件则 `reload` 即可）。
