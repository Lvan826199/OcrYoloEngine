from ocr_yolo_engine.config_loader import load_model_specs, load_template_specs


def test_load_model_specs(tmp_path):
    p = tmp_path / "models.yaml"
    p.write_text(
        "models:\n"
        "  game_a:\n"
        "    path: models_store/game_a.pt\n"
        "    version: v1\n"
        "    classes:\n"
        "      0: boss\n"
        "      1: coin\n",
        encoding="utf-8",
    )
    specs = load_model_specs(str(p))
    assert specs["game_a"].path == "models_store/game_a.pt"
    assert specs["game_a"].version == "v1"
    assert specs["game_a"].classes == {0: "boss", 1: "coin"}


def test_load_model_specs_missing_file_returns_empty(tmp_path):
    assert load_model_specs(str(tmp_path / "nope.yaml")) == {}


def test_load_model_specs_falls_back_to_example(tmp_path):
    """实际文件不存在但 .example 存在时,回退读取 .example。"""
    example = tmp_path / "models.yaml.example"
    example.write_text(
        "models:\n  demo:\n    path: demo.pt\n    version: v1\n",
        encoding="utf-8",
    )
    # 传入实际文件路径(不存在),应回退到同名 .example
    specs = load_model_specs(str(tmp_path / "models.yaml"))
    assert specs["demo"].path == "demo.pt"


def test_load_model_specs_prefers_real_file_over_example(tmp_path):
    """实际文件存在时优先用实际文件,忽略 .example。"""
    real = tmp_path / "models.yaml"
    real.write_text("models:\n  real:\n    path: real.pt\n    version: v2\n", encoding="utf-8")
    (tmp_path / "models.yaml.example").write_text(
        "models:\n  demo:\n    path: demo.pt\n    version: v1\n", encoding="utf-8"
    )
    specs = load_model_specs(str(real))
    assert "real" in specs
    assert "demo" not in specs


def test_load_template_specs_falls_back_to_example(tmp_path):
    """模板配置同样支持回退到 .example。"""
    example = tmp_path / "templates.yaml.example"
    example.write_text(
        "templates:\n  demo_block:\n    path: patch.png\n    version: v1\n",
        encoding="utf-8",
    )
    specs = load_template_specs(str(tmp_path / "templates.yaml"))
    assert specs["demo_block"].path == "patch.png"


def test_load_template_specs(tmp_path):
    p = tmp_path / "templates.yaml"
    p.write_text(
        "templates:\n"
        "  settings_icon:\n"
        "    path: templates_store/settings.png\n"
        "    version: v1\n"
        "    params:\n"
        "      threshold: 0.85\n",
        encoding="utf-8",
    )
    specs = load_template_specs(str(p))
    assert specs["settings_icon"].path == "templates_store/settings.png"
    assert specs["settings_icon"].params == {"threshold": 0.85}
