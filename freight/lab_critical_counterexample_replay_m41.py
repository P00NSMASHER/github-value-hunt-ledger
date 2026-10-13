"""RETALLY Lab 14 / M41: executable critical-counterexample *analog* replay.

Replays four critical original-register failure classes against the CURRENT
freight.lab_assurance verifier using isolated, fictional SQLite and fixed
TEST-ONLY HMAC signers. This is NOT a historical baseline reproduction,
not a real carrier/bank verification, and does NOT close original findings.
"""
from __future__ import annotations

from datetime import date
from hashlib import sha256
from html import escape
import argparse
import json
from pathlib import Path
import sqlite3
import tempfile

from freight.lab_assurance import AssuranceRejected, digest, verify_settlement
from freight.lab_historical_disposition_m40 import _book
from freight.test_lab_assurance import (
    BUYER, BU, CLAIM, SRC, assertions_and_fees, populate, stamp, verifier,
)

SCOPE = "RETALLY_LAB14_M41_CRITICAL_SYNTHETIC_COUNTEREXAMPLE_ANALOG_REPLAY"
FINDING_IDS = ("LAB-P0-01", "LAB-P0-02", "LAB-P0-03", "D-01")
EXPECTED_REJECTIONS = {
    "LAB-P0-01": "RECEIPT_OVER_ALLOCATED",
    "LAB-P0-02": "SOURCE_OWNER_BINDING_MISMATCH",
    "LAB-P0-03": "MISSING_CREDIT_RECEIPT",
    "D-01": "DUPLICATE_ECONOMIC_RECOVERY",
}
ATTACKS = {
    "LAB-P0-01": "SQL_ALLOCATION_BALANCE_INFLATION_CURRENT_VERIFIER_ANALOG",
    "LAB-P0-02": "SQL_INVOICE_CLAIM_TOTAL_REWRITE_CURRENT_VERIFIER_ANALOG",
    "LAB-P0-03": "SQL_PHANTOM_CARRIER_RECEIPT_NO_PROVIDER_ATTESTATION_ANALOG",
    "D-01": "SQL_DUPLICATE_ISSUE_WITH_SECOND_BUYER_SIGNED_CLAIM_ANALOG",
}
BASELINE = {
    "recovered_cents": 500,
    "earned_fee_cents": 100,
    "collected_fee_cents": 100,
    "fee_refund_due_cents": 0,
}


def _observe(db: Path, proofs: list, fees: list):
    return verify_settlement(
        db, buyer_id=BUYER, business_unit=BU,
        assertions=proofs, fee_events=fees, verifier=verifier()
    )


def _inject(db: Path, finding_id: str, proofs: list) -> list:
    """Touch an isolated test-only database; never reach a persistent store."""
    if finding_id not in FINDING_IDS:
        raise ValueError("M41_UNREGISTERED_CRITICAL_COUNTEREXAMPLE")
    with sqlite3.connect(db) as con:
        if finding_id == "LAB-P0-01":
            con.execute(
                "UPDATE allocations SET amount_cents=10000 "
                "WHERE allocation_id='allocation-400'"
            )
        elif finding_id == "LAB-P0-02":
            con.execute(
                "UPDATE recovery_claims SET amount_cents=999999 "
                "WHERE claim_id='case-1'"
            )
        elif finding_id == "LAB-P0-03":
            con.execute(
                "INSERT INTO settlement_events VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    BUYER, BU, "phantom-credit-9m", "INV-100",
                    "SIM-CARRIER", "SIM-BUYER", "USD", 9_000_000,
                    "2026-11-09T12:00:00Z",
                    sha256(b"m41-test-only-phantom-no-provider").hexdigest(),
                    "EXTERNAL",
                ),
            )
        elif finding_id == "D-01":
            # Even a *syntactically signed* second record cannot make the
            # same economic issue eligible for two different case IDs.
            con.execute(
                "INSERT INTO recovery_claims VALUES (?,?,?,?,?,?,?,?,?,?,?)",
                (
                    BUYER, BU, "case-2", "INV-100",
                    "SIM-CARRIER", "SIM-BUYER", "USD", 1000,
                    CLAIM, SRC, 0,
                ),
            )
            proofs = [
                *proofs,
                stamp(
                    "SOURCE_OWNER", "m41-second-owner-proof",
                    "buyer-signer", "2026-10-01T10:00:00Z",
                    claim_id="case-2", reference="INV-100",
                    payer_id="SIM-CARRIER", payee_id="SIM-BUYER",
                    currency="USD", amount_cents=1000,
                    issued_at=CLAIM, source_hash=SRC,
                    economic_issue_id="accessorial-100",
                ),
            ]
    return proofs


def replay_one(finding_id: str) -> dict:
    """Require positive control AND one precise signed-source denial.

    A different failure code, no failure, or unexpectedly failing positive
    control is NOT an accepted hardening result. No original audit baseline.
    """
    if type(finding_id) is not str or finding_id not in FINDING_IDS:
        raise ValueError("M41_UNKNOWN_OR_UNCONTROLLED_HISTORICAL_FINDING")
    with tempfile.TemporaryDirectory(prefix="retally-m41-fake-replay-") as tmp:
        db = Path(tmp) / "fictional-settlement.sqlite3"
        populate(db)
        proofs, fees = assertions_and_fees()
        good = _observe(db, proofs, fees)
        if (good.status != "PASS_SYNTHETIC_ONLY"
            or good.scope != "SIGNED_SYNTHETIC_EVIDENCE_ONLY"
            or good.verified_claims != 1
            or good.verified_receipts != 2
            or good.currency_totals.get("USD") is None
            or any(good.currency_totals["USD"].get(k) != v
                   for k, v in BASELINE.items())):
            raise ValueError("M41_POSITIVE_SYNTHETIC_SETTLEMENT_CHAIN_NOT_VERIFIED")
        before_hash = sha256(db.read_bytes()).hexdigest()
        changed_proofs = _inject(db, finding_id, proofs)
        after_hash = sha256(db.read_bytes()).hexdigest()
        if before_hash == after_hash:
            raise ValueError("M41_INJECTION_DID_NOT_MUTATE_ISOLATED_SQLITE")
        try:
            _observe(db, changed_proofs, fees)
        except AssuranceRejected as err:
            if err.code != EXPECTED_REJECTIONS[finding_id]:
                raise ValueError(
                    "M41_WRONG_DENIAL_MECHANISM_FOR_HISTORICAL_ANALOG:"
                    + finding_id + ":" + err.code
                ) from err
            observed = err.code
        else:
            raise ValueError("M41_CRITICAL_CURRENT_IMPLEMENTATION_ACCEPTED_FORGED_EVIDENCE:" + finding_id)
        return {
            "historical_finding_id": finding_id,
            "test_only_attack": ATTACKS[finding_id],
            "positive_control_result": "PASS_SYNTHETIC_ONLY",
            "positive_control_recovered_cents": BASELINE["recovered_cents"],
            "positive_control_earned_fee_cents": BASELINE["earned_fee_cents"],
            "attack_sqlite_differed_from_positive_control": True,
            "expected_independent_verifier_denial": EXPECTED_REJECTIONS[finding_id],
            "observed_denial": observed,
            "current_source_negative_protection": "REJECTED_IN_ISOLATED_SYNTHETIC_PATH",
            "original_historical_bug_reproduced_from_pinned_old_revision": False,
            "original_defect_verified_repaired": False,
            "independent_real_provider_or_buyer_evidence": False,
            "historical_disposition": "OPEN_UNVERIFIED",
            "test_only_before_database_sha256": before_hash,
            "test_only_after_database_sha256": after_hash,
        }


def run_campaign(*, as_of: date) -> dict:
    if type(as_of) is not date or as_of < date(2026, 10, 13):
        raise ValueError("M41_INVALID_RESEARCH_AS_OF_DATE")
    book = _book()
    known = {row["id"]: row for row in book["entries"][:26]}
    if (book["historical_open_findings"] != 26
        or any(id_ not in known or known[id_]["severity"] != "CRITICAL"
               or known[id_]["remediation"] != "OPEN_UNVERIFIED"
               for id_ in FINDING_IDS)):
        raise ValueError("M41_CRITICAL_HISTORICAL_REGISTER_RELABELED")
    results = [replay_one(fid) for fid in FINDING_IDS]
    if (len(results) != 4
        or {r["historical_finding_id"] for r in results} != set(FINDING_IDS)
        or any(r["observed_denial"] != EXPECTED_REJECTIONS[r["historical_finding_id"]]
               or r["original_defect_verified_repaired"] is not False
               for r in results)):
        raise ValueError("M41_CRITICAL_REPLAY_SET_UNTRUSTWORTHY")
    body = {
        "schema_version": 1,
        "scope": SCOPE,
        "as_of": as_of.isoformat(),
        "original_lab_number": 14,
        "new_lab_created": False,
        "current_source_paths_attacked": 4,
        "current_source_guards_rejected_attack": 4,
        "historical_original_defects_open": 26,
        "historical_original_defects_closed": 0,
        "original_pinned_vulnerable_revisions_replayed": 0,
        "independent_historical_fix_signoffs": 0,
        "source_fixture_type": "TEST_ONLY_HMAC_KEYS_FUTURE_DATED_SYNTHETIC_EVENTS",
        "external_customer_or_carrier_authority_established": False,
        "production_customer_settlement_data_read": False,
        "actual_recovered_customer_cash_usd": None,
        "external_empirical_commercial_claims_approved": 0,
        "independent_customer_pilot_controls_unmet": 18,
        "no_live_external_effects_or_schedule_changes": True,
        "original_register_git_blob_sha1": "8a97b74432b82b34468bbb57cbc14d869258b77c",
        "cases": results,
        "caveat": (
            "Four critical historical issue classes are tested as analogous "
            "attacks against the CURRENT isolated verifier, not reproduced "
            "against their original vulnerable git baselines. Positive "
            "controls and typed denials demonstrate selected current-code "
            "behavior only. Fictional receipts and HMAC test signers cannot "
            "authenticate a buyer, carrier, bank, collected cash or customer "
            "pilot, and may not close any of the 26 original defects. "
            "Twenty-six remain OPEN_UNVERIFIED, 18 required pilot approvals "
            "remain unmet and external publication is not authorized."
        ),
    }
    body["receipt_sha256"] = digest(body)
    return body


def render_html(report: dict) -> str:
    cards = "".join(
        "<article><h2>" + escape(x["historical_finding_id"]) +
        "</h2><p><strong>Current negative probe rejected: " +
        escape(x["observed_denial"]) +
        "</strong></p><p>Original historical defect: OPEN_UNVERIFIED.</p>"
        "<p>No historic baseline replay or real customer evidence.</p></article>"
        for x in report["cases"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width, initial-scale=1">'
        '<title>RETALLY | Four critical synthetic negative proofs</title>'
        '<style>body{font:15px/1.6 system-ui;color:#203327;'
        'background:#f4f7f3;max-width:960px;margin:auto;padding:24px}'
        'article{background:white;padding:16px;margin:16px 0;'
        'border:1px solid #d5e2d5;border-radius:12px}</style></head><body>'
        '<small>RETALLY / LAB 14 / M41 / RESEARCH-ONLY</small>'
        '<h1>Four executable critical-case controls</h1>'
        '<p>4/4 modern-path fictional attacks rejected by current verifier. '
        '0 historical bugs independently closed; 26 remain open. '
        'No live bank, carrier, buyer or public-performance proof.</p>' +
        cards +
        '<small>' + escape(report["caveat"]) + '</small></body></html>'
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Offline critical analog regression")
    ap.add_argument("--as-of-date", type=date.fromisoformat,
                    default=date.today())
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    report = run_campaign(as_of=args.as_of_date)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "critical_counterexample_replay.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "critical_counterexample_replay.html").write_text(
        render_html(report), encoding="utf-8"
    )
    print(json.dumps({
        "current_code_denials_verified": 4,
        "original_defects_closed": 0,
        "pilot_human_gates_unmet": 18,
        "receipt_sha256": report["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
