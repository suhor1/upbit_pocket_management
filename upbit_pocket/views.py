"""포켓 현황 / 이전 내역 렌더링."""

from __future__ import annotations

from decimal import Decimal

from .display import BLUE, BOLD, CYAN, DIM, GREEN, RED, YELLOW, colorize, pad, render_table
from .models import Pocket, PriceBook, Transfer, format_amount
from .service import PocketSnapshot, TransferPlan

STATE_COLORS = {
    "done": GREEN,
    "failed": RED,
    "processing": YELLOW,
    "submitted": DIM,
}


def render_pocket_list(pockets: list[Pocket]) -> str:
    rows = []
    for index, pocket in enumerate(pockets, start=1):
        kind = "메인포켓" if pocket.is_main else "서브포켓"
        rows.append([str(index), pocket.name, kind, pocket.uuid])
    return render_table(["#", "포켓 이름", "종류", "UUID"], rows)


def render_snapshot(
    snapshots: list[PocketSnapshot],
    prices: PriceBook,
    market_names: dict[str, str],
) -> str:
    blocks: list[str] = []
    grand_total = Decimal("0")

    for snap in snapshots:
        balances = [b for b in snap.balances if b.has_balance or b.locked > 0]
        if not balances:
            balances = list(snap.balances)

        rows = []
        subtotal = Decimal("0")
        priced_count = 0
        for balance in balances:
            price = prices.get(balance.currency)
            valuation = balance.balance * price if price is not None else None
            if valuation is not None:
                subtotal += valuation
                priced_count += 1

            name = market_names.get(balance.currency, "")
            rows.append(
                [
                    f"{balance.currency} {name}".strip(),
                    format_amount(balance.balance),
                    format_amount(balance.locked) if balance.locked > 0 else "-",
                    f"{format_amount(balance.avg_buy_price)} {balance.unit_currency}".strip()
                    if balance.avg_buy_price > 0
                    else "-",
                    f"{format_amount(price)}" if price is not None else "-",
                    f"{format_amount(valuation, 0)}" if valuation is not None else "-",
                ]
            )

        grand_total += subtotal
        title = f"{snap.pocket.name} ({'메인포켓' if snap.pocket.is_main else '서브포켓'})"
        header = colorize(f"[{title}]", BOLD, True) + colorize(f"  uuid={snap.pocket.uuid}", DIM, True)

        table = render_table(
            ["자산", "수량", "잠김", "매수평균가", "현재가(KRW)", "평가금액(KRW)"],
            rows,
            ["left", "right", "right", "right", "right", "right"],
        )
        footer = colorize(f"  소계 {subtotal:,.0f} KRW", CYAN, True)
        if priced_count < len(balances):
            footer += colorize("  (시세 미확인 자산 제외)", DIM, True)
        blocks.append(f"{header}\n{table}\n{footer}")

    blocks.append(colorize(f"합계 {grand_total:,.0f} KRW", BOLD + CYAN, True))
    return "\n\n".join(blocks)


def render_plans(plans: list[TransferPlan]) -> str:
    rows = []
    for index, plan in enumerate(plans, start=1):
        rows.append(
            [
                str(index),
                plan.from_pocket.name,
                "→",
                plan.to_pocket.name,
                plan.currency,
                format_amount(plan.amount),
                format_amount(plan.available),
                "전량" if plan.is_full else "일부",
            ]
        )
    return render_table(
        ["#", "출발", "", "도착", "자산", "이전 수량", "가용 잔고", "구분"],
        rows,
        ["right", "left", "left", "left", "left", "right", "right", "left"],
    )


def render_transfers(
    transfers: list[Transfer],
    pockets: list[Pocket],
    names: dict[str, str] | None = None,
) -> str:
    lookup = names or {pocket.uuid: pocket.name for pocket in pockets}
    rows = []
    for transfer in transfers:
        color = STATE_COLORS.get(transfer.state, "")
        rows.append(
            [
                transfer.created_at,
                lookup.get(transfer.from_uuid, transfer.from_uuid[:8]),
                "→",
                lookup.get(transfer.to_uuid, transfer.to_uuid[:8]),
                transfer.currency,
                format_amount(transfer.amount),
                colorize(transfer.state, color) if color else transfer.state,
                transfer.uuid[:8],
            ]
        )
    return render_table(
        ["생성 시각", "출발", "", "도착", "자산", "수량", "상태", "요청 UUID"],
        rows,
        ["left", "left", "left", "left", "left", "right", "left", "left"],
    )


def render_transfers_result(results: list[Transfer], plans: list[TransferPlan]) -> str:
    rows = []
    for plan, result in zip(plans, results):
        color = STATE_COLORS.get(result.state, BLUE)
        rows.append(
            [
                f"{plan.from_pocket.name} → {plan.to_pocket.name}",
                plan.currency,
                format_amount(plan.amount),
                colorize(result.state, color),
                result.uuid,
                result.identifier or "-",
            ]
        )
    return render_table(
        ["이전", "자산", "수량", "상태", "요청 UUID", "identifier"],
        rows,
        ["left", "left", "right", "left", "left", "left"],
    )
