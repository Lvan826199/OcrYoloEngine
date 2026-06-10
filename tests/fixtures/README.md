# 固定回归样例（golden）

放置固定样例图与期望结果。golden 用于防止模型/预处理改动悄悄改变行为。

## 文件组织

每新增一个识别场景,在本目录放两个文件:

- `<场景>.png` / `<场景>.jpg`:样例图(确定性内容;外来图片需在下方登记来源与许可)。
- `<场景>.expected.json`:期望结果,**必须遵循下面的字段规范**。

断言写在 `tests/unit/`(无重依赖,如模板匹配)或 `tests/smoke/`(真实 OCR/YOLO 模型)。

## expected.json 字段规范（强制）

```jsonc
{
  "scene": "game_race.jpg",          // 必填:本目录下的样例图文件名
  "scene_size": [1366, 768],         // 必填:[宽, 高],测试先校验图未被误改
  "description": "场景与期望的说明",  // 必填:一句话讲清这是什么场景、期望从哪来
  "expectations": {                  // 必填:按识别方法分组,每组为数组
    "template": [
      {
        "name": "game_button",            // 模板名
        "template_file": "patch.png",     // 二选一:独立模板图文件名
        "crop": { "x": 0, "y": 0, "w": 1, "h": 1 },  // 二选一:从 scene 上裁剪
        "bbox": [80, 60, 100, 80],        // 可选:期望框 [x1,y1,x2,y2]
        "center": [90.0, 70.0],           // 必填:期望中心 [x, y]
        "tolerance_px": 3,                // 必填:坐标容差(像素)
        "min_confidence": 0.99            // 必填:置信度下限
      }
    ],
    "ocr": [
      {
        "text_contains": "00:01.53",      // 必填:识别文字应包含的子串
        "center": [1254, 38],             // 必填 + 必填容差,同上
        "tolerance_px": 15
      }
    ],
    "yolo": [
      {
        "model": "yolov8n",               // 必填:模型名
        "label": "person",                // 必填:期望类别
        "center": [1106, 281],
        "tolerance_px": 40,
        "min_confidence": 0.5
      }
    ]
  }
}
```

规则:

1. **期望值必须出自真实运行**,不得拍脑袋——用 `scripts/gen_expected.py` 对样例图跑真实识别生成草稿,人工审定容差后入库。
2. **坐标必带容差**(`tolerance_px`):模板/精确场景 ±3,OCR ±15,YOLO ±40 起步,按场景放宽。
3. 容差与 `min_confidence` 是人工审定的工程判断,改动它们要在 `description` 或提交信息里说明理由。
4. 只写测试实际断言的字段;`expectations` 里没有的方法组,测试不得凭空假设。

## 外来样例图登记（来源与许可）

`game_menu.png`、`game_race.jpg` 为开源游戏 **SuperTuxKart** 截图,取自 Wikimedia Commons,
许可证 **CC BY-SA 4.0**(入库前经尺寸压缩/转码):

- `game_menu.png` ← [Menu SuperTuxKart in English.png](https://commons.wikimedia.org/wiki/File:Menu_SuperTuxKart_in_English.png),作者 TrainAndBus64
- `game_race.jpg` ← [SuperTuxKart in-race (2018).png](https://commons.wikimedia.org/wiki/File:SuperTuxKart_in-race_(2018).png),作者 QwertyChouskie

用途:`tests/unit/test_game_golden.py`(模板匹配回归,从菜单图裁真实按钮再找回)、
`tests/smoke/test_real_recognition.py`(真实 OCR 读 HUD 文字、真实 YOLO 检目标)。
