<a id="readme-top"></a>

<!--
门面型 README，结构参考 othneildrew/Best-README-Template
https://github.com/othneildrew/Best-README-Template
-->

<div align="center">

<h1 align="center">OcrYoloEngine</h1>

<p align="center">
  面向自动化测试的视觉识别服务:OCR + YOLO + 模板匹配,只识别返回坐标,不执行动作。
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
![状态](https://img.shields.io/badge/status-WIP-orange)
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
        <li><a href="#安装">安装</a></li>
      </ul>
    </li>
    <li><a href="#使用方法">使用方法</a></li>
    <li><a href="#开发文档">开发文档</a></li>
    <li><a href="#路线图">路线图</a></li>
    <li><a href="#贡献">贡献</a></li>
    <li><a href="#许可证">许可证</a></li>
    <li><a href="#联系方式">联系方式</a></li>
  </ol>
</details>

---

## 关于项目

`OcrYoloEngine` 是面向**自动化测试**的视觉识别 HTTP 服务。其他自动化脚本在执行时截图,把图片发给本服务,本服务用三种互补手段识别并返回结果(坐标、文字、置信度),**只识别、不执行点击等动作**:

- **OCR**(PaddleOCR):文字识别与定位。
- **YOLO**(ultralytics):目标检测/分类,返回坐标 + 置信度,支持按游戏训练专用模型。
- **模板匹配**(OpenCV):多尺度模板/图标匹配。

三种方法统一接口、统一结果结构,调用方拿到全字段后自行筛选。典型场景:手机 App 文字定位、Web 元素定位、手机游戏复杂图像定位。

> ℹ️ 首版骨架已实现:FastAPI `/v1` 服务 + OCR/YOLO/模板匹配三识别器,统一返回坐标/文字/置信度。模型权重需另行获取并在 `configs/models.yaml` 登记。详见 [开发文档](#开发文档)。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

### 技术栈

* [![Python][Python-badge]][Python-url]
* [![PyTorch][PyTorch-badge]][PyTorch-url]
* [![ONNX][ONNX-badge]][ONNX-url]

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 快速开始

按以下步骤在本地搭建项目。

### 环境要求

* Python 3.x
* （待补充）依赖清单与模型权重获取方式

### 安装

> 以下命令为占位示例，待项目依赖与入口脚本就绪后更新。

1. 克隆仓库
   ```sh
   git clone https://gitee.com/xiaozai-van-liu/OcrYoloEngine.git
   cd OcrYoloEngine
   ```
2. 创建并激活虚拟环境
   ```sh
   python -m venv .venv
   source .venv/bin/activate
   ```
3. 安装依赖
   ```sh
   pip install -r requirements.txt
   ```

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 使用方法

_待补充：提供推理 / 训练的最小示例。_

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 开发文档

项目的设计与实现细节由以下文档持续维护，参与开发前请先阅读：

- 🗃️ [文档中心（分类索引）](docs/README.md) —— 所有开发文档的统一入口。
- 📌 [开发主线索引与进度](docs/DEVELOPMENT.md) —— **跨会话接手的第一入口**：文档地图、任务进度表、关键约定速查。
- 📐 [设计文档（spec）](docs/specs/2026-06-03-recognition-service-design.md) —— 需求、范围与架构的权威来源。
- 🗂️ [实现计划](docs/plans/2026-06-03-recognition-service.md) —— 分阶段、逐任务的 TDD 实现步骤。
- 🧭 [架构决策记录（ADR）](docs/adr/) —— 重要技术取舍的逐条记录。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 路线图

- [x] 搭建项目骨架与依赖管理
- [x] 接入 YOLO 检测模块（含模型注册表 + 懒加载）
- [x] 接入 OCR 识别模块（PaddleOCR）
- [x] 接入模板匹配模块（多尺度 + NMS）
- [x] 统一识别管线（预处理 / 并发背压 / 坐标回映射）
- [x] 提供 CLI 与 HTTP API（FastAPI `/v1`）入口
- [x] 补充测试（单元 + 契约）与文档
- [ ] 接入真实权重的端到端冒烟测试与 golden 用例
- [ ] `/recognize` 多方法智能合并、ROI 完整落地、结果缓存
- [ ] 标注图（debug）输出与 Prometheus 指标端点

详见 [开放的 Issues](https://gitee.com/xiaozai-van-liu/OcrYoloEngine/issues)。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 贡献

欢迎贡献！请先阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解流程，并遵守 [行为准则](CODE_OF_CONDUCT.md)。变更记录见 [CHANGELOG.md](CHANGELOG.md)，重要架构决策记录见 [docs/adr](docs/adr/)。

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
