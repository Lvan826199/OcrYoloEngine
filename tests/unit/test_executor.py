import threading
import time

import pytest

from ocr_yolo_engine.concurrency.executor import InferenceExecutor
from ocr_yolo_engine.errors import EngineError, ErrorCode


def test_submit_returns_result():
    ex = InferenceExecutor(max_workers=2, max_queue=8, timeout_s=5)
    assert ex.submit("m", lambda: 41 + 1) == 42
    ex.shutdown()


def test_same_model_serialized():
    ex = InferenceExecutor(max_workers=4, max_queue=16, timeout_s=5)
    active = 0
    max_active = 0
    lock = threading.Lock()

    def work():
        nonlocal active, max_active
        with lock:
            active += 1
            max_active = max(max_active, active)
        time.sleep(0.05)
        with lock:
            active -= 1
        return True

    threads = [threading.Thread(target=lambda: ex.submit("same", work)) for _ in range(4)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert max_active == 1
    ex.shutdown()


def test_overload_raises_503():
    ex = InferenceExecutor(max_workers=1, max_queue=1, timeout_s=5)
    started = threading.Event()
    release = threading.Event()

    def block():
        started.set()
        release.wait()
        return 1

    t = threading.Thread(target=lambda: ex.submit("m", block))
    t.start()
    started.wait()
    errors = []

    def try_submit():
        try:
            ex.submit("m", lambda: 1)
        except EngineError as e:
            errors.append(e.code)

    extra = [threading.Thread(target=try_submit) for _ in range(3)]
    for th in extra:
        th.start()
    for th in extra:
        th.join(timeout=2)
    release.set()
    t.join()
    assert ErrorCode.OVERLOADED in errors
    ex.shutdown()


def test_timeout_raises_504():
    ex = InferenceExecutor(max_workers=1, max_queue=4, timeout_s=0)

    def slow():
        time.sleep(0.2)
        return 1

    with pytest.raises(EngineError) as ei:
        ex.submit("m", slow)
    assert ei.value.code is ErrorCode.TIMEOUT
    ex.shutdown()
