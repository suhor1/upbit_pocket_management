"""업비트 API 도메인 모델."""

from __future__ import annotations

from dataclasses import dataclass, field
from decimal import Decimal

MAIN_POCKET = "main"
SUB_POCKET = "user_spot_trading"


@dataclass(frozen=True)
class Pocket:
    uuid: str
    name: str
    type: str

    @property
    def is_main(self) -> bool:
        return self.type == MAIN_POCKET

    @property
    def short_uuid(self) -> str:
        return self.uuid[:8]

    @classmethod
    def from_payload(cls, payload: dict) -> "Pocket":
        return cls(
            uuid=payload["uuid"],
            name=payload.get("name", ""),
            type=payload.get("type", ""),
        )


@dataclass(frozen=True)
class Balance:
    currency: str
    balance: Decimal
    locked: Decimal
    avg_buy_price: Decimal
    avg_buy_price_modified: bool
    unit_currency: str

    @property
    def available(self) -> Decimal:
        return self.balance - self.locked

    @property
    def has_balance(self) -> bool:
        return self.balance > 0

    @classmethod
    def from_payload(cls, payload: dict) -> "Balance":
        return cls(
            currency=payload["currency"],
            balance=Decimal(str(payload["balance"])),
            locked=Decimal(str(payload.get("locked", "0"))),
            avg_buy_price=Decimal(str(payload.get("avg_buy_price", "0"))),
            avg_buy_price_modified=bool(payload.get("avg_buy_price_modified", False)),
            unit_currency=payload.get("unit_currency", ""),
        )


@dataclass(frozen=True)
class Market:
    market: str
    korean_name: str
    english_name: str

    @property
    def quote(self) -> str:
        return self.market.split("-", 1)[0]

    @property
    def base(self) -> str:
        return self.market.split("-", 1)[1]

    @classmethod
    def from_payload(cls, payload: dict) -> "Market":
        return cls(
            market=payload["market"],
            korean_name=payload.get("korean_name", ""),
            english_name=payload.get("english_name", ""),
        )


@dataclass(frozen=True)
class TransferRequest:
    from_uuid: str
    to_uuid: str
    currency: str
    amount: Decimal
    identifier: str | None = None

    def to_payload(self) -> dict:
        payload = {
            "from": self.from_uuid,
            "to": self.to_uuid,
            "currency": self.currency,
            "amount": format_amount(self.amount),
        }
        if self.identifier:
            payload["identifier"] = self.identifier
        return payload


@dataclass(frozen=True)
class Transfer:
    uuid: str
    from_uuid: str
    to_uuid: str
    state: str
    currency: str
    amount: Decimal
    created_at: str
    identifier: str | None = None

    @property
    def is_finished(self) -> bool:
        return self.state in {"done", "failed"}

    @classmethod
    def from_payload(cls, payload: dict) -> "Transfer":
        return cls(
            uuid=payload.get("uuid", ""),
            from_uuid=payload.get("from", ""),
            to_uuid=payload.get("to", ""),
            state=payload.get("state", ""),
            currency=payload.get("currency", ""),
            amount=Decimal(str(payload.get("amount", "0"))),
            created_at=payload.get("created_at", ""),
            identifier=payload.get("identifier"),
        )


@dataclass(frozen=True)
class MarketPrice:
    market: str
    trade_price: Decimal

    @classmethod
    def from_payload(cls, payload: dict) -> "MarketPrice":
        return cls(
            market=payload["market"],
            trade_price=Decimal(str(payload.get("trade_price", "0"))),
        )


@dataclass
class PriceBook:
    """통화별 원화 시세. 없는 통화는 None."""

    prices: dict[str, Decimal | None] = field(default_factory=dict)

    def get(self, currency: str) -> Decimal | None:
        return self.prices.get(currency)


def format_amount(value: Decimal, places: int = 8) -> str:
    """Decimal을 지수 표기 없이 문자열로 변환한다."""
    text = f"{value:,.{places}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def format_krw(value: Decimal) -> str:
    return f"{value.quantize(Decimal('1')):,.0f}"
