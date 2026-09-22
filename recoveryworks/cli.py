"""Local operator CLI for RecoveryWorks.

Every command is local state manipulation. This CLI never sends a claim, appeal,
demand, dispute, email, or counterparty communication.
"""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Any, Sequence

from .ap_csv import execute_ap_csv_scan
from .fees import FeeAgreement, assess_fee
from .io import execute_scan_payload
from .models import Branch, EvidenceRef
from .review import build_review_queue, review_queue_summary
from .raw_scan import execute_raw_scan_payload
from .packets import build_client_portfolio_packet, build_recovery_packet, submission_ready
from .storage import load_ledger, save_ledger


def _ledger_key() -> str | None:
    value = os.environ.get("RECOVERYWORKS_LEDGER_HMAC_KEY")
    return value if value else None


def _require_signed_ledger() -> bool:
    return os.environ.get("RECOVERYWORKS_REQUIRE_SIGNED_LEDGER", "").strip().lower() in {
        "1", "true", "yes", "on",
    }


def _add_output(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", "-o", type=Path)


def _add_receipt_args(parser: argparse.ArgumentParser, default_kind: str) -> None:
    parser.add_argument("--evidence-id", required=True)
    parser.add_argument("--source-hash", required=True)
    parser.add_argument("--locator", required=True)
    parser.add_argument("--kind", dest="receipt_kind", default=default_kind)


def _receipt(args) -> EvidenceRef:
    return EvidenceRef(
        evidence_id=args.evidence_id,
        source_hash=args.source_hash,
        locator=args.locator,
        kind=args.receipt_kind,
        verified=True,
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="recoveryworks")
    sub = parser.add_subparsers(dest="command", required=True)

    scan = sub.add_parser("scan", help="run a normalized frozen Recovery Scan 360 payload")
    scan.add_argument("input", type=Path)
    _add_output(scan)
    scan.add_argument("--ledger-output", type=Path, help="persist the resulting proof/audit ledger locally")

    raw_scan = sub.add_parser(
        "raw-scan",
        help="run raw structured records through all applicable deterministic recovery engines",
    )
    raw_scan.add_argument("input", type=Path)
    _add_output(raw_scan)
    raw_scan.add_argument("--ledger-output", type=Path, help="persist the resulting proof/audit ledger locally")

    ap_csv = sub.add_parser(
        "ap-scan-csv",
        help="scan ordinary AP invoice/payment CSV exports",
    )
    ap_csv.add_argument("--scan-id", required=True)
    ap_csv.add_argument("--client-id", required=True)
    ap_csv.add_argument("--invoices", type=Path, required=True)
    ap_csv.add_argument("--payments", type=Path, required=True)
    ap_csv.add_argument(
        "--verify-invoices",
        action="store_true",
        help="operator attests invoice export source is verified",
    )
    ap_csv.add_argument(
        "--verify-payments",
        action="store_true",
        help="operator attests payment export source is verified",
    )
    ap_csv.add_argument(
        "--selection-rule",
        default="all rows in supplied AP invoice and payment exports",
    )
    _add_output(ap_csv)
    ap_csv.add_argument(
        "--ledger-output",
        type=Path,
        help="persist the resulting proof/audit ledger locally",
    )

    review = sub.add_parser("review-queue", help="render deterministic operator queues")
    review.add_argument("ledger", type=Path)
    review.add_argument("--client-id")
    review.add_argument("--branch", choices=tuple(branch.value for branch in Branch))
    review.add_argument("--currency")
    _add_output(review)

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
    _add_receipt_args(claimed, "claim_submission_receipt")

    recovered = sub.add_parser("recover", help="record externally verified recovered cash")
    recovered.add_argument("ledger", type=Path)
    recovered.add_argument("finding_id")
    recovered.add_argument("--recovered-cents", type=int, required=True)
    recovered.add_argument("--fee-cents", type=int, default=0)
    recovered.add_argument("--fee-agreement-id")
    recovered.add_argument("--fee-bps", type=int)
    recovered.add_argument("--fee-source-hash")
    recovered.add_argument("--fee-locator")
    recovered.add_argument(
        "--fee-rounding",
        choices=("HALF_UP", "FLOOR"),
        default="HALF_UP",
    )
    recovered.add_argument(
        "--settlement-total-cents",
        type=int,
        help="verified total settlement amount; defaults to this case allocation",
    )
    _add_receipt_args(recovered, "recovery_settlement")

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

    if args.command in {"scan", "raw-scan"}:
        payload = json.loads(args.input.read_text(encoding="utf-8"))
        if args.command == "raw-scan":
            result, ledger = execute_raw_scan_payload(payload)
        else:
            result, ledger = execute_scan_payload(payload)
        if args.ledger_output:
            key = _ledger_key()
            if _require_signed_ledger() and key is None:
                raise ValueError(
                    "RECOVERYWORKS_REQUIRE_SIGNED_LEDGER is enabled but "
                    "RECOVERYWORKS_LEDGER_HMAC_KEY is missing"
                )
            save_ledger(args.ledger_output, ledger, integrity_key=key)
            result = {
                **result,
                "ledger_path": str(args.ledger_output),
                "ledger_signed": key is not None,
            }
        _emit(result, args.output)
        return 0

    if args.command == "ap-scan-csv":
        result, ledger = execute_ap_csv_scan(
            scan_id=args.scan_id,
            client_id=args.client_id,
            invoices_path=args.invoices,
            payments_path=args.payments,
            invoices_verified=args.verify_invoices,
            payments_verified=args.verify_payments,
            selection_rule=args.selection_rule,
        )
        if args.ledger_output:
            key = _ledger_key()
            if _require_signed_ledger() and key is None:
                raise ValueError(
                    "RECOVERYWORKS_REQUIRE_SIGNED_LEDGER is enabled but "
                    "RECOVERYWORKS_LEDGER_HMAC_KEY is missing"
                )
            save_ledger(args.ledger_output, ledger, integrity_key=key)
            result = {
                **result,
                "ledger_path": str(args.ledger_output),
                "ledger_signed": key is not None,
            }
        _emit(result, args.output)
        return 0

    key = _ledger_key()
    ledger = load_ledger(
        args.ledger,
        integrity_key=key,
        require_signature=_require_signed_ledger(),
    )

    if args.command == "review-queue":
        branch_filter = Branch(args.branch) if args.branch else None
        items = build_review_queue(
            ledger,
            client_id=args.client_id,
            branch=branch_filter,
            currency=args.currency,
        )
        _emit({
            "summary": review_queue_summary(items),
            "items": [
                {
                    **item.__dict__,
                    "blockers": list(item.blockers),
                }
                for item in items
            ],
            "ledger_snapshot_hash": ledger.snapshot_hash,
            "audit_head": ledger.audit_head,
        }, args.output)
        return 0

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
        ledger.mark_claimed(args.finding_id, _receipt(args))
    elif args.command == "recover":
        fee_assessment = None
        if args.fee_cents > 0:
            required = {
                "--fee-agreement-id": args.fee_agreement_id,
                "--fee-bps": args.fee_bps,
                "--fee-source-hash": args.fee_source_hash,
                "--fee-locator": args.fee_locator,
            }
            missing = [name for name, value in required.items() if value is None]
            if missing:
                raise ValueError(
                    "positive --fee-cents requires " + ", ".join(missing)
                )
            finding = ledger.get(args.finding_id).finding
            agreement = FeeAgreement(
                agreement_id=args.fee_agreement_id,
                client_id=finding.client_id,
                fee_bps=args.fee_bps,
                branches=(finding.branch,),
                source_hash=args.fee_source_hash,
                locator=args.fee_locator,
                verified=True,
                currency=finding.currency,
                rounding=args.fee_rounding,
            )
            fee_assessment = assess_fee(
                finding,
                args.recovered_cents,
                agreement,
            )
            if fee_assessment.fee_cents != args.fee_cents:
                raise ValueError(
                    "--fee-cents does not match the verified fee agreement calculation"
                )
        ledger.mark_recovered(
            args.finding_id,
            args.recovered_cents,
            args.fee_cents,
            recovery_evidence=_receipt(args),
            settlement_total_cents=args.settlement_total_cents,
            fee_assessment=fee_assessment,
        )
    elif args.command == "reject":
        ledger.reject(args.finding_id, args.reviewer, args.note)
    else:
        raise ValueError("unsupported command")

    save_ledger(args.ledger, ledger, integrity_key=key)
    _emit(_record_result(ledger, args.finding_id))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
