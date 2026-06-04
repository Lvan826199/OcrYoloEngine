import pytest


@pytest.mark.smoke
def test_real_model_smoke_placeholder():
    """占位:接入真实权重后,在此加载模型跑端到端。

    运行方式:uv run pytest -m smoke
    默认 CI 用 -m 'not smoke' 跳过(见 pyproject.toml)。
    """
    pytest.skip("尚未配置真实权重;放好 models_store 后实现")
