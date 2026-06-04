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
