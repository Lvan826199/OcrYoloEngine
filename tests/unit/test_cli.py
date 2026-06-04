import pytest

from ocr_yolo_engine.cli import build_parser


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
