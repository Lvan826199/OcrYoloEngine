"""指标模块单元测试:用真实计数,断言 Prometheus 文本输出。"""

from ocr_yolo_engine.observability import metrics


def test_record_and_render():
    metrics.reset()
    metrics.record("template", 12.0, ok=True)
    metrics.record("template", 8.0, ok=True)
    metrics.record("yolo", 50.0, ok=False)
    out = metrics.render()

    assert "# TYPE oye_requests_total counter" in out
    assert 'oye_requests_total{method="template",status="ok"} 2' in out
    assert 'oye_requests_total{method="yolo",status="error"} 1' in out
    assert 'oye_inference_seconds_count{method="template"} 2' in out
    # 两次 template 共 20ms = 0.02s
    assert 'oye_inference_seconds_sum{method="template"} 0.020000' in out


def test_reset_clears():
    metrics.record("ocr", 5.0)
    metrics.reset()
    out = metrics.render()
    assert "oye_requests_total" in out  # 头部仍在
    assert 'method="ocr"' not in out  # 数据已清空
