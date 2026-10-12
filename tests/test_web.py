"""웹 UI 라우트 테스트. 네트워크를 모킹해 렌더링과 검증 로직만 확인한다."""

from __future__ import annotations

import json
import sys
from decimal import Decimal
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from upbit_pocket.config import Settings
from upbit_pocket.models import Balance, Market, MarketPrice, Pocket, TransferRequest
from upbit_pocket.web import create_app

MAIN_UUID = "11111111-1111-1111-1111-111111111111"
SUB_UUID = "22222222-2222-2222-2222-222222222222"


def balance(currency, amount, locked="0"):
    return Balance(
        currency=currency,
        balance=Decimal(amount),
        locked=Decimal(locked),
        avg_buy_price=Decimal("0"),
        avg_buy_price_modified=False,
        unit_currency="KRW",
    )


class FakeClient:
    def __init__(self):
        self.transfers: list[TransferRequest] = []
        self.fail_next = False

    def list_pockets(self):
        return [
            Pocket(uuid=MAIN_UUID, name="메인포켓", type="main"),
            Pocket(uuid=SUB_UUID, name="단기", type="user_spot_trading"),
        ]

    def get_main_pocket_balances(self):
        return [balance("KRW", "1000000"), balance("BTC", "0.5", locked="0.1")]

    def get_sub_pocket_balances(self, uuid):
        return [balance("KRW", "10000")]

    def universal_transfer(self, request):
        self.transfers.append(request)
        return type(
            "T",
            (),
            {
                "uuid": "req-uuid-0001",
                "identifier": request.identifier,
                "state": "processing",
                "currency": request.currency,
                "amount": request.amount,
                "from_uuid": request.from_uuid,
                "to_uuid": request.to_uuid,
                "created_at": "2026-01-01T00:00:00+09:00",
            },
        )()

    def list_universal_transfers(self, **kwargs):
        return []

    def list_markets(self):
        return [Market("KRW-BTC", "비트코인", "Bitcoin")]

    def list_tickers(self, markets):
        price = Decimal("60000000") if "KRW-BTC" in markets else Decimal("1")
        return [MarketPrice("KRW-BTC", price)]


@pytest.fixture()
def client(monkeypatch):
    fake = FakeClient()
    monkeypatch.setattr("upbit_pocket.web.routes.UpbitClient", lambda settings: fake)
    settings = Settings(access_key="ak", secret_key="sk-secret-value")
    app = create_app(settings)
    app.config["TESTING"] = True
    with app.test_client() as test_client:
        test_client.fake = fake
        yield test_client


def csrf(client) -> str:
    with client.session_transaction() as session:
        return session.get("csrf_token") or ""


def bootstrap_csrf(client) -> str:
    client.get("/")
    return csrf(client)


def post(client, url, payload):
    return client.post(
        url,
        data=json.dumps(payload),
        content_type="application/json",
        headers={"X-CSRF-Token": csrf(client)},
    )


# ------------------------------------------------------------------ 페이지


def test_dashboard_renders_all_pockets(client):
    response = client.get("/")
    assert response.status_code == 200
    body = response.get_data(as_text=True)
    assert "메인포켓" in body
    assert "단기" in body
    assert "1,000,000" in body


# ------------------------------------------------------------- 합계 / 총액


def test_total_sums_every_pocket(client):
    data = client.get("/api/state").get_json()
    subtotals = [int(p["subtotal"].replace(",", "")) for p in data["pockets"]]
    assert int(data["total"].replace(",", "")) == sum(subtotals)
    assert len(subtotals) == 2


def test_total_splits_krw_and_crypto(client):
    data = client.get("/api/state").get_json()
    total = int(data["total"].replace(",", ""))
    krw = int(data["krw_total"].replace(",", ""))
    crypto = int(data["crypto_total"].replace(",", ""))
    assert total == krw + crypto
    # 메인포켓 KRW 1,000,000 + 서브포켓 KRW 10,000
    assert krw == 1_010_000
    # BTC 0.5 * 60,000,000
    assert crypto == 30_000_000


def test_total_warns_when_assets_cannot_be_priced(client):
    """시세를 못 잡은 자산은 합계에서 빠지므로 반드시 알려야 한다."""
    # ETHF 는 KRW 마켓도 BTC 마켓도 없는 종목이라 시세 조회가 불가능하다.
    client.fake.get_main_pocket_balances = lambda: [
        balance("KRW", "1000"),
        balance("ETHF", "12.5"),
    ]

    data = client.get("/api/state").get_json()
    assert data["has_unpriced"] is True
    assert [u["currency"] for u in data["unpriced"]] == ["ETHF"]
    assert data["unpriced"][0]["balance"] == "12.5"
    # 미평가 자산은 합계에 들어가지 않는다 (메인 1,000 + 서브 10,000)
    assert int(data["total"].replace(",", "")) == 11_000


def test_total_reports_no_warning_when_everything_is_priced(client):
    data = client.get("/api/state").get_json()
    assert data["has_unpriced"] is False
    assert data["unpriced"] == []


def test_zero_balance_unpriced_asset_is_not_flagged(client):
    client.fake.get_main_pocket_balances = lambda: [
        balance("KRW", "1000"),
        balance("ETHF", "0"),
    ]
    data = client.get("/api/state").get_json()
    assert data["has_unpriced"] is False


def test_dashboard_shows_total_and_unpriced_warning(client):
    client.fake.get_main_pocket_balances = lambda: [
        balance("KRW", "1000"),
        balance("ETHF", "12.5"),
    ]
    body = client.get("/").get_data(as_text=True)
    assert "전체 평가금액" in body
    assert "모든 포켓 합계" in body
    assert "시세를 확인하지 못한 자산" in body
    assert "ETHF" in body
    assert "포함되지 않았습니다" in body


def test_dashboard_summary_counts_pockets_and_assets(client):
    body = client.get("/").get_data(as_text=True)
    assert "포켓 · 보유자산" in body


# ------------------------------------------------------------------ 브랜드


def test_brand_shows_upbit_pocket_manager_title(client):
    body = client.get("/").get_data(as_text=True)
    assert "업비트 포켓 관리" in body
    assert '<span class="brand-text">업비트 포켓 관리</span>' in body


def test_brand_uses_committed_upbit_logo_by_default(client):
    """저장소에 로고가 포함되어 있으므로 기본 상태에서 로고를 쓴다."""
    from upbit_pocket.web.app import find_brand_logo

    assert find_brand_logo(client.application.static_folder) == "upbit-logo.png"

    body = client.get("/").get_data(as_text=True)
    assert "brand-mark-fallback" not in body
    assert '<img src="/static/upbit-logo.png"' in body


def test_brand_falls_back_to_letter_without_logo_file(client, tmp_path):
    """static 폴더에 로고가 없으면 U 마크로 안전하게 되돌아간다."""
    original = client.application.static_folder
    client.application.static_folder = str(tmp_path)
    try:
        body = client.get("/").get_data(as_text=True)
    finally:
        client.application.static_folder = original

    assert "brand-mark-fallback" in body
    assert "<img" not in body.split("</nav>")[0]


def test_brand_uses_logo_file_when_present(client, tmp_path):
    logo = tmp_path / "upbit-logo.svg"
    logo.write_text('<svg xmlns="http://www.w3.org/2000/svg"></svg>', encoding="utf-8")

    from upbit_pocket.web.app import find_brand_logo

    assert find_brand_logo(tmp_path) == "upbit-logo.svg"

    # static 폴더를 임시 디렉터리로 바꿔 로고가 있는 상황을 만든다.
    original = client.application.static_folder
    client.application.static_folder = str(tmp_path)
    try:
        body = client.get("/").get_data(as_text=True)
    finally:
        client.application.static_folder = original

    assert "brand-mark-fallback" not in body
    assert "upbit-logo.svg" in body
    assert '<img src="/static/upbit-logo.svg"' in body


def test_find_brand_logo_prefers_svg_over_png(tmp_path):
    (tmp_path / "logo.png").write_bytes(b"\x89PNG")
    (tmp_path / "upbit-logo.svg").write_text("<svg/>", encoding="utf-8")
    from upbit_pocket.web.app import find_brand_logo

    assert find_brand_logo(tmp_path) == "upbit-logo.svg"


def test_find_brand_logo_returns_none_when_missing(tmp_path):
    from upbit_pocket.web.app import find_brand_logo

    assert find_brand_logo(tmp_path) is None


def test_history_page_renders(client):
    response = client.get("/history")
    assert response.status_code == 200
    assert "자산 이전 내역" in response.get_data(as_text=True)


def test_state_api_returns_totals(client):
    response = client.get("/api/state")
    assert response.status_code == 200
    data = response.get_json()
    assert len(data["pockets"]) == 2
    assert "total" in data


# ------------------------------------------------------------------ CSRF


def test_plan_requires_csrf_token(client):
    response = client.post(
        "/api/plan",
        data=json.dumps({"from": MAIN_UUID, "to": SUB_UUID, "currency": "KRW"}),
        content_type="application/json",
    )
    assert response.status_code == 400
    assert "보안 토큰" in response.get_json()["error"]


def test_plan_rejects_wrong_csrf_token(client):
    bootstrap_csrf(client)
    response = client.post(
        "/api/plan",
        data=json.dumps({"from": MAIN_UUID, "to": SUB_UUID, "currency": "KRW"}),
        content_type="application/json",
        headers={"X-CSRF-Token": "forged"},
    )
    assert response.status_code == 400


# ------------------------------------------------------------------ 계획


def test_plan_single_currency_full_amount(client):
    bootstrap_csrf(client)
    response = post(client, "/api/plan", {"from": MAIN_UUID, "to": SUB_UUID, "currency": "KRW"})
    data = response.get_json()
    assert data["ok"] is True
    assert data["plans"][0]["amount"] == "1,000,000"
    assert data["plans"][0]["is_full"] is True
    assert client.fake.transfers == []


def test_plan_all_assets_excludes_locked_by_default(client):
    bootstrap_csrf(client)
    response = post(client, "/api/plan", {"from": MAIN_UUID, "to": SUB_UUID, "currency": "*"})
    plans = {p["currency"]: p for p in response.get_json()["plans"]}
    assert plans["KRW"]["amount"] == "1,000,000"
    assert plans["BTC"]["amount"] == "0.4"  # 0.5 - 0.1 locked


def test_plan_all_assets_includes_locked_when_asked(client):
    bootstrap_csrf(client)
    response = post(
        client,
        "/api/plan",
        {"from": MAIN_UUID, "to": SUB_UUID, "currency": "*", "include_locked": True},
    )
    plans = {p["currency"]: p for p in response.get_json()["plans"]}
    assert plans["BTC"]["amount"] == "0.5"


def test_plan_partial_amount(client):
    bootstrap_csrf(client)
    response = post(
        client, "/api/plan", {"from": MAIN_UUID, "to": SUB_UUID, "currency": "KRW", "amount": "100000"}
    )
    plan = response.get_json()["plans"][0]
    assert plan["amount"] == "100,000"
    assert plan["is_full"] is False


def test_plan_rejects_same_pocket(client):
    bootstrap_csrf(client)
    response = post(client, "/api/plan", {"from": MAIN_UUID, "to": MAIN_UUID, "currency": "KRW"})
    assert response.status_code == 400
    assert "같습니다" in response.get_json()["error"]


def test_plan_rejects_overdraft(client):
    bootstrap_csrf(client)
    response = post(
        client, "/api/plan", {"from": MAIN_UUID, "to": SUB_UUID, "currency": "KRW", "amount": "99999999"}
    )
    assert response.status_code == 400
    assert "초과" in response.get_json()["error"]


def test_plan_rejects_invalid_amount(client):
    bootstrap_csrf(client)
    response = post(
        client, "/api/plan", {"from": MAIN_UUID, "to": SUB_UUID, "currency": "KRW", "amount": "abc"}
    )
    assert response.status_code == 400


def test_plan_rejects_unknown_currency(client):
    bootstrap_csrf(client)
    response = post(client, "/api/plan", {"from": MAIN_UUID, "to": SUB_UUID, "currency": "XRP"})
    assert response.status_code == 400
    assert "XRP" in response.get_json()["error"]


def test_plan_accepts_pocket_name(client):
    bootstrap_csrf(client)
    response = post(client, "/api/plan", {"from": "메인포켓", "to": "단기", "currency": "KRW"})
    assert response.get_json()["ok"] is True


# ------------------------------------------------------------------ 실행


def test_transfer_requires_confirmation_flag(client):
    bootstrap_csrf(client)
    response = post(client, "/api/transfer", {"from": MAIN_UUID, "to": SUB_UUID, "currency": "KRW"})
    assert response.status_code == 400
    assert "확인" in response.get_json()["error"]
    assert client.fake.transfers == []


def test_transfer_executes_and_returns_state(client):
    bootstrap_csrf(client)
    response = post(
        client,
        "/api/transfer",
        {"from": MAIN_UUID, "to": SUB_UUID, "currency": "BTC", "confirmed": True},
    )
    data = response.get_json()
    assert data["ok"] is True
    assert data["results"][0]["state"] == "processing"
    assert data["results"][0]["route"] == "메인포켓 → 단기"
    assert len(client.fake.transfers) == 1
    assert client.fake.transfers[0].amount == Decimal("0.4")


def test_transfer_all_sends_one_request_per_currency(client):
    bootstrap_csrf(client)
    response = post(
        client,
        "/api/transfer",
        {"from": MAIN_UUID, "to": SUB_UUID, "currency": "*", "confirmed": True},
    )
    assert response.get_json()["ok"] is True
    assert {t.currency for t in client.fake.transfers} == {"KRW", "BTC"}
    assert len({t.identifier for t in client.fake.transfers}) == 2


def test_transfer_revalidates_amount_at_execution_time(client):
    """계획 후 잔고가 줄어든 경우 실행 시점에 다시 차단되어야 한다."""
    bootstrap_csrf(client)
    client.fake.get_main_pocket_balances = lambda: [balance("KRW", "10")]
    response = post(
        client,
        "/api/transfer",
        {"from": MAIN_UUID, "to": SUB_UUID, "currency": "KRW", "amount": "9999", "confirmed": True},
    )
    assert response.status_code == 400
    assert client.fake.transfers == []


# ---------------------------------------------------- API 본문 수량 (회귀)


def test_web_transfer_sends_unformatted_amount_to_upbit(client):
    """화면에는 쉼표가 보여도 업비트 요청 본문에는 없어야 한다.

    쉼표가 들어가면 업비트가 invalid_parameter로 거절한다.
    """
    bootstrap_csrf(client)
    response = post(
        client,
        "/api/transfer",
        {"from": MAIN_UUID, "to": SUB_UUID, "currency": "KRW", "amount": "1000000", "confirmed": True},
    )
    assert response.status_code == 200

    payload = client.fake.transfers[0].to_payload()
    assert payload["amount"] == "1000000"
    assert "," not in payload["amount"]

    # 화면에는 사람이 읽기 좋은 쉼표 포맷으로 보인다.
    display = response.get_json()["results"][0]["amount"]
    assert display == "1,000,000"
