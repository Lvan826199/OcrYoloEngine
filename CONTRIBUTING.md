# 贡献指南

感谢你愿意为 OcrYoloEngine 做出贡献！本文档说明参与本项目的流程与约定。

## 行为准则

参与本项目即表示你同意遵守我们的[行为准则](CODE_OF_CONDUCT.md)。

## 如何贡献

### 报告问题

通过 [Issues](https://gitee.com/xiaozai-van-liu/OcrYoloEngine/issues) 提交 bug 或需求。提交 bug 时请尽量包含：

- 问题的清晰描述与复现步骤
- 期望行为与实际行为
- 运行环境（操作系统、Python 版本、依赖版本）
- 相关日志或截图

### 提交代码

1. Fork 本仓库并基于 `master` 创建特性分支：
   ```sh
   git checkout -b feature/你的特性
   ```
2. 进行修改，保持提交粒度清晰。
3. 提交信息使用简体中文，建议遵循 [Conventional Commits](https://www.conventionalcommits.org/zh-hans/) 风格，例如：
   ```
   feat: 接入 YOLO 检测模块
   fix: 修复 OCR 识别区域越界问题
   docs: 完善安装说明
   ```
4. 推送分支并发起 Pull Request，在描述中说明改动内容与动机，并关联相关 Issue。

### 分支约定

- `master`：稳定主分支。
- `feature/*`：新功能开发。
- `fix/*`：缺陷修复。

## 开发约定

- 影响架构的重要决策，请在 [设计与决策](docs/设计与决策.md) 的「架构决策记录」一节新增一条 ADR。
- 面向用户的变更，请在 [CHANGELOG.md](CHANGELOG.md) 的「未发布」小节登记。
- 模型权重文件（`*.pt`、`*.pth`、`*.onnx` 等）不要提交入库，已在 `.gitignore` 中排除。

> 注：测试、lint 等具体命令待项目工具链就绪后在此补充。
