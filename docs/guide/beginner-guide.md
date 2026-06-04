# 小白操作文档（从零开始，手把手）

> 假设你**完全没接触过这个项目**,甚至对命令行不太熟。跟着一步步来即可。
> 已经熟练 → 直接看 [快速开始](quickstart.md)。

本文以 **Ubuntu / Linux** 为主,Windows / macOS 的差异在每步备注。

---

## 第 0 步：理解这个服务在干嘛

你有一个自动化测试脚本,它会截图。它想知道"截图里某个按钮/文字在哪个坐标"。
本服务就是收下截图、告诉你坐标和文字的"眼睛"。**它不点击,只识别**。点击还是你的脚本自己做。

所以使用顺序是:**先把这个服务在某台机器上跑起来 → 你的脚本把截图发给它 → 它返回坐标**。

---

## 第 1 步：装 Python(≥ 3.11)

先看有没有:

```bash
python3 --version
```

如果显示 `Python 3.11.x` 或更高,跳过本步。否则:

- Ubuntu:`sudo apt update && sudo apt install -y python3 python3-venv`
- Windows:去 [python.org](https://www.python.org/downloads/) 下载安装,安装时**勾选 "Add Python to PATH"**。
- macOS:`brew install python@3.12`

---

## 第 2 步：装 uv(包管理器)

`uv` 用来装依赖、跑命令,比传统 pip 快很多。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

装完它会提示把一个目录加进 PATH。**关掉终端重开**,或执行:

```bash
source $HOME/.local/bin/env    # 或重开终端
uv --version                   # 能打印版本号就成功
```

> Windows(PowerShell):`powershell -c "irm https://astral.sh/uv/install.ps1 | iex"`

---

## 第 3 步：把代码拿下来

```bash
git clone https://gitee.com/xiaozai-van-liu/OcrYoloEngine.git
cd OcrYoloEngine
```

后面所有命令都在这个 `OcrYoloEngine` 目录里执行。

---

## 第 4 步：装依赖

依赖分两类,按需装:

```bash
# 基础:HTTP 服务 + 模板匹配(不含 YOLO/OCR 的大包)
uv sync

# 要用文字识别(OCR)和目标检测(YOLO),再装这两个 extras:
uv sync --extra yolo --extra ocr
```

> ⚠️ `--extra yolo --extra ocr` 会下载 PyTorch、PaddlePaddle 等大包,首次较慢、占空间(可能 GB 级),耐心等。只想先体验文字识别也可以先只 `uv sync --extra ocr`。

---

## 第 5 步：启动服务

```bash
uv run ocr-yolo serve
```

看到类似 `Uvicorn running on http://0.0.0.0:8000` 就成功了。**这个终端要一直开着**(服务在前台运行)。

验证(**另开一个终端**):

```bash
curl http://localhost:8000/health
```

返回 `{"status":"ok"}` 即正常。也可以用浏览器打开 `http://localhost:8000/docs`,会看到一个可视化的接口测试页。

---

## 第 6 步：发第一个识别请求(文字识别)

文字识别(OCR)最省事,不用你准备任何模型(首次会自动下载内置中文模型,需联网,稍等)。

准备一张带文字的截图,比如 `screenshot.png`,放进当前目录,然后:

```bash
B64=$(base64 -w0 screenshot.png)
curl -s http://localhost:8000/v1/ocr \
  -H "Content-Type: application/json" \
  -d "{\"base64\": \"$B64\"}" | python3 -m json.tool
```

> macOS 的 base64 没有 `-w0`,改用:`B64=$(base64 -i screenshot.png)`

你会看到一大段 JSON,重点看 `method_results → ocr → detections`,里面每一项是识别到的一段文字:

- `text`:识别出的文字
- `confidence`:有多大把握(0~1)
- `center`:文字框中心点坐标 `[x, y]`——你的脚本就拿这个去点击

🎉 到这里你已经跑通了全流程!

---

## 第 7 步（进阶）：用 YOLO 检测 / 模板匹配

这两种需要你**先准备资产**:

### 用模板匹配找固定图标

1. 把要找的图标小图(如 `settings.png`)放进 `templates_store/`。
2. 编辑 `configs/templates.yaml`:
   ```yaml
   templates:
     settings_icon:
       path: templates_store/settings.png
       version: v1
       params:
         threshold: 0.85
   ```
3. 重启服务,请求:
   ```bash
   curl -s http://localhost:8000/v1/match \
     -H "Content-Type: application/json" \
     -d "{\"image\": {\"base64\": \"$B64\"}, \"methods\": [\"template\"], \"templates\": [\"settings_icon\"]}"
   ```

### 用 YOLO 检测目标

1. 把训练好的权重(`.pt`)放进 `models_store/`。(怎么训练见 `training/README.md`)
2. 编辑 `configs/models.yaml` 登记模型名、路径、类别表。
3. 请求带 `"model": "你的模型名"`(见 [使用文档](usage.md))。

---

## 常见报错与处理

| 现象 | 原因 / 处理 |
|---|---|
| `uv: command not found` | 第 2 步 PATH 没生效,重开终端或 `source $HOME/.local/bin/env` |
| 启动报 `ModuleNotFoundError: torch/paddle` | 没装 extras,跑 `uv sync --extra yolo --extra ocr` |
| `curl: command not found` | 装 curl:`sudo apt install curl`;或用浏览器的 `/docs` 页面测 |
| 请求返回 `detections: []` | 不是报错——只是没找到达阈值的目标,把 `conf_threshold` 调低些再试 |
| 返回 `{"error_code":"INVALID_IMAGE"}` | 图片路径错 / base64 不完整,确认图片存在且转码正确 |
| 返回 `{"error_code":"MODEL_NOT_FOUND"}` | `model` 名没在 `configs/models.yaml` 登记,或权重没放对 |
| 返回 `{"error_code":"PATH_NOT_ALLOWED"}` | 用 `path` 传图时,该路径不在白名单,设 `OYE_ALLOWED_PATH_ROOTS`(见 [使用文档 §8](usage.md#8-配置环境变量-oye_)) |
| 端口被占 | 换端口:`uv run ocr-yolo serve --port 8001` |

---

## 下一步

- 接口字段全解释 → [使用文档](usage.md)
- 部署到服务器、用 Docker、配鉴权 → [部署文档](deployment.md)
- 想理解它内部怎么运转 → [项目详细文档](overview.md)
