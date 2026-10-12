"""포켓 관리 도메인 로직."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from decimal import Decimal

from .client import UpbitClient
from .errors import TransferValidationError
from .models import (
    Balance,
    Pocket,
    PriceBook,
    Transfer,
    TransferRequest,
    format_amount,
)
from .pricing import PriceService

IDENTIFIER_PREFIX = "pocketmgr"


@dataclass
class PocketSnapshot:
    pocket: Pocket
    balances: list[Balance]


@dataclass
class TransferPlan:
    from_pocket: Pocket
    to_pocket: Pocket
    currency: str
    amount: Decimal
    available: Decimal

    @property
    def is_full(self) -> bool:
        return self.amount >= self.available


def new_identifier() -> str:
    """업비트가 허용하는 규격(1~64자, 영숫자/_/./-)의 고유 식별자."""
    stamp = time.strftime("%Y%m%d%H%M%S")
    return f"{IDENTIFIER_PREFIX}-{stamp}-{uuid.uuid4().hex[:8]}"


class PocketService:
    def __init__(self, client: UpbitClient):
        self._client = client
        self._prices = PriceService(client)

    # --------------------------------------------------------------- 조회

    def pockets(self) -> list[Pocket]:
        """메인포켓이 먼저 오는 순서로 포켓 목록을 반환한다."""
        pockets = self._client.list_pockets()
        return sorted(pockets, key=lambda p: (not p.is_main, p.name))

    def find_pocket(self, target: str) -> Pocket:
        """이름, UUID, UUID 앞 8자리로 포켓을 찾는다."""
        pockets = self.pockets()
        normalized = target.strip().lower()

        for pocket in pockets:
            if pocket.uuid.lower() == normalized:
                return pocket
        for pocket in pockets:
            if pocket.name.lower() == normalized:
                return pocket
        for pocket in pockets:
            if pocket.uuid.lower().startswith(normalized):
                return pocket

        available = ", ".join(f"{p.name}({p.short_uuid})" for p in pockets)
        raise TransferValidationError(f"'{target}' 포켓을 찾을 수 없습니다. 사용 가능한 포켓: {available}")

    def balances_of(self, pocket: Pocket) -> list[Balance]:
        if pocket.is_main:
            return self._client.get_main_pocket_balances()
        return self._client.get_sub_pocket_balances(pocket.uuid)

    def snapshot(self) -> list[PocketSnapshot]:
        return [PocketSnapshot(pocket, self.balances_of(pocket)) for pocket in self.pockets()]

    def market_names(self) -> dict[str, str]:
        """통화 코드 → 한글 종목명."""
        return {market.base: market.korean_name for market in self._prices.markets()}

    def price_book_for(self, snapshots: list[PocketSnapshot]) -> PriceBook:
        currencies = {b.currency for snap in snapshots for b in snap.balances}
        currencies.update({"BTC"})
        return self._prices.price_book(currencies)

    def transfers(self, **kwargs) -> list[Transfer]:
        return self._client.list_universal_transfers(**kwargs)

    # --------------------------------------------------------- 이전 계획

    def balance_of(self, snapshot: PocketSnapshot, currency: str) -> Balance | None:
        for balance in snapshot.balances:
            if balance.currency == currency:
                return balance
        return None

    def build_plan(
        self,
        from_pocket: Pocket,
        to_pocket: Pocket,
        currency: str,
        amount: Decimal | None,
        snapshots: list[PocketSnapshot] | None = None,
    ) -> TransferPlan:
        """amount가 None이면 해당 통화의 가용 잔액 전량을 이전한다."""
        if from_pocket.uuid == to_pocket.uuid:
            raise TransferValidationError("출발 포켓과 도착 포켓이 같습니다. (from != to)")

        snapshots = snapshots if snapshots is not None else self.snapshot()
        source = next((s for s in snapshots if s.pocket.uuid == from_pocket.uuid), None)
        if source is None:
            raise TransferValidationError(f"출발 포켓 '{from_pocket.name}' 잔고를 확인할 수 없습니다.")

        balance = self.balance_of(source, currency)
        if balance is None or balance.balance <= 0:
            raise TransferValidationError(f"{from_pocket.name} 포켓에 보유한 {currency} 자산이 없습니다.")

        available = balance.available
        if available <= 0:
            raise TransferValidationError(
                f"{from_pocket.name}의 {currency} 잔고 전부가 잠겨 있습니다. (잠김 {format_amount(balance.locked)})"
            )

        requested = available if amount is None else amount
        if requested <= 0:
            raise TransferValidationError("이전 수량은 0보다 커야 합니다.")
        if requested > available:
            raise TransferValidationError(
                f"이전 수량({format_amount(requested)})이 가용 잔고({format_amount(available)})를 초과합니다."
            )

        return TransferPlan(
            from_pocket=from_pocket,
            to_pocket=to_pocket,
            currency=currency,
            amount=requested,
            available=available,
        )

    def build_plan_for_all(
        self,
        from_pocket: Pocket,
        to_pocket: Pocket,
        snapshots: list[PocketSnapshot] | None = None,
        include_locked: bool = False,
    ) -> list[TransferPlan]:
        """출발 포켓의 가용 자산 전체를 이전하는 계획을 만든다."""
        if from_pocket.uuid == to_pocket.uuid:
            raise TransferValidationError("출발 포켓과 도착 포켓이 같습니다. (from != to)")

        snapshots = snapshots if snapshots is not None else self.snapshot()
        source = next((s for s in snapshots if s.pocket.uuid == from_pocket.uuid), None)
        if source is None:
            raise TransferValidationError(f"출발 포켓 '{from_pocket.name}' 잔고를 확인할 수 없습니다.")

        plans: list[TransferPlan] = []
        for balance in source.balances:
            amount = balance.balance if include_locked else balance.available
            if amount <= 0:
                continue
            plans.append(
                TransferPlan(
                    from_pocket=from_pocket,
                    to_pocket=to_pocket,
                    currency=balance.currency,
                    amount=amount,
                    available=balance.available,
                )
            )
        if not plans:
            raise TransferValidationError(f"{from_pocket.name} 포켓에 이전할 수 있는 자산이 없습니다.")
        return plans

    # ------------------------------------------------------------- 실행

    def execute(self, plans: list[TransferPlan], identifier_prefix: str | None = None) -> list[Transfer]:
        results: list[Transfer] = []
        for index, plan in enumerate(plans, start=1):
            identifier = new_identifier()
            if identifier_prefix:
                identifier = f"{identifier_prefix}-{index}"
            request = TransferRequest(
                from_uuid=plan.from_pocket.uuid,
                to_uuid=plan.to_pocket.uuid,
                currency=plan.currency,
                amount=plan.amount,
                identifier=identifier,
            )
            results.append(self._client.universal_transfer(request))
        return results
