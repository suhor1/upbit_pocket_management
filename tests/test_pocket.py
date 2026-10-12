"""네트워크 없이 도메인 로직을 검증하는 테스트."""

from __future__ import annotations

import hashlib
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from upbit_pocket.auth import build_query_string, create_token
from upbit_pocket.client import UpbitClient
from upbit_pocket.errors import TransferValidationError
from upbit_pocket.models import (
    Balance,
    Market,
    MarketPrice,
    Pocket,
    TransferRequest,
    format_amount,
    to_api_amount,
)
from upbit_pocket.pricing import PriceService
from upbit_pocket.service import PocketService, PocketSnapshot

MAIN_UUID = "11111111-1111-1111-1111-111111111111"
SUB1_UUID = "22222222-2222-2222-2222-222222222222"
SUB2_UUID = "33333333-3333-3333-3333-333333333333"


def balance(currency: str, amount: str, locked: str = "0", avg: str = "0", unit: str = "KRW") -> Balance:
    return Balance(
        currency=currency,
        balance=Decimal(amount),
        locked=Decimal(locked),
        avg_buy_price=Decimal(avg),
        avg_buy_price_modified=False,
        unit_currency=unit,
    )


class FakeClient:
    def __init__(self):
        self.pockets = [
            Pocket(uuid=SUB1_UUID, name="단기", type="user_spot_trading"),
            Pocket(uuid=MAIN_UUID, name="메인포켓", type="main"),
            Pocket(uuid=SUB2_UUID, name="장기", type="user_spot_trading"),
        ]
        self.assets = {
            MAIN_UUID: [balance("KRW", "1000000"), balance("BTC", "0.5", avg="140000000")],
            SUB1_UUID: [balance("KRW", "10000")],
            SUB2_UUID: [],
        }
        self.transferred: list[TransferRequest] = []

    def list_pockets(self):
        return self.pockets

    def get_main_pocket_balances(self):
        return self.assets[MAIN_UUID]

    def get_sub_pocket_balances(self, uuid):
        return self.assets.get(uuid, [])

    def universal_transfer(self, request):
        self.transferred.append(request)

        class Result:
            uuid = "req-uuid"
            state = "processing"
            identifier = request.identifier
            from_uuid = request.from_uuid
            to_uuid = request.to_uuid
            currency = request.currency
            amount = request.amount
            created_at = "2026-01-01T00:00:00+09:00"

        return Result()

    def list_markets(self):
        return [
            Market("KRW-BTC", "비트코인", "Bitcoin"),
            Market("BTC-ETH", "이더리움", "Ethereum"),
            Market("KRW-ETH", "이더리움", "Ethereum"),
        ]

    def list_tickers(self, markets):
        prices = {"KRW-BTC": Decimal("60000000"), "KRW-ETH": Decimal("3000000"), "BTC-ETH": Decimal("0.05")}
        return [MarketPrice(m, prices[m]) for m in markets if m in prices]


@pytest.fixture()
def service():
    return PocketService(FakeClient())


# ------------------------------------------------------------------- 인증


def test_build_query_string_keeps_order_and_array_brackets():
    params = [("states[]", "processing"), ("states[]", "done"), ("currency", "XRP"), ("limit", 2)]
    assert build_query_string(params) == "states[]=processing&states[]=done&currency=XRP&limit=2"


def test_create_token_contains_sha512_query_hash():
    query = "uuid=abc"
    token = create_token("access", "secret", query)
    import jwt as pyjwt

    payload = pyjwt.decode(token, "secret", algorithms=["HS512"])
    assert payload["query_hash"] == hashlib.sha512(query.encode()).hexdigest()
    assert payload["query_hash_alg"] == "SHA512"
    assert "nonce" in payload


def test_create_token_without_query_has_no_hash():
    import jwt as pyjwt

    payload = pyjwt.decode(create_token("access", "secret"), "secret", algorithms=["HS512"])
    assert "query_hash" not in payload


# ------------------------------------------------------------------ 포켓


def test_pockets_are_sorted_with_main_first(service):
    names = [p.name for p in service.pockets()]
    assert names[0] == "메인포켓"
    assert set(names[1:]) == {"단기", "장기"}


def test_find_pocket_by_name_prefix_and_uuid(service):
    assert service.find_pocket("메인포켓").uuid == MAIN_UUID
    assert service.find_pocket(SUB1_UUID).uuid == SUB1_UUID
    assert service.find_pocket("22222222").uuid == SUB1_UUID
    with pytest.raises(TransferValidationError):
        service.find_pocket("없는포켓")


def test_snapshot_covers_every_pocket(service):
    snapshots = service.snapshot()
    assert len(snapshots) == 3
    assert isinstance(snapshots[0], PocketSnapshot)
    assert snapshots[0].pocket.is_main


# -------------------------------------------------------------- 이전 계획


def test_build_plan_defaults_to_full_available(service):
    main = service.find_pocket("메인포켓")
    sub = service.find_pocket("단기")
    plan = service.build_plan(main, sub, "BTC", None)
    assert plan.amount == Decimal("0.5")
    assert plan.is_full


def test_build_plan_accepts_partial_amount(service):
    main = service.find_pocket("메인포켓")
    sub = service.find_pocket("단기")
    plan = service.build_plan(main, sub, "BTC", Decimal("0.1"))
    assert plan.amount == Decimal("0.1")
    assert not plan.is_full


def test_build_plan_respects_locked_balance():
    client = FakeClient()
    client.assets[MAIN_UUID] = [balance("BTC", "1", locked="0.4")]
    service = PocketService(client)
    plan = service.build_plan(
        service.find_pocket("메인포켓"), service.find_pocket("장기"), "BTC", None
    )
    assert plan.amount == Decimal("0.6")


def test_build_plan_rejects_same_pocket(service):
    main = service.find_pocket("메인포켓")
    with pytest.raises(TransferValidationError):
        service.build_plan(main, main, "BTC", None)


def test_build_plan_rejects_overdraft(service):
    main = service.find_pocket("메인포켓")
    sub = service.find_pocket("단기")
    with pytest.raises(TransferValidationError):
        service.build_plan(main, sub, "BTC", Decimal("10"))


def test_build_plan_rejects_zero_and_negative(service):
    main = service.find_pocket("메인포켓")
    sub = service.find_pocket("단기")
    for amount in (Decimal("0"), Decimal("-1")):
        with pytest.raises(TransferValidationError):
            service.build_plan(main, sub, "KRW", amount)


def test_build_plan_rejects_missing_currency(service):
    main = service.find_pocket("메인포켓")
    sub = service.find_pocket("단기")
    with pytest.raises(TransferValidationError):
        service.build_plan(main, sub, "XRP", None)


def test_build_plan_for_all_covers_available_assets():
    client = FakeClient()
    client.assets[MAIN_UUID] = [
        balance("KRW", "1000"),
        balance("BTC", "2", locked="0.5"),
        balance("ETH", "0"),
    ]
    service = PocketService(client)
    plans = service.build_plan_for_all(
        service.find_pocket("메인포켓"), service.find_pocket("장기")
    )
    assert [(p.currency, p.amount) for p in plans] == [("KRW", Decimal("1000")), ("BTC", Decimal("1.5"))]


def test_build_plan_for_all_can_include_locked():
    client = FakeClient()
    client.assets[MAIN_UUID] = [balance("BTC", "2", locked="0.5")]
    service = PocketService(client)
    plans = service.build_plan_for_all(
        service.find_pocket("메인포켓"), service.find_pocket("장기"), include_locked=True
    )
    assert plans[0].amount == Decimal("2")


def test_execute_sends_unique_identifiers(service):
    main = service.find_pocket("메인포켓")
    sub = service.find_pocket("단기")
    plans = service.build_plan_for_all(main, sub)
    results = service.execute(plans)
    identifiers = [r.identifier for r in service._client.transferred]
    assert len(set(identifiers)) == len(identifiers)
    assert all(len(i) <= 64 for i in identifiers)
    assert len(results) == len(plans)


# ------------------------------------------------------------------ 시세


def test_price_book_uses_krw_market_directly(service):
    book = service.price_book_for(service.snapshot())
    assert book.get("KRW") == Decimal("1")
    assert book.get("BTC") is not None


def test_price_book_falls_back_to_btc_conversion():
    class TickerClient(FakeClient):
        """KRW 마켓이 없는 자산은 BTC 마켓을 경유해 원화 환산한다."""

        def list_markets(self):
            return [Market("KRW-BTC", "비트코인", "Bitcoin"), Market("BTC-ETH", "이더리움", "Ethereum")]

        def list_tickers(self, markets):
            prices = {"KRW-BTC": Decimal("1000"), "BTC-ETH": Decimal("2")}
            return [MarketPrice(m, prices[m]) for m in markets if m in prices]

    book = PriceService(TickerClient()).price_book({"ETH"})
    assert book.get("ETH") == Decimal("2000")


# ------------------------------------------------------------------ 포맷


def test_format_amount_avoids_scientific_notation():
    assert format_amount(Decimal("1000000")) == "1,000,000"
    assert format_amount(Decimal("0.5")) == "0.5"
    assert format_amount(Decimal("0")) == "0"


def test_transfer_request_payload_omits_empty_identifier():
    request = TransferRequest(MAIN_UUID, SUB1_UUID, "KRW", Decimal("1000"))
    assert "identifier" not in request.to_payload()
    assert request.to_payload()["from"] == MAIN_UUID


# ------------------------------------------------- API 요청 수량 포맷 (회귀)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("1000000", "1000000"),
        ("0.5", "0.5"),
        ("0.04748728", "0.04748728"),
        ("3166805.80007475", "3166805.80007475"),
        ("1E+3", "1000"),
        ("0", "0"),
    ],
)
def test_api_amount_has_no_separators(value, expected):
    """업비트는 쉼표가 들어간 amount를 invalid_parameter로 거절한다."""
    assert to_api_amount(Decimal(value)) == expected
    assert "," not in to_api_amount(Decimal(value))


def test_api_amount_never_uses_scientific_notation():
    assert "E" not in to_api_amount(Decimal("1E+9")).upper()
    assert to_api_amount(Decimal("1E+9")) == "1000000000"


def test_transfer_payload_amount_is_api_safe():
    """표시용 쉼표 포맷이 API 본문에 섞이지 않아야 한다."""
    request = TransferRequest(MAIN_UUID, SUB1_UUID, "KRW", Decimal("1000000"))
    amount = request.to_payload()["amount"]
    assert amount == "1000000"
    assert "," not in amount


def test_display_and_api_formats_differ():
    value = Decimal("3166805.80007475")
    assert format_amount(value) == "3,166,805.80007475"
    assert to_api_amount(value) == "3166805.80007475"
