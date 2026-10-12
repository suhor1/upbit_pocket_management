"""명령줄 인터페이스."""

from __future__ import annotations

import argparse
import sys
from decimal import Decimal, InvalidOperation

from .client import UpbitClient
from .config import Settings
from .display import BLUE, BOLD, CYAN, DIM, GREEN, RED, YELLOW, colorize, render_table
from .errors import TransferAborted, TransferValidationError, UpbitPocketError
from .models import Pocket
from .service import PocketService, PocketSnapshot, TransferPlan
from .views import (
    render_plans,
    render_pocket_list,
    render_snapshot,
    render_transfers,
    render_transfers_result,
)


# --------------------------------------------------------------- 입력 헬퍼


def ask(prompt: str) -> str:
    try:
        return input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        print()
        raise TransferAborted("입력이 취소되었습니다.")


def confirm(prompt: str, assume_yes: bool) -> bool:
    if assume_yes:
        return True
    answer = ask(f"{prompt} [y/N] ").lower()
    return answer in {"y", "yes"}


def choose_pocket(
    service: PocketService,
    title: str,
    exclude: Pocket | None = None,
    options: list[Pocket] | None = None,
) -> Pocket:
    pockets = options if options is not None else service.pockets()
    candidates = [p for p in pockets if exclude is None or p.uuid != exclude.uuid]

    if not candidates:
        raise TransferValidationError("선택할 수 있는 포켓이 없습니다.")

    print()
    print(colorize(f"{title}", BOLD))
    for index, pocket in enumerate(candidates, start=1):
        kind = "메인포켓" if pocket.is_main else "서브포켓"
        print(f"  {colorize(str(index), CYAN)}) {pocket.name} {colorize(f'({kind})', DIM)}")

    while True:
        raw = ask(f"  포켓 번호 입력: ")
        if not raw.isdigit() or not 1 <= int(raw) <= len(candidates):
            print(colorize("  올바른 번호를 입력해주세요.", RED))
            continue
        return candidates[int(raw) - 1]


def choose_currency(snapshot: PocketSnapshot) -> str:
    balances = [b for b in snapshot.balances if b.balance > 0]
    if not balances:
        raise TransferValidationError(f"{snapshot.pocket.name} 포켓에 보유한 자산이 없습니다.")

    print()
    print(colorize(f"{snapshot.pocket.name} 보유 자산", BOLD))
    for index, balance in enumerate(balances, start=1):
        print(f"  {colorize(str(index), CYAN)}) {balance.currency:<8} {balance.balance}")

    while True:
        raw = ask("  자산 번호 또는 코드 입력: ")
        if not raw:
            raise TransferAborted("취소되었습니다.")
        if raw.isdigit() and 1 <= int(raw) <= len(balances):
            return balances[int(raw) - 1].currency
        match = next((b for b in balances if b.currency.upper() == raw.upper()), None)
        if match:
            return match.currency
        print(colorize("  해당 자산을 찾을 수 없습니다.", RED))


def parse_amount(raw: str) -> Decimal | None:
    """'all'/'전체'/빈 값은 None(전량)으로 해석한다."""
    if not raw or raw.lower() in {"all", "전체", "전부", "*"}:
        return None
    try:
        return Decimal(raw.replace(",", ""))
    except InvalidOperation as exc:
        raise TransferValidationError(f"'{raw}'은(는) 올바른 수량이 아닙니다.") from exc


# ------------------------------------------------------------------ 명령


def cmd_pockets(service: PocketService, args: argparse.Namespace) -> int:
    print(render_pocket_list(service.pockets()))
    return 0


def cmd_status(service: PocketService, args: argparse.Namespace) -> int:
    snapshots = service.snapshot()
    prices = service.price_book_for(snapshots)
    market_names = service.market_names()
    print()
    print(render_snapshot(snapshots, prices, market_names))
    return 0


def _run_plans(
    service: PocketService,
    plans: list[TransferPlan],
    execute: bool,
    assume_yes: bool,
) -> int:
    if not plans:
        raise TransferValidationError("이전할 자산이 없습니다.")

    print()
    print(colorize("자산 이전 계획", BOLD))
    print(render_plans(plans))

    if not execute:
        print()
        print(colorize("[드라이런] 실제 이전 요청을 보내지 않았습니다.", YELLOW))
        print(colorize("실제로 실행하려면 --execute 옵션을 사용하세요.", DIM))
        return 0

    print()
    if not confirm("위 계획대로 이전을 실행할까요?", assume_yes):
        raise TransferAborted("사용자가 실행을 취소했습니다.")

    results = service.execute(plans)
    print()
    print(render_transfers_result(results, plans))

    failed = [r for r in results if r.state == "failed"]
    if failed:
        print(colorize(f"\n{len(failed)}건이 실패했습니다. `history` 명령으로 상태를 확인하세요.", RED))
        return 1
    print(colorize("\n모든 이전 요청이 접수되었습니다. 최종 상태는 `history` 명령으로 확인하세요.", GREEN))
    return 0


def cmd_move(service: PocketService, args: argparse.Namespace) -> int:
    snapshots = service.snapshot()
    snapshot_by_uuid = {snap.pocket.uuid: snap for snap in snapshots}

    source = choose_pocket(service, "출발 포켓 선택", options=args_pockets(snapshots))
    destination = choose_pocket(
        service, "도착 포켓 선택", exclude=source, options=args_pockets(snapshots)
    )

    source_snapshot = snapshot_by_uuid[source.uuid]
    currency = choose_currency(source_snapshot)
    amount = parse_amount(ask("  이전 수량 (빈 입력 또는 'all' = 전량): "))

    plan = service.build_plan(source, destination, currency, amount, snapshots)
    return _run_plans(service, [plan], execute=args.execute, assume_yes=args.yes)


def cmd_move_all(service: PocketService, args: argparse.Namespace) -> int:
    snapshots = service.snapshot()

    source = choose_pocket(service, "출발 포켓 선택", options=args_pockets(snapshots))
    destination = choose_pocket(
        service, "도착 포켓 선택", exclude=source, options=args_pockets(snapshots)
    )

    scope = ask("  전체 자산 / 특정 자산만 (all/선택): ") or "all"
    if scope.lower() in {"all", "전체", "전부", "*"}:
        include_locked = False if args.yes else confirm("  잠긴(locked) 자산까지 포함할까요?", False)
        plans = service.build_plan_for_all(source, destination, snapshots, include_locked=include_locked)
    else:
        snapshot_by_uuid = {snap.pocket.uuid: snap for snap in snapshots}
        currency = choose_currency(snapshot_by_uuid[source.uuid])
        amount = parse_amount(ask("  이전 수량 (빈 입력 또는 'all' = 전량): "))
        plans = [service.build_plan(source, destination, currency, amount, snapshots)]

    return _run_plans(service, plans, execute=args.execute, assume_yes=args.yes)


def cmd_history(service: PocketService, args: argparse.Namespace) -> int:
    pockets = service.pockets()

    kwargs = {"limit": args.limit, "order_by": "desc"}
    if args.currency:
        kwargs["currency"] = args.currency.upper()
    if args.states:
        kwargs["states"] = [state.strip() for state in args.states.split(",") if state.strip()]
    if getattr(args, "from_pocket", None):
        kwargs["from"] = service.find_pocket(args.from_pocket).uuid
    if getattr(args, "to_pocket", None):
        kwargs["to"] = service.find_pocket(args.to_pocket).uuid

    transfers = service.transfers(**kwargs)
    print()
    if not transfers:
        print(colorize("조회된 이전 내역이 없습니다.", DIM))
        return 0
    print(render_transfers(transfers, pockets))
    return 0


def cmd_check(service: PocketService, args: argparse.Namespace) -> int:
    checks: list[list[str]] = []

    pockets = service.pockets()
    checks.append(["포켓 관리", "GET /v1/pockets", "OK", f"포켓 {len(pockets)}개"])

    balances = service.balances_of(pockets[0])
    checks.append(["자산 조회", "GET /v1/accounts", "OK", f"자산 {len(balances)}종"])

    markets = service.market_names()
    checks.append(["시세 조회", "GET /v1/market/all", "OK", f"마켓 {len(markets)}개"])
    if len(pockets) > 1:
        sub_balances = service.balances_of(pockets[1])
        checks.append(
            ["서브포켓 잔고", f"GET /v1/pockets/assets?uuid={pockets[1].uuid[:8]}..", "OK", f"자산 {len(sub_balances)}종"]
        )

    print()
    print(colorize("연결 점검", BOLD))
    print(render_table(["기능", "엔드포인트", "결과", "상세"], checks))

    if len(pockets) < 2:
        print()
        print(colorize("서브포켓이 없습니다. 업비트 앱에서 서브포켓을 먼저 만들어주세요.", YELLOW))
    return 0


def args_pockets(snapshots: list[PocketSnapshot]) -> list[Pocket]:
    return [snap.pocket for snap in snapshots]


# ------------------------------------------------------------------ 진입점


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="upbit_pocket",
        description="업비트 메인포켓 / 서브포켓 자산 관리 도구",
    )
    parser.add_argument("--env-file", default=".env", help="API Key가 담긴 파일 경로 (기본: .env)")
    parser.add_argument("--execute", action="store_true", help="자산 이전을 실제 실행 (기본은 드라이런)")
    parser.add_argument("--yes", action="store_true", help="확인 prompts 생략")

    sub = parser.add_subparsers(dest="command")

    sub.add_parser("status", help="모든 포켓의 자산 현황 조회 (기본)").set_defaults(func=cmd_status)
    sub.add_parser("pockets", help="포켓 목록 조회").set_defaults(func=cmd_pockets)
    sub.add_parser("check", help="API 연결 및 권한 점검").set_defaults(func=cmd_check)
    sub.add_parser("move", help="특정 자산을 다른 포켓으로 이동").set_defaults(func=cmd_move)
    sub.add_parser("move-all", help="모든 자산을 다른 포켓으로 이동").set_defaults(func=cmd_move_all)

    history = sub.add_parser("history", help="포켓 자산 이전 내역 조회")
    history.add_argument("--limit", type=int, default=20)
    history.add_argument("--currency", help="자산 코드 필터 (예: BTC)")
    history.add_argument("--states", help="상태 필터, 쉼표 구분 (done,failed,processing,submitted)")
    history.add_argument("--from-pocket", dest="from_pocket", help="출발 포켓 이름 또는 UUID")
    history.add_argument("--to-pocket", dest="to_pocket", help="도착 포켓 이름 또는 UUID")
    history.set_defaults(func=cmd_history)

    return parser


def _setup_console() -> None:
    """출력을 파일/파이프로 리디렉션했을 때 한국어가 깨지지 않도록 UTF-8로 맞춘다.

    실제 콘솔(cp949 등)은 자체 인코딩을 그대로 사용한다.
    """
    for stream in (sys.stdout, sys.stderr):
        if stream is None or not hasattr(stream, "reconfigure"):
            continue
        try:
            if not stream.isatty():
                stream.reconfigure(encoding="utf-8")
        except (ValueError, OSError):
            pass


def main(argv: list[str] | None = None) -> int:
    _setup_console()
    parser = build_parser()
    args = parser.parse_args(argv)

    if not getattr(args, "command", None):
        args.command = "status"
        args.func = cmd_status

    try:
        settings = Settings.load(args.env_file)
        service = PocketService(UpbitClient(settings))
        return args.func(service, args)
    except TransferAborted as exc:
        print(colorize(f"\n{exc}", YELLOW))
        return 130
    except (TransferValidationError, UpbitPocketError) as exc:
        print(colorize(f"\n오류: {exc}", RED))
        return 1
    except KeyboardInterrupt:
        print(colorize("\n중단되었습니다.", YELLOW))
        return 130


if __name__ == "__main__":
    sys.exit(main())
