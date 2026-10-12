"""요청 폼 검증용 헬퍼."""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation

from ..errors import TransferValidationError

IDENTIFIER_PATTERN = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")


def require_text(payload: dict, key: str) -> str:
    value = str(payload.get(key, "")).strip()
    if not value:
        raise TransferValidationError(f"'{key}' 값이 필요합니다.")
    return value


def parse_amount(raw: object) -> Decimal | None:
    """빈 값 / 'all' 은 None(전량)으로 해석한다."""
    if raw is None:
        return None
    text = str(raw).strip()
    if not text or text.lower() in {"all", "전체", "전부", "*"}:
        return None
    try:
        return Decimal(text.replace(",", ""))
    except InvalidOperation as exc:
        raise TransferValidationError(f"'{text}'은(는) 올바른 수량이 아닙니다.") from exc


def parse_flag(payload: dict, key: str) -> bool:
    value = payload.get(key, False)
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "on", "yes"}
