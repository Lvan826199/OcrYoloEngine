import socket

import pytest

from ocr_yolo_engine.cli import _find_free_port, build_parser


def test_parser_serve_defaults():
    args = build_parser().parse_args(["serve"])
    assert args.command == "serve"
    assert args.host == "0.0.0.0"
    assert args.port == 8000


def test_parser_infer_args():
    args = build_parser().parse_args(
        ["infer", "img.png", "--methods", "ocr,yolo", "--model", "game", "--conf", "0.4"]
    )
    assert args.command == "infer"
    assert args.image == "img.png"
    assert args.methods == "ocr,yolo"
    assert args.model == "game"
    assert args.conf == 0.4


def test_parser_requires_command():
    with pytest.raises(SystemExit):
        build_parser().parse_args([])


def test_find_free_port_returns_none_when_exhausted():
    """候选端口全被占用时返回 None(而非静默返回必然失败的原端口)。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        occupied = s.getsockname()[1]
        assert _find_free_port("127.0.0.1", occupied, max_tries=1) is None


def test_find_free_port_skips_occupied_port():
    """起始端口被占时自动顺延到下一个空闲端口。"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("127.0.0.1", 0))
        occupied = s.getsockname()[1]
        got = _find_free_port("127.0.0.1", occupied, max_tries=5)
        assert got is not None
        assert got != occupied
