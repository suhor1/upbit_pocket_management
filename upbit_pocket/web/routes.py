"""웹 UI 라우트."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone
from decimal import Decimal

from flask import Blueprint, current_app, jsonify, render_template, request, session

from ..client import UpbitClient
from ..config import Settings
from ..errors import TransferValidationError, UpbitPocketError
from ..models import format_amount
from ..service import PocketService, PocketSnapshot
from .forms import parse_amount, parse_flag, require_text

bp = Blueprint("web", __name__)

KST = timezone(timedelta(hours=9))


def get_service() -> PocketService:
    """요청마다 PocketService를 만든다. (캐시되지 않는 시세 반영)"""
    return PocketService(UpbitClient(current_app.config["SETTINGS"]))


def csrf_token() -> str:
    if "csrf_token" not in session:
        session["csrf_token"] = secrets.token_urlsafe(32)
    return session["csrf_token"]


def ensure_csrf() -> None:
    sent = request.headers.get("X-CSRF-Token") or (request.form.get("csrf_token") or "")
    if not secrets.compare_digest(str(sent), csrf_token()):
        raise TransferValidationError("보안 토큰이 만료되었습니다. 페이지를 새로고침해주세요.")


def snapshot_context(service: PocketService) -> dict:
    snapshots = service.snapshot()
    prices = service.price_book_for(snapshots)
    names = service.market_names()

    total = Decimal("0")
    pocket_rows = []
    for snap in snapshots:
        subtotal = Decimal("0")
        rows = []
        for balance in sorted(snap.balances, key=lambda b: (b.currency != "KRW", b.currency)):
            price = prices.get(balance.currency)
            valuation = balance.balance * price if price is not None else None
            if valuation is not None:
                subtotal += valuation
            rows.append(
                {
                    "currency": balance.currency,
                    "name": names.get(balance.currency, ""),
                    "balance": format_amount(balance.balance),
                    "locked": format_amount(balance.locked),
                    "available": format_amount(balance.available),
                    "has_locked": balance.locked > 0,
                    "avg_buy_price": format_amount(balance.avg_buy_price),
                    "unit_currency": balance.unit_currency,
                    "price": format_amount(price) if price is not None else None,
                    "valuation": format_amount(valuation, 0) if valuation is not None else None,
                    "has_balance": balance.balance > 0,
                }
            )
        total += subtotal
        pocket_rows.append(
            {
                "uuid": snap.pocket.uuid,
                "name": snap.pocket.name,
                "is_main": snap.pocket.is_main,
                "short_uuid": snap.pocket.short_uuid,
                "rows": rows,
                "subtotal": f"{subtotal:,.0f}",
                "asset_count": sum(1 for r in rows if r["has_balance"]),
            }
        )

    return {
        "pockets": pocket_rows,
        "total": f"{total:,.0f}",
        "generated_at": datetime.now(KST).strftime("%Y-%m-%d %H:%M:%S KST"),
    }


# ------------------------------------------------------------------ 페이지


@bp.get("/")
def dashboard():
    service = get_service()
    context = snapshot_context(service)
    context["csrf_token"] = csrf_token()
    context["has_sub_pocket"] = any(not p["is_main"] for p in context["pockets"])
    return render_template("dashboard.html", **context)


@bp.get("/history")
def history():
    service = get_service()
    pockets = service.pockets()
    limit = request.args.get("limit", default=50, type=int)
    limit = max(1, min(limit, 100))

    states = [s.strip() for s in request.args.get("states", "").split(",") if s.strip()]
    transfers = service.transfers(
        limit=limit,
        order_by="desc",
        states=states or None,
        currency=(request.args.get("currency") or "").strip().upper() or None,
    )

    lookup = {pocket.uuid: pocket.name for pocket in pockets}
    return render_template(
        "history.html",
        csrf_token=csrf_token(),
        transfers=[
            {
                "created_at": t.created_at,
                "from_name": lookup.get(t.from_uuid, t.from_uuid[:8]),
                "to_name": lookup.get(t.to_uuid, t.to_uuid[:8]),
                "currency": t.currency,
                "amount": format_amount(t.amount),
                "state": t.state,
                "state_label": {
                    "done": "완료",
                    "failed": "실패",
                    "processing": "처리 중",
                    "submitted": "접수",
                }.get(t.state, t.state),
                "uuid": t.uuid,
                "identifier": t.identifier or "-",
            }
            for t in transfers
        ],
        filters={
            "limit": limit,
            "states": ",".join(states),
            "currency": (request.args.get("currency") or "").strip().upper(),
        },
        state_options=[
            ("done", "완료"),
            ("failed", "실패"),
            ("processing", "처리 중"),
            ("submitted", "접수"),
        ],
    )


# --------------------------------------------------------------------- API


@bp.get("/api/state")
def api_state():
    """대시보드 자동 갱신용."""
    service = get_service()
    context = snapshot_context(service)
    context["csrf_token"] = csrf_token()
    return jsonify(context)


def _resolve(service: PocketService, payload: dict) -> tuple:
    snapshots = service.snapshot()
    by_uuid = {snap.pocket.uuid: snap for snap in snapshots}

    source = service.find_pocket(require_text(payload, "from"))
    target = service.find_pocket(require_text(payload, "to"))
    currency = require_text(payload, "currency").upper()
    amount = parse_amount(payload.get("amount"))
    include_locked = parse_flag(payload, "include_locked")

    if source.uuid not in by_uuid:
        raise TransferValidationError("출발 포켓의 잔고를 확인할 수 없습니다.")

    if currency == "*":
        plans = service.build_plan_for_all(
            source, target, snapshots, include_locked=include_locked
        )
    else:
        plans = [service.build_plan(source, target, currency, amount, snapshots)]

    return service, snapshots, plans


@bp.post("/api/plan")
def api_plan():
    """실제 전송 없이 이전 계획만 계산한다."""
    try:
        ensure_csrf()
        service, _, plans = _resolve(get_service(), request.get_json(silent=True) or {})
        return jsonify({"ok": True, "plans": [serialize_plan(p) for p in plans]})
    except (TransferValidationError, UpbitPocketError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


@bp.post("/api/transfer")
def api_transfer():
    """계획을 다시 검증한 뒤 실제로 이전을 실행한다."""
    try:
        ensure_csrf()
        payload = request.get_json(silent=True) or {}
        service, _, plans = _resolve(get_service(), payload)

        if not parse_flag(payload, "confirmed"):
            return jsonify({"ok": False, "error": "실행 확인이 필요합니다."}), 400

        results = service.execute(plans)
        return jsonify(
            {
                "ok": True,
                "results": [
                    {
                        "uuid": r.uuid,
                        "identifier": r.identifier,
                        "state": r.state,
                        "currency": r.currency,
                        "amount": format_amount(r.amount),
                        "route": f"{plan.from_pocket.name} → {plan.to_pocket.name}",
                    }
                    for plan, r in zip(plans, results)
                ],
            }
        )
    except (TransferValidationError, UpbitPocketError) as exc:
        return jsonify({"ok": False, "error": str(exc)}), 400


def serialize_plan(plan) -> dict:
    return {
        "from": plan.from_pocket.name,
        "from_uuid": plan.from_pocket.uuid,
        "to": plan.to_pocket.name,
        "to_uuid": plan.to_pocket.uuid,
        "currency": plan.currency,
        "amount": format_amount(plan.amount),
        "available": format_amount(plan.available),
        "is_full": plan.is_full,
    }
