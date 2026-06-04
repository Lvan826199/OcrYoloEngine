# 快速开始（5 分钟）

> 目标:把服务跑起来,发一个请求拿到识别结果。第一次接触、对命令行不熟 → 看更详细的 [小白操作文档](beginner-guide.md)。

## 前置

- Python ≥ 3.11
- [uv](https://docs.astral.sh/uv/)(Python 包管理器)。没装就跑:
  ```bash
  curl -LsSf https://astral.sh/uv/install.sh | sh
  ```

## 1. 获取代码 + 装依赖

```bash
git clone https://gitee.com/xiaozai-van-liu/OcrYoloEngine.git
cd OcrYoloEngine

# 只跑模板匹配 + HTTP 服务,核心依赖即可:
uv sync

# 要用 YOLO / OCR,装对应 extras(会拉 torch / paddle,较大):
uv sync --extra yolo --extra ocr
```

## 2. 启动服务

```bash
uv run ocr-yolo serve
```

看到 uvicorn 在 `http://0.0.0.0:8000` 监听即成功。浏览器打开 `http://localhost:8000/docs` 可看到交互式接口文档。

健康检查:

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

## 3. 发第一个识别请求(OCR,无需模型权重)

OCR 不需要你自己准备权重(PaddleOCR 首次会自动下载内置模型)。把任意带文字的截图转 base64 发过去:

```bash
B64=$(base64 -w0 screenshot.png)
curl -s http://localhost:8000/v1/ocr \
  -H "Content-Type: application/json" \
  -d "{\"base64\": \"$B64\"}" | python3 -m json.tool
```

返回里 `method_results.ocr.detections` 就是识别到的每段文字 + 坐标:

```jsonc
{
  "image_size": [1080, 1920],
  "method_results": {
    "ocr": {
      "detections": [
        { "source": "ocr", "text": "登录", "confidence": 0.97,
          "bbox": [120, 340, 220, 390], "center": [170, 365], ... }
      ]
    }
  }
}
```

`center` 就是你的自动化脚本要点击的坐标。

## 4. （可选）用 YOLO / 模板匹配

需要先准备资产:

- **YOLO**:把训练好的权重放 `models_store/`,在 `configs/models.yaml` 登记(见 [使用文档 §8.1](usage.md#81-模型登记-configsmodelsyaml)),请求时带 `"model": "你的模型名"`。
- **模板匹配**:把模板图放 `templates_store/`,在 `configs/templates.yaml` 登记,请求时带 `"templates": ["模板名"]`。

```bash
# YOLO 检测
curl -s http://localhost:8000/v1/detect \
  -H "Content-Type: application/json" \
  -d '{"image": {"base64": "..."}, "methods": ["yolo"], "model": "game_a"}'
```

## 下一步

- 完整接口、字段、错误码 → [使用文档](usage.md)
- 部署到服务器 / Docker → [部署文档](deployment.md)
- 想搞懂它怎么运转 → [项目详细文档](overview.md)
