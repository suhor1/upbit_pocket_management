#!/usr/bin/env python
"""업비트 포켓 관리 웹 UI 실행 진입점.

    python web.py                # http://127.0.0.1:5000
    python web.py --port 8080
"""

from __future__ import annotations

import argparse
import sys
import webbrowser
from threading import Timer

from upbit_pocket.config import Settings
from upbit_pocket.errors import UpbitPocketError
from upbit_pocket.web import create_app


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="업비트 포켓 관리 웹 UI")
    parser.add_argument("--host", default="127.0.0.1", help="바인딩 주소 (기본: 127.0.0.1, 로컬 전용)")
    parser.add_argument("--port", type=int, default=5000, help="포트 (기본: 5000)")
    parser.add_argument("--no-browser", action="store_true", help="브라우저 자동 실행 안 함")
    parser.add_argument("--debug", action="store_true", help="디버그 모드 (비권장)")
    parser.add_argument("--env-file", default=".env", help="API Key 파일 경로 (기본: .env)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    try:
        settings = Settings.load(args.env_file)
    except UpbitPocketError as exc:
        print(f"설정 오류: {exc}", file=sys.stderr)
        return 1

    app = create_app(settings)

    if not args.no_browser and not args.debug:
        url = f"http://127.0.0.1:{args.port}"
        Timer(1.0, lambda: webbrowser.open(url)).start()
        print(f"\n  업비트 포켓 관리  ->  {url}\n  종료하려면 Ctrl+C 를 누르세요.\n")

    try:
        app.run(host=args.host, port=args.port, debug=args.debug)
    except KeyboardInterrupt:
        print("\n서버를 종료했습니다.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
