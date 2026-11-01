"""Execute real Python rating, settlement, economics and reliability boundaries.

This integrates *actual* existing RecoveryOS Python domain implementations with
synthetic fixtures. Does not execute Floot hosted API nor externally sign money.
No carrier, customer, email, banking, or production side effects.
"""
from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Sequence
import sqlite3
import tempfile
from time import perf_counter_ns

from freight.lab_assurance import Evidence, EvidenceVerifier, FeeEvent, verify_settlement, AssuranceRejected, digest
from freight.lab_phase3_economics import ContingencyAssumptions, analyze_contingency


class IntegrationRejected(ValueError):
    pass


def _duration(start_ns: int) -> int:
    return max(0, (perf_counter_ns() - start_ns) // 1_000_000)


def _adversarial_replay(store, assertions, fee_events, verifier) -> bool:
    """Damage an *isolated copy*, verify independently sourced proof refuses it."""
    with tempfile.TemporaryDirectory(prefix="retally-isolated-restore-") as directory:
        dest = Path(directory) / "adversarial-copy.sqlite3"
        src = sqlite3.connect(store.path)
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
            dst.commit()
        finally:
            src.close()
            dst.close()
        conn = sqlite3.connect(dest)
        try:
            conn.execute("BEGIN IMMEDIATE")
            # This is a negative test on a temporary copy, not an instruction to
            # modify the real store or disable any live constraint.
            triggers = conn.execute("SELECT name FROM sqlite_master WHERE type='trigger'").fetchall()
            for (trigger,) in triggers:
                conn.execute('DROP TRIGGER "' + trigger.replace('"','""') + '"')
            event = conn.execute("SELECT buyer_id,business_unit,event_id FROM settlement_events LIMIT 1").fetchone()
            if event is None:
                raise IntegrationRejected("NO_SETTLEMENT_TO_CHALLENGE")
            conn.execute("UPDATE settlement_events SET amount_cents=amount_cents+1 WHERE buyer_id=? AND business_unit=? AND event_id=?", event)
            conn.commit()
        finally:
            conn.close()
        try:
            verify_settlement(dest, buyer_id=store.buyer_id, business_unit=store.business_unit,
                              assertions=assertions, fee_events=fee_events, verifier=verifier)
        except AssuranceRejected:
            return True
        raise IntegrationRejected("ALTERED_RECEIPT_WAS_ACCEPTED")


def execute_domain_chain(*, record, authority_book, store, assertions: Sequence[Evidence],
                         fee_events: Sequence[FeeEvent], verifier: EvidenceVerifier,
                         contingency: ContingencyAssumptions) -> dict:
    """Five genuinely executed domain checks; nine remain explicit blockers.

    The caller must supply a separate manifest and account authority. Research
    HMAC anchors in tests are *synthetic* and never certify real bank claims.
    """
    from freight.rating_engine import rate_record, RATED
    from freight.canonical_schema import verify_record
    steps = []
    start = perf_counter_ns()
    rated = rate_record(record, authority_book)
    if rated.status != RATED or rated.variance_cents is None or rated.variance_cents <= 0 or not rated.authority_verified:
        raise IntegrationRejected("RATE_NOT_SUPPORTED")
    steps.append({"lab":1, "status":"EXECUTED_REAL_PYTHON_DOMAIN", "evidence":rated.rating_hash, "elapsed_ms":_duration(start)})
    start = perf_counter_ns()
    verify_record(record)
    if (record.buyer_id, record.business_unit) != (store.buyer_id, store.business_unit):
        raise IntegrationRejected("RATING_AND_SETTLEMENT_TENANTS_DIFFER")
    source_assertions = [e for e in assertions if e.kind == "SOURCE_OWNER"]
    if len(source_assertions) != 1:
        raise IntegrationRejected("EXACTLY_ONE_SOURCE_OWNER_EXPECTED")
    signed_sources = verifier.check(assertions)
    signed_source = signed_sources.get(source_assertions[0].evidence_id)
    if not signed_source or signed_source.payload.get("source_hash") not in {x.sha256 for x in record.sources}:
        raise IntegrationRejected("INVOICE_SOURCE_MISMATCH")
    if signed_source.payload.get("reference") != record.invoice_id:
        raise IntegrationRejected("INVOICE_IDENTITY_MISMATCH")
    steps.append({"lab":4, "status":"EXECUTED_SYNTHETIC_SIGNED_SOURCE_MATCH", "evidence":record.record_hash, "elapsed_ms":_duration(start)})
    start = perf_counter_ns()
    proof = verify_settlement(store.path,buyer_id=store.buyer_id,business_unit=store.business_unit,
                              assertions=assertions,fee_events=fee_events,verifier=verifier)
    if len(proof.claim_balances)!=1:
        raise IntegrationRejected("SCOPED_TEST_EXPECTS_ONE_CLAIM")
    claim_id = proof.claim_balances[0]["claim_id"]
    claimed_amount = signed_source.payload.get("amount_cents")
    if type(claimed_amount) is not int or claimed_amount != rated.variance_cents:
        raise IntegrationRejected("RATING_DIFFERS_FROM_AUTHORIZED_CLAIM")
    if store.realized_cents(claim_id) != proof.claim_balances[0]["recovered_cents"]:
        raise IntegrationRejected("STORED_RECOVERY_DISAGREES_WITH_PROOF")
    if proof.scope != "SIGNED_SYNTHETIC_EVIDENCE_ONLY":
        raise IntegrationRejected("UNEXPECTED_ASSURANCE_SCOPE")
    steps.append({"lab":5, "status":"EXECUTED_REAL_SETTLEMENT_DOMAIN", "evidence":proof.receipt_hash, "elapsed_ms":_duration(start)})
    start=perf_counter_ns()
    money = analyze_contingency(contingency)
    if money.upfront_audit_revenue_cents != 0:
        raise IntegrationRejected("FREE_AUDIT_REVENUE_INVENTED")
    steps.append({"lab":8, "status":"EXECUTED_CONTINGENCY_MODEL", "evidence":money.receipt_sha256, "elapsed_ms":_duration(start)})
    start=perf_counter_ns()
    replay = verify_settlement(store.path,buyer_id=store.buyer_id,business_unit=store.business_unit,
                               assertions=assertions,fee_events=fee_events,verifier=verifier)
    if replay.receipt_hash != proof.receipt_hash:
        raise IntegrationRejected("REPLAY_IS_NOT_DETERMINISTIC")
    tamper_rejected = _adversarial_replay(store, assertions, fee_events, verifier)
    steps.append({"lab":11, "status":"EXECUTED_NEGATIVE_RESTORE_PROBE", "evidence":proof.receipt_hash, "elapsed_ms":_duration(start)})
    blocked = {2:"SIMULATED_PERSONA_NOT_REAL_CUSTOMER_AGENT",3:"BUYER_HELD_BLIND_TRUTH_NOT_AVAILABLE",
               6:"HOSTED_MULTI_TENANT_STAGING_NOT_CONNECTED",7:"NO_PERMISSIONED_REAL_SALES_FUNNEL",
               9:"PROCUREMENT_EVIDENCE_NOT_EXTERNALLY_ATTESTED",10:"PRIMARY_CARRIER_TARIFF_RESEARCH_NOT_PERSISTED",
               12:"NO_INDEPENDENT_REAL_FRAUD_LABELS",13:"NO_OBSERVED_COUNTERFACTUAL_SAVINGS",
               14:"INDEPENDENT_COMPETITOR_EVIDENCE_NOT_AVAILABLE"}
    for lab,reason in blocked.items():
        steps.append({"lab":lab,"status":"BLOCKED_EXTERNAL_OR_UNINTEGRATED", "reason":reason, "elapsed_ms":None})
    steps.sort(key=lambda row: row["lab"])
    body={"scope":"ISOLATED_ACTUAL_PYTHON_DOMAIN_WITH_SIMULATED_EVIDENCE",
          "financially_certified":False, "production_deployed":False,
          "executed_domain_labs":sorted(x["lab"] for x in steps if x["status"].startswith("EXECUTED")),
          "blocked_labs":sorted(blocked),
          "rating":{"invoice_id":record.invoice_id,"candidate_variance_cents":rated.variance_cents,
                    "rating_hash":rated.rating_hash},
          "settlement":{"currency":record.currency,"recovered_cents":proof.claim_balances[0]["recovered_cents"],
                        "fee_earned_cents":proof.claim_balances[0]["earned_fee_cents"],
                        "fee_collected_cents":proof.claim_balances[0]["collected_fee_cents"],
                        "assurance_receipt":proof.receipt_hash},
          "contingency":asdict(money),"tampered_temporary_restore_rejected":tamper_rejected,
          "lab_executions":steps}
    # Timing is measured runtime metadata: hashes intentionally exclude duration.
    stable = {**body,"lab_executions":[{k:v for k,v in row.items() if k!="elapsed_ms"} for row in steps]}
    body["receipt_sha256"]=digest(stable)
    return body
