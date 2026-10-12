"""JWT 인증 토큰 생성."""

from __future__ import annotations

import hashlib
import uuid
from typing import Any, Iterable, Sequence
from urllib.parse import unquote, urlencode

import jwt

ALGORITHM = "HS512"
HASH_ALG = "SHA512"


def build_query_string(params: Sequence[tuple[str, Any]] | dict[str, Any]) -> str:
    """요청 파라미터/본문을 쿼리 문자열로 변환한다.

    업비트는 URL 인코딩되지 않은 쿼리 문자열을 기준으로 query_hash를 계산한다.
    순서를 바꾸지 않고, `states[]` 처럼 이름에 []가 포함된 키는 그대로 유지한다.
    """
    if isinstance(params, dict):
        items: Iterable[tuple[str, Any]] = list(params.items())
    else:
        items = list(params)

    pairs = [(str(key), str(value)) for key, value in items if value is not None]
    return unquote(urlencode(pairs))


def create_token(access_key: str, secret_key: str, query_string: str = "") -> str:
    payload: dict[str, Any] = {
        "access_key": access_key,
        "nonce": str(uuid.uuid4()),
    }
    if query_string:
        payload["query_hash"] = hashlib.sha512(query_string.encode("utf-8")).hexdigest()
        payload["query_hash_alg"] = HASH_ALG

    token = jwt.encode(payload, secret_key, algorithm=ALGORITHM)
    return token if isinstance(token, str) else token.decode("utf-8")
