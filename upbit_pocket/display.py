"""터미널 출력 유틸리티."""

from __future__ import annotations

import sys
import unicodedata
from decimal import Decimal

from .models import format_amount, format_krw

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
CYAN = "\033[36m"


def colorize(text: str, color: str, enabled: bool = True) -> str:
    if not enabled or not sys.stdout.isatty():
        return text
    return f"{color}{text}{RESET}"


def display_width(text: str) -> int:
    width = 0
    for char in text:
        width += 2 if unicodedata.east_asian_width(char) in ("W", "F") else 1
    return width


def pad(text: str, width: int, align: str = "left") -> str:
    padding = " " * max(0, width - display_width(text))
    if align == "right":
        return padding + text
    if align == "center":
        left = len(padding) // 2
        return " " * left + text + " " * (len(padding) - left)
    return text + padding


def render_table(headers: list[str], rows: list[list[str]], aligns: list[str] | None = None) -> str:
    aligns = aligns or ["left"] * len(headers)
    widths = [display_width(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], display_width(cell))

    lines = [
        "  ".join(colorize(pad(header, widths[i], aligns[i]), BOLD) for i, header in enumerate(headers)),
        "  ".join(colorize("-" * widths[i], DIM) for i in range(len(headers))),
    ]
    for row in rows:
        lines.append("  ".join(pad(cell, widths[i], aligns[i]) for i, cell in enumerate(row)))
    return "\n".join(lines)


def render_amount(value: Decimal, currency: str) -> str:
    return f"{format_amount(value)} {currency}"


def render_krw(value: Decimal | None) -> str:
    if value is None:
        return "-"
    return f"{format_krw(value)} KRW"
