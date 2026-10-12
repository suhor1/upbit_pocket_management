"""통화별 원화 시세 조회."""

from __future__ import annotations

from decimal import Decimal

from .client import UpbitClient
from .models import Market, PriceBook

TICKER_BATCH_SIZE = 40


class PriceService:
    def __init__(self, client: UpbitClient):
        self._client = client
        self._markets: list[Market] | None = None

    def markets(self) -> list[Market]:
        if self._markets is None:
            self._markets = self._client.list_markets()
        return self._markets

    def price_book(self, currencies: set[str]) -> PriceBook:
        """요청한 통화들에 대한 원화 기준 시세를 한 번에 조회한다."""
        wanted = {c.upper() for c in currencies} - {"KRW"}
        if not wanted:
            return PriceBook({"KRW": Decimal("1")})

        by_base: dict[str, dict[str, str]] = {}
        for market in self.markets():
            by_base.setdefault(market.base, {})[market.quote] = market.market

        # KRW 마켓을 우선 사용하고, 없으면 BTC 경유로 환산한다.
        targets: dict[str, str] = {}
        via_btc: dict[str, str] = {}
        for currency in sorted(wanted):
            quotes = by_base.get(currency, {})
            if "KRW" in quotes:
                targets[currency] = quotes["KRW"]
            elif "BTC" in quotes:
                via_btc[currency] = quotes["BTC"]

        if "BTC" not in wanted and via_btc:
            targets["BTC"] = "KRW-BTC"

        tickers: dict[str, Decimal] = {}
        codes = list(dict.fromkeys([*targets.values(), *via_btc.values()]))
        for index in range(0, len(codes), TICKER_BATCH_SIZE):
            batch = codes[index : index + TICKER_BATCH_SIZE]
            for price in self._client.list_tickers(batch):
                tickers[price.market] = price.trade_price

        book = PriceBook({"KRW": Decimal("1")})
        for currency, code in targets.items():
            book.prices[currency] = tickers.get(code)
        btc_krw = book.prices.get("BTC")
        for currency, code in via_btc.items():
            rate = tickers.get(code)
            book.prices[currency] = rate * btc_krw if rate is not None and btc_krw is not None else None
        return book
