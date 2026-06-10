# golden 测试样例

放置固定样例图与期望结果(坐标/置信度带容差)。每新增一个识别场景:
1. 在此目录放 `<场景>.png` 与 `<场景>.expected.json`。
2. 在 `tests/unit/` 或 `tests/smoke/` 写断言:坐标允许 ±N 像素、置信度 ±0.05。

golden 用于防止模型/预处理改动悄悄改变行为。

## 真实游戏截图样例（来源与许可）

`game_menu.png`、`game_race.jpg` 为开源游戏 **SuperTuxKart** 截图,取自 Wikimedia Commons,
许可证 **CC BY-SA 4.0**(入库前经尺寸压缩/转码):

- `game_menu.png` ← [Menu SuperTuxKart in English.png](https://commons.wikimedia.org/wiki/File:Menu_SuperTuxKart_in_English.png),作者 TrainAndBus64
- `game_race.jpg` ← [SuperTuxKart in-race (2018).png](https://commons.wikimedia.org/wiki/File:SuperTuxKart_in-race_(2018).png),作者 QwertyChouskie

用途:`tests/unit/test_game_golden.py`(模板匹配回归,从菜单图裁真实按钮再找回)、
`tests/smoke/test_real_recognition.py`(真实 OCR 读 HUD 文字、真实 YOLO 检目标)。
