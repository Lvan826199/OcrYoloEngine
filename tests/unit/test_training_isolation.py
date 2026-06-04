import pathlib


def test_src_never_imports_training():
    """服务代码 src/ 任何文件都不得 import training。"""
    src = pathlib.Path(__file__).resolve().parents[2] / "src"
    offenders = []
    for py in src.rglob("*.py"):
        text = py.read_text(encoding="utf-8")
        if "import training" in text or "from training" in text:
            offenders.append(str(py))
    assert offenders == [], f"src 不应 import training: {offenders}"
