# 项目详细文档（架构 · 流程 · 核心技术）

> 面向想**整体理解本项目**的读者:它解决什么问题、怎么运转、用了哪些关键技术。
> 只想快速跑起来 → 看 [快速开始](quickstart.md);只想查接口 → 看 [使用文档](usage.md)。

---

## 1. 这是什么

`OcrYoloEngine` 是一个**面向自动化测试的视觉识别 HTTP 服务**。

一句话:**别的自动化脚本在跑用例时截图,把图片发给本服务,本服务识别出"目标在哪、文字是什么、有多大把握",再把结果返回。本服务只"看",不"点"**——不执行任何点击、滑动等动作,动作由调用方自己做。

典型使用场景:

- 手机 App 截图的**文字定位**(找到"登录"按钮在哪)
- Web 端**元素定位**
- 手机**游戏**里的复杂图像定位(设置按钮、角色、道具图标等)

---

## 2. 三种识别手段（互补)

| 手段 | 技术 | 适合 | 返回 |
|---|---|---|---|
| **OCR** | PaddleOCR | 识别**文字**及其位置 | 文字 + 框 + 置信度 |
| **YOLO** | ultralytics(v8/v11) | **目标检测/分类**,可按游戏训练专用模型 | 类别 + 框 + 置信度 |
| **模板匹配** | OpenCV(多尺度 + NMS) | 固定不变的**图标**(类似 airtest) | 模板名 + 框 + 相似度 |

三种方法**统一接口、统一结果结构**:调用方一次拿到全部字段(坐标、文字、置信度、归一化坐标),自己按需筛选。

---

## 3. 操作流程（使用方视角)

```
1. 部署本服务(本地 / Docker),在 configs/ 里登记好模型与模板
2. 你的自动化脚本截图 → 得到一张图片
3. 调用本服务接口(把图片以 base64 / 本地路径 / 上传 发来,指定用哪种识别、哪个模型)
4. 拿到 JSON 结果:每个目标的 bbox[x1,y1,x2,y2]、center[cx,cy]、文字、置信度
5. 你的脚本用这些坐标自己去点击 / 断言
```

详见 [使用文档](usage.md) 的完整请求/响应示例。

---

## 4. 请求处理流程（服务内部,一次 detect 为例)

```
HTTP POST /v1/detect (base64/path + model + conf + roi? )
  └─ 鉴权(API Key,可关闭)
     └─ image/loader:载图 + 解码;本地路径走白名单(防路径穿越)
        └─ preprocessing:校验大小/分辨率上限 → BGR转RGB统一通道 → ROI 裁剪
           └─ concurrency.executor:入队(满则 503) → 工作池线程 + 每模型锁串行化
              └─ models.registry:按名取模型(懒加载/LRU 缓存) → yolo.infer 推理
                 └─ preprocessing.finalize:坐标加 ROI 偏移回映射到全图 + 归一化
                    └─ 组装 Detection 列表 + 用到的模型版本 + 耗时
                       └─ 200 响应(JSON)
```

关键:**识别器只在"输入给它的那张图"上给坐标;加偏移、归一化统一由预处理层 `finalize_detections` 完成**,识别器内部不碰坐标系转换——这样三种识别器的坐标口径绝对一致。

---

## 5. 分层架构

```
            ┌─────────────────────────────────────────────┐
 HTTP 请求 →│ service (FastAPI, /v1, 鉴权, 路由, 错误处理) │
            └───────────────┬─────────────────────────────┘
                            ▼
            ┌─────────────────────────────────────────────┐
            │ concurrency (有界工作池 + 每模型锁 + 背压503) │
            └───────────────┬─────────────────────────────┘
                            ▼
 image/loader → preprocessing (通道统一 / ROI 裁剪 / 坐标回映射)
                            ▼
            ┌──────────── recognizers (统一抽象) ─────────┐
            │   ocr        yolo            template        │
            │ (PaddleOCR) (ultralytics)  (OpenCV)          │
            └───────┬───────────┬──────────────┬──────────┘
                    ▼           ▼              ▼
             models.registry          templates.store
             (按名加载/版本/LRU)       (模板库/版本)
```

各层职责(对应 `src/ocr_yolo_engine/` 下目录):

| 模块 | 职责 |
|---|---|
| `settings.py` | 集中配置(环境变量 `OYE_*` + 默认值) |
| `schemas.py` | 请求/响应/`Detection` 数据模型(pydantic) |
| `errors.py` | 统一错误码与 HTTP 映射 |
| `image/loader.py` | 图片来源:base64 / 本地路径(白名单) / 上传 |
| `preprocessing/pipeline.py` | 通道统一、上限校验、ROI 裁剪与坐标回映射 |
| `recognizers/` | `base`(抽象)+ `ocr`/`yolo`/`template` 三识别器 |
| `models/registry.py` | 模型按需加载 + 版本 + LRU 淘汰 + 卸载/重载 |
| `templates/store.py` | 模板库加载缓存 + 版本 |
| `concurrency/executor.py` | 有界线程池 + 每模型锁 + 背压(503)/ 超时(504) |
| `observability/logging.py` | 结构化 JSON 日志 + `request_id` 贯穿 |
| `service/` | `app`(装配)/`routes`(/v1)/`auth`(鉴权)/`deps`(依赖注入) |
| `cli.py` | 命令行:`serve` 起服务 / `infer` 本地单图推理 |
| `training/` | **隔离**的训练入口,服务运行时绝不 import |

---

## 6. 核心技术与设计要点

- **重依赖懒加载**:`torch`(YOLO)、`paddle`(OCR)只在对应识别器**首次推理时**才 import。`--help`、健康检查、只用模板匹配时都不会触发,启动快、互不干扰。
- **多模型按需切换**:`models.yaml` 登记多个模型,请求里用 `model` 字段指定;首次用到才加载,超过 `OYE_MODEL_CACHE_SIZE` 个按 **LRU 淘汰**,防显存/内存爆。
- **CPU/GPU 皆可**:`OYE_DEVICE=auto`(默认,有 GPU 用 GPU 否则 CPU)/`cpu`/`cuda`;提供 CPU、GPU 两套 Dockerfile。
- **并发与背压**:推理是 CPU/GPU 密集的同步操作,放进**有界线程池**跑(不阻塞事件循环);同一模型用**一把锁**串行(规避模型非线程安全);排队超过上限直接 **503 + Retry-After**,不堆积拖垮服务;单请求超时 **504**。
- **统一坐标口径**:返回**全图原始像素** `bbox/center` + **归一化** `bbox_norm/center_norm`(0~1)。不同分辨率设备用归一化坐标更稳。
- **统一错误契约**:成功但没识别到目标 = `200` + 空 `detections`(**不是错误**);只有真出错才 `4xx/5xx` + `error_code`。
- **安全**:本地路径输入必须落在 `OYE_ALLOWED_PATH_ROOTS` 白名单内(**防路径穿越/任意文件读取**);输入大小、分辨率上限(防内存打爆 / decompression bomb);可选 API Key 鉴权。
- **可观测**:结构化 JSON 日志贯穿 `request_id`;响应里带每方法耗时 `elapsed_ms` 与模型/模板版本,便于复现与排障。
- **可测试**:识别器抽象 + 依赖注入,服务层/并发层可注入 `FakeRecognizer`,**不加载真实模型**即可完整测试;81 个测试(单元 + HTTP 契约)全绿。
- **训练隔离**:`training/` 独立目录,有专门测试断言 `src/` 不 import 它;训练产出权重放 `models_store/`,在 `configs/models.yaml` 登记即可被服务加载。

---

## 7. 进一步阅读

- [快速开始](quickstart.md) · [小白操作文档](beginner-guide.md) · [使用文档](usage.md) · [部署文档](deployment.md)
- 设计依据:[设计 spec](../specs/2026-06-03-recognition-service-design.md)
- 架构取舍:[ADR](../adr/)(如 0002 为何模板匹配用归一化 SAD)
