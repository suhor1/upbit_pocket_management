"""업비트 REST API 클라이언트."""

from __future__ import annotations

import time
from typing import Any, Sequence

import requests

from .auth import build_query_string, create_token
from .config import Settings
from .errors import UpbitAPIError
from .models import Balance, Market, MarketPrice, Pocket, Transfer, TransferRequest

# 포켓 단위 초당 30회 제한을 여유 있게 지키기 위한 최소 호출 간격.
MIN_INTERVAL = 0.05


class UpbitClient:
    def __init__(self, settings: Settings, timeout: float = 10.0, session: requests.Session | None = None):
        self._settings = settings
        self._session = session or requests.Session()
        self._timeout = timeout
        self._last_request_at = 0.0

    # ------------------------------------------------------------------ 공통

    def _throttle(self) -> None:
        elapsed = time.monotonic() - self._last_request_at
        if elapsed < MIN_INTERVAL:
            time.sleep(MIN_INTERVAL - elapsed)
        self._last_request_at = time.monotonic()

    def _request(
        self,
        method: str,
        path: str,
        params: Sequence[tuple[str, Any]] | dict[str, Any] | None = None,
        body: dict[str, Any] | None = None,
    ) -> Any:
        query_string = ""
        if params:
            query_string = build_query_string(params)
        elif body is not None:
            query_string = build_query_string(body)

        token = create_token(
            self._settings.access_key,
            self._settings.secret_key,
            query_string,
        )

        headers = {
            "Authorization": f"Bearer {token}",
            "Accept": "application/json",
        }
        if body is not None:
            headers["Content-Type"] = "application/json"

        url = f"{self._settings.base_url}{path}"
        if query_string and body is None:
            url = f"{url}?{query_string}"

        self._throttle()
        response = self._session.request(
            method,
            url,
            headers=headers,
            json=body,
            timeout=self._timeout,
        )

        if response.status_code >= 400:
            raise self._to_error(response)

        if not response.content:
            return None
        return response.json()

    @staticmethod
    def _to_error(response: requests.Response) -> UpbitAPIError:
        name, message = "unknown_error", response.text
        try:
            payload = response.json()
            if isinstance(payload, dict) and isinstance(payload.get("error"), dict):
                name = str(payload["error"].get("name", name))
                message = str(payload["error"].get("message", message))
        except ValueError:
            pass
        return UpbitAPIError(name, message, response.status_code)

    # -------------------------------------------------------------- Exchange

    def list_pockets(self) -> list[Pocket]:
        payload = self._request("GET", "/v1/pockets")
        return [Pocket.from_payload(item) for item in payload]

    def get_main_pocket_balances(self) -> list[Balance]:
        """현재 API Key가 속한 포켓(메인포켓)의 잔고."""
        payload = self._request("GET", "/v1/accounts")
        return [Balance.from_payload(item) for item in payload]

    def get_sub_pocket_balances(self, pocket_uuid: str) -> list[Balance]:
        payload = self._request("GET", "/v1/pockets/assets", params=[("uuid", pocket_uuid)])
        return [Balance.from_payload(item) for item in payload]

    def universal_transfer(self, request: TransferRequest) -> Transfer:
        """메인포켓 API Key로 포켓 간 자산 이전을 요청한다."""
        payload = self._request(
            "POST",
            "/v1/pockets/universal_transfers",
            body=request.to_payload(),
        )
        return Transfer.from_payload(payload)

    def list_universal_transfers(self, **kwargs: Any) -> list[Transfer]:
        params: list[tuple[str, Any]] = []
        for key in ("from", "to", "currency", "start_time", "end_time", "limit", "order_by"):
            if kwargs.get(key) is not None:
                params.append((key, kwargs[key]))
        for key in ("states", "uuids", "identifiers"):
            for value in kwargs.get(key) or []:
                params.append((f"{key}[]", value))

        payload = self._request("GET", "/v1/pockets/universal_transfers", params=params)
        return [Transfer.from_payload(item) for item in payload]

    # ------------------------------------------------------------- Quotation

    def list_markets(self) -> list[Market]:
        payload = self._request("GET", "/v1/market/all")
        return [Market.from_payload(item) for item in payload]

    def list_tickers(self, markets: Sequence[str]) -> list[MarketPrice]:
        if not markets:
            return []
        payload = self._request("GET", "/v1/ticker", params=[("markets", ",".join(markets))])
        return [MarketPrice.from_payload(item) for item in payload]
