"""CLI:serve 启动服务;infer 本地单图推理。重依赖懒加载。"""

from __future__ import annotations

import argparse
import json
import sys


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ocr-yolo", description="OcrYoloEngine 视觉识别服务")
    sub = parser.add_subparsers(dest="command", required=True)

    serve = sub.add_parser("serve", help="启动 HTTP 服务")
    serve.add_argument("--host", default="0.0.0.0")
    serve.add_argument("--port", type=int, default=8000)

    infer = sub.add_parser("infer", help="本地单图推理")
    infer.add_argument("image", help="本地图片路径")
    infer.add_argument("--methods", default="ocr", help="逗号分隔:ocr,yolo,template")
    infer.add_argument("--model", default=None)
    infer.add_argument("--templates", default=None, help="逗号分隔模板名")
    infer.add_argument("--conf", type=float, default=None)
    return parser


def _find_free_port(host: str, start: int, max_tries: int = 10) -> int:
    """从 start 开始找一个没被占用的端口,最多尝试 max_tries 个。"""
    import socket

    for offset in range(max_tries):
        port = start + offset
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind((host if host != "0.0.0.0" else "127.0.0.1", port))
                return port
            except OSError:
                continue
    return start


def _cmd_serve(args: argparse.Namespace) -> int:
    import uvicorn  # 懒加载

    from ocr_yolo_engine.service.app import create_app

    port = _find_free_port(args.host, args.port)
    if port != args.port:
        print(f"端口 {args.port} 已被占用，自动切换到 {port}")
    browse_host = "localhost" if args.host == "0.0.0.0" else args.host
    print(f"浏览器打开 http://{browse_host}:{port}/docs 查看接口文档")
    uvicorn.run(create_app(), host=args.host, port=port)
    return 0


def _cmd_infer(args: argparse.Namespace) -> int:
    import os

    from ocr_yolo_engine.observability.logging import bind_request_id, new_request_id
    from ocr_yolo_engine.pipeline_runner import run_recognition
    from ocr_yolo_engine.schemas import ImageInput, RecognizeRequest
    from ocr_yolo_engine.service.deps import build_context
    from ocr_yolo_engine.settings import Settings

    bind_request_id(new_request_id())

    root = os.path.dirname(os.path.realpath(args.image)) or "."
    ctx = build_context(Settings(allowed_path_roots=[root]))
    methods = [m.strip() for m in args.methods.split(",") if m.strip()]
    templates = [t.strip() for t in args.templates.split(",")] if args.templates else None
    req = RecognizeRequest(
        image=ImageInput(path=os.path.realpath(args.image)),
        methods=methods,
        model=args.model,
        templates=templates,
        conf_threshold=args.conf,
    )
    resp = run_recognition(ctx, req)
    print(json.dumps(resp.model_dump(), ensure_ascii=False, indent=2))
    ctx.executor.shutdown()
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv if argv is not None else sys.argv[1:])
    if args.command == "serve":
        return _cmd_serve(args)
    if args.command == "infer":
        return _cmd_infer(args)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
