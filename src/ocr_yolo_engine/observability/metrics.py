"""轻量进程内指标:按识别方法统计请求数与推理耗时,以 Prometheus 文本格式暴露。

故意不引入 prometheus_client 依赖,保持零额外依赖;够用即可,后续如需多维标签再替换。
"""

from __future__ import annotations

import threading
from collections import defaultdict

_lock = threading.Lock()
_requests: dict[tuple[str, str], int] = defaultdict(int)  # (method, status) -> 次数
_seconds_sum: dict[str, float] = defaultdict(float)  # method -> 累计耗时(秒)
_seconds_count: dict[str, int] = defaultdict(int)  # method -> 次数


def record(method: str, elapsed_ms: float, ok: bool = True) -> None:
    """记录一次识别:方法、耗时(毫秒)、是否成功。"""
    status = "ok" if ok else "error"
    with _lock:
        _requests[(method, status)] += 1
        _seconds_sum[method] += elapsed_ms / 1000.0
        _seconds_count[method] += 1


def reset() -> None:
    """清空所有计数(主要给测试用)。"""
    with _lock:
        _requests.clear()
        _seconds_sum.clear()
        _seconds_count.clear()


def render() -> str:
    """渲染为 Prometheus 文本暴露格式。"""
    lines: list[str] = []
    with _lock:
        lines.append("# HELP oye_requests_total 各识别方法处理的请求数")
        lines.append("# TYPE oye_requests_total counter")
        for (method, status), count in sorted(_requests.items()):
            lines.append(f'oye_requests_total{{method="{method}",status="{status}"}} {count}')
        lines.append("# HELP oye_inference_seconds 各识别方法推理累计耗时(秒)")
        lines.append("# TYPE oye_inference_seconds summary")
        for method in sorted(_seconds_count):
            lines.append(
                f'oye_inference_seconds_sum{{method="{method}"}} {_seconds_sum[method]:.6f}'
            )
            lines.append(
                f'oye_inference_seconds_count{{method="{method}"}} {_seconds_count[method]}'
            )
    return "\n".join(lines) + "\n"
