<a id="readme-top"></a>

<!--
门面型 README，结构参考 othneildrew/Best-README-Template
https://github.com/othneildrew/Best-README-Template
-->

<div align="center">

<h1 align="center">OcrYoloEngine</h1>

<p align="center">
  面向自动化测试的视觉识别 HTTP 服务。截图发过来，返回文字和目标的坐标，支持 OCR 文字识别、YOLO 目标检测、模板匹配三种方式，统一接口统一格式，开箱即用。
  <br />
  <a href="#关于项目"><strong>探索文档 »</strong></a>
  <br />
  <br />
  <a href="https://gitee.com/xiaozai-van-liu/OcrYoloEngine/issues">报告问题</a>
  ·
  <a href="https://gitee.com/xiaozai-van-liu/OcrYoloEngine/issues">提出需求</a>
</p>

<!-- 徽章（占位，待 CI / License 等就绪后替换为真实徽章） -->

![语言](https://img.shields.io/badge/language-Python-blue)
![版本](https://img.shields.io/badge/version-0.2.1-blue)
![状态](https://img.shields.io/badge/status-Ready-brightgreen)
![许可证](https://img.shields.io/badge/license-MIT-green)

</div>

<details>
  <summary>目录</summary>
  <ol>
    <li><a href="#关于项目">关于项目</a>
      <ul>
        <li><a href="#技术栈">技术栈</a></li>
      </ul>
    </li>
    <li><a href="#快速开始">快速开始</a>
      <ul>
        <li><a href="#环境要求">环境要求</a></li>
        <li><a href="#安装与启动">安装与启动</a></li>
      </ul>
    </li>
    <li><a href="#使用方法">使用方法</a></li>
    <li><a href="#部署">部署</a></li>
    <li><a href="#开发文档">开发文档</a></li>
    <li><a href="#路线图">路线图</a></li>
    <li><a href="#贡献">贡献</a></li>
    <li><a href="#许可证">许可证</a></li>
    <li><a href="#联系方式">联系方式</a></li>
  </ol>
</details>

---

## 关于项目

`OcrYoloEngine` 是帮**自动化测试脚本"看懂"截图**的服务。你的脚本截了图发过来,服务看完告诉你"东西在哪、文字是什么、有多大把握",你的脚本再根据坐标去点击。**只负责看,不负责点**。

三种"看图"方式,互相配合:

- **文字识别（OCR）**:找出图里的文字和位置。
- **目标检测（YOLO）**:找特定物体（如游戏里的角色、道具），需要提前训练模型。
- **模板匹配**:按图索骥找固定图标（类似"找不同"）。

三种方式用**同一套接口、返回同一种格式**的结果——坐标、文字、把握程度,拿来就能用。

> ℹ️ 当前版本 **v0.2.1**:网页接口 + 三种识别 + 结果缓存 + 多方式合并 + 调试标注图 + 监控指标,157 个测试全部通过。模板匹配开箱即用(自带示例),YOLO 自带通用模型 `yolov8n`;要用自己的模型/模板时从 `configs/*.yaml.example` 复制一份再改。详见 [开发文档](#开发文档)。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

### 技术栈

* [![Python][Python-badge]][Python-url]
* [![PyTorch][PyTorch-badge]][PyTorch-url]
* [![ONNX][ONNX-badge]][ONNX-url]

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 快速开始

> 完整版见 [快速开始](docs/快速开始.md)(含「从零开始(小白手把手)」一节,对命令行不熟也能跟着跑通)。

### 环境要求

* Python ≥ 3.11
* [uv](https://docs.astral.sh/uv/) 包管理器(`curl -LsSf https://astral.sh/uv/install.sh | sh`)
* 模板匹配开箱即用(自带示例素材);YOLO 自带通用模型 `yolov8n`;OCR 首次使用自动下载内置模型

### 安装与启动

```sh
git clone https://gitee.com/xiaozai-van-liu/OcrYoloEngine.git
cd OcrYoloEngine

uv sync                          # 基础:HTTP 服务 + 模板匹配
uv sync --extra yolo --extra ocr # 需要 YOLO / OCR 时(会拉 torch / paddle 大包)

uv run ocr-yolo serve            # 启动服务,默认 8000 端口(被占自动切下一个)
```

启动后终端会打印浏览器地址，直接打开即可看到接口文档。健康检查:`curl http://localhost:8000/health` → `{"status":"ok"}`。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 使用方法

把截图发给服务,拿回坐标和文字。仓库**自带示例素材**,安装完就能试（模板匹配,不需要额外装大包）:

```python
import base64, json, urllib.request

with open("tests/fixtures/golden_scene.png", "rb") as f:
    b64 = base64.b64encode(f.read()).decode()

req = urllib.request.Request(
    "http://localhost:8000/v1/match",
    data=json.dumps({
        "image": {"base64": b64},
        "templates": ["demo_block"],
    }).encode(),
    headers={"Content-Type": "application/json"},
)
data = json.loads(urllib.request.urlopen(req).read())
det = data["method_results"]["template"]["detections"][0]
print(f"坐标: {det['center']}, 把握: {det['confidence']:.2f}")
# 输出: 坐标: [90.0, 70.0], 把握: 0.99
```

返回结果里每个识别到的目标都有 `confidence`（把握程度）、`center`（中心点坐标）——**你的脚本直接点 `center` 坐标就行**。

主要接口：`/v1/ocr`（文字识别）、`/v1/detect`（目标检测）、`/v1/match`（模板匹配）、`/v1/recognize`（多种方式一起跑）、`/v1/recognize/upload`（文件上传）。命令行调试：`uv run ocr-yolo infer screenshot.png --methods ocr`。

> 全部端点、字段、错误码、配置项见 **[使用文档](docs/使用文档.md)**。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 部署

- 本地直接跑：`uv run ocr-yolo serve --host 0.0.0.0 --port 8000`（可配成系统服务后台常驻）。
- Docker：`docker build -f docker/Dockerfile.cpu -t ocr-yolo:cpu .`（有显卡用 `Dockerfile.gpu`），模型/模板/配置用文件夹挂载。
- 正式环境建议开启密钥验证（`OYE_API_KEYS`）、限制允许读取的目录（`OYE_ALLOWED_PATH_ROOTS`）。

> 完整部署、调优与安全见 **[部署文档](docs/部署文档.md)**。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 开发文档

项目的细节由 `docs/` 下 7 个文档维护：

- [项目说明](docs/项目说明.md) —— 这个服务是干什么的、怎么运转的
- [快速开始](docs/快速开始.md) —— 5 分钟跑起来 + 完全零基础的手把手教程
- [使用文档](docs/使用文档.md) —— 所有接口怎么调、命令行、配置、错误码
- [接口集成指南](docs/接口集成指南.md) —— **平台对接用**：Python 客户端类 + 每个接口的完整代码示例
- [部署文档](docs/部署文档.md) —— 怎么部署到服务器 / Docker / 性能调优 / 安全
- [设计与决策](docs/设计与决策.md) —— 技术方案和重要选择的记录
- [开发说明](docs/开发说明.md) —— 开发进度、约定、任务清单（开发者接手看这个）
- [bug修复日志](docs/bug修复日志.md) —— 长期累积的修复记录（现象/根因/修法/验证）

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

### 已完成（v0.2.1）

- [x] 搭建项目骨架与依赖管理（uv）
- [x] 接入 YOLO 检测模块（含模型注册表 + 按需加载 + 热卸载/重载）
- [x] 接入 OCR 文字识别模块（PaddleOCR）
- [x] 接入模板匹配模块（自动缩放 + 去重）
- [x] 统一识别流程（预处理 / 排队限流 / 坐标换算）
- [x] 提供命令行与网页接口入口（含端口自动轮询、根路径跳转 `/docs`）
- [x] 真实模型端到端冒烟测试与标准样例回归（157 个测试全绿，含真实游戏截图回归）
- [x] `/recognize` 多方法合并（优先级/去重/汇总）、区域裁剪、结果缓存
- [x] 调试标注图输出与 Prometheus 运行指标监控端点
- [x] CPU/GPU Docker 镜像（uv 构建）与 CI 质量门禁
- [x] 资产配置 `.example` 模板模式（开箱即用 + 加载自动回退）
- [x] 全量文档小白友好化 + 平台对接集成指南 + `/docs` 中文接口说明
- [x] 全量代码校验修复批次：错误响应 request_id、上传接口校验契约、防解压炸弹、模板匹配防爆炸、背压语义、锁粒度与缓存键优化（v0.2.1）
- [x] 自定义 YOLO 模型训练端到端教程（`training/README.md`，含零标注 demo 数据集生成器，CPU 实测全流程跑通）

### 规划中

- [ ] OCR 多语言支持（当前以中文为主）
- [ ] 可选 ONNX Runtime 推理后端（更轻量的部署）
- [ ] 客户端 SDK 打包（可 `pip install` 的对接库）

详见 [开放的 Issues](https://gitee.com/xiaozai-van-liu/OcrYoloEngine/issues)。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 贡献

欢迎贡献！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解流程，并遵守 [行为准则](CODE_OF_CONDUCT.md)。变更记录见 [CHANGELOG.md](CHANGELOG.md)，重要架构决策记录见 [设计与决策](docs/设计与决策.md)。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 许可证

基于 MIT 许可证分发，详见 [LICENSE](LICENSE)。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 联系方式

vincent - Lvan826199@163.com

项目地址: [https://gitee.com/xiaozai-van-liu/OcrYoloEngine](https://gitee.com/xiaozai-van-liu/OcrYoloEngine)

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

<!-- 链接与徽章定义 -->
[Python-badge]: https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white
[Python-url]: https://www.python.org/
[PyTorch-badge]: https://img.shields.io/badge/PyTorch-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white
[PyTorch-url]: https://pytorch.org/
[ONNX-badge]: https://img.shields.io/badge/ONNX-005CED?style=for-the-badge&logo=onnx&logoColor=white
[ONNX-url]: https://onnx.ai/
