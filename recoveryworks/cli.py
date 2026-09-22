"""Local operator CLI for RecoveryWorks.

Every command is local state manipulation. This CLI never sends a claim, appeal,
demand, dispute, email, or counterparty communication.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Sequence

from .io import execute_scan_payload
from .packets import build_client_portfolio_packet, build_recovery_packet, submission_ready
from .storage import load_ledger, save_ledger


def _add_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", "-o", type=Path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="recoveryworks")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="run a frozen Recovery Scan 360 payload")
    scan.add_argument("input", type=Path)
    _add_output(scan)
    scan.add_argument("--ledger-output", type=Path, help="persist the resulting proof/audit ledger locally")

    summary = sub.add_parser("summary", help="read a persisted ledger without mutating it")
    summary.add_argument("ledger", type=Path)
    _add_output(summary)

    packet = sub.add_parser("packet", help="render one recovery case packet")
    packet.add_argument("ledger", type=Path)
    packet.add_argument("finding_id")
    _add_output(packet)

    portfolio = sub.add_parser("portfolio", help="render one client-isolated portfolio packet")
    portfolio.add_argument("ledger", type=Path)
    portfolio.add_argument("client_id")
    _add_output(portfolio)

    approve = sub.add_parser("approve", help="record human reviewer approval locally")
    approve.add_argument("ledger", type=Path)
    approve.add_argument("finding_id")
    approve.add_argument("--reviewer", required=True)
    approve.add_argument("--note", required=True)

    authorize = sub.add_parser("authorize", help="record explicit customer authorization locally")
    authorize.add_argument("ledger", type=Path)
    authorize.add_argument("finding_id")
    authorize.add_argument("--authorization-id", required=True)

    claimed = sub.add_parser(
        "mark-claimed",
        help="record that an authorized claim was submitted elsewhere; performs no submission",
    )
    claimed.add_argument("ledger", type=Path)
    claimed.add_argument("finding_id")

    recovered = sub.add_parser("recover", help="record externally verified recovered cash")
    recovered.add_argument("ledger", type=Path)
    recovered.add_argument("finding_id")
    recovered.add_argument("--recovered-cents", type=int, required=True)
    recovered.add_argument("--fee-cents", type=int, default=0)

    reject = sub.add_parser("reject", help="record reviewer rejection locally")
    reject.add_argument("ledger", type=Path)
    reject.add_argument("finding_id")
    reject.add_argument("--reviewer", required=True)
    reject.add_argument("--note", required=True)

    return parser


def _emit(value: Any, output: Path | None = None) -> None:
    rendered = json.dumps(value, indent=2, sort_keys=True) + "\n"
    if output is None:
        print(rendered, end="")
    else:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(rendered, encoding="utf-8")


def _record_result(ledger, finding_id: str) -> dict[str, Any]:
    record = ledger.get(finding_id)
    packet = build_recovery_packet(record)
    return {
        "finding_id": finding_id,
        "case_state": record.case_state.value,
        "reviewer_approved": record.reviewer_approved,
        "authorization_id": record.authorization_id,
        "recovered_cents": record.recovered_cents,
        "fee_cents": record.fee_cents,
        "submission_ready": submission_ready(packet),
        "packet_hash": packet.packet_hash,
        "ledger_snapshot_hash": ledger.snapshot_hash,
        "audit_head": ledger.audit_head,
    }


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "scan":
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        result, ledger = execute_scan_payload(payload)
        if args.ledger_output:
            save_ledger(args.ledger_output, ledger)
            result = {**result, "ledger_path": str(args.ledger_output)}
        _emit(result, args.output)
        return 0

    ledger = load_ledger(args.ledger)

    if args.command == "summary":
        _emit({
            "rollup": ledger.rollup(),
            "ledger_snapshot_hash": ledger.snapshot_hash,
            "audit_head": ledger.audit_head,
            "audit_chain_valid": ledger.verify_event_chain(),
        }, args.output)
        return 0

    if args.command == "packet":
        packet = build_recovery_packet(ledger.get(args.finding_id))
        _emit({
            **packet.__dict__,
            "rule": dict(packet.rule) if packet.rule is not None else None,
            "evidence": [dict(item) for item in packet.evidence],
            "gates": dict(packet.gates),
            "submission_ready": submission_ready(packet),
        }, args.output)
        return 0

    if args.command == "portfolio":
        _emit(build_client_portfolio_packet(ledger, args.client_id), args.output)
        return 0

    if args.command == "approve":
        ledger.approve(args.finding_id, args.reviewer, args.note)
    elif args.command == "authorize":
        ledger.authorize(args.finding_id, args.authorization_id)
    elif args.command == "mark-claimed":
        ledger.mark_claimed(args.finding_id)
    elif args.command == "recover":
        ledger.mark_recovered(args.finding_id, args.recovered_cents, args.fee_cents)
    elif args.command == "reject":
        ledger.reject(args.finding_id, args.reviewer, args.note)
    else:
        raise ValueError("unsupported command")

    save_ledger(args.ledger, ledger)
    _emit(_record_result(ledger, args.finding_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
