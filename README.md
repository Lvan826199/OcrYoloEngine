<a id="readme-top"></a>

<!--
门面型 README，结构参考 othneildrew/Best-README-Template
https://github.com/othneildrew/Best-README-Template
-->

<div align="center">

<h1 align="center">OcrYoloEngine</h1>

<p align="center">
  一个基于 YOLO 目标检测 + OCR 文字识别的引擎。
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

`OcrYoloEngine` 旨在把 **YOLO 目标检测**与 **OCR 文字识别**结合到一个统一的引擎中：先用 YOLO 定位图像中的文字/目标区域，再对这些区域做 OCR 识别，输出结构化结果。

> ⚠️ 项目当前处于早期阶段，核心代码仍在搭建中。本 README 的结构已就位，功能描述将随开发推进逐步充实。

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

- 📌 [开发主线索引与进度](docs/DEVELOPMENT.md) —— **跨会话接手的第一入口**：文档地图、任务进度表、关键约定速查。
- 📐 [设计文档（spec）](docs/superpowers/specs/2026-06-03-recognition-service-design.md) —— 需求、范围与架构的权威来源。
- 🗂️ [实现计划](docs/superpowers/plans/2026-06-03-recognition-service.md) —— 分阶段、逐任务的 TDD 实现步骤。
- 🧭 [架构决策记录（ADR）](docs/adr/) —— 重要技术取舍的逐条记录。

<p align="right">(<a href="#readme-top">回到顶部</a>)</p>

---

## 路线图

- [ ] 搭建项目骨架与依赖管理
- [ ] 接入 YOLO 检测模块
- [ ] 接入 OCR 识别模块
- [ ] 串联检测 → 识别流水线
- [ ] 提供 CLI / API 入口
- [ ] 补充测试与文档

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
