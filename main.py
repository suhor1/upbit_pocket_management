#!/usr/bin/env python
"""업비트 포켓 관리 도구 실행 진입점."""

from __future__ import annotations

import sys

from upbit_pocket.cli import main

if __name__ == "__main__":
    sys.exit(main())
