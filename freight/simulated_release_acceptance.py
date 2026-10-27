"""Release acceptance *simulation* with fictional rate, bank and adjudication.

No external signer, bank, rate owner, independent reviewer, or customer has
validated these inputs. This is a negative-control rehearsal showing that
plausible-looking source strings cannot promote customer/recovery release.
"""
from __future__ import annotations

from hashlib import sha256
import json

from freight.financial_integrity import (
    FinancialMovement, replay_financial_movements, financial_claim_gate,
)
from freight.rate_authority import AuthorityBook
from freight.rating_engine import rate_record
from freight.reliability_dashboard import acceptance_snapshot
from freight.sealed_real_accuracy import (
    ModelCall, TruthCall, PredictionSeal, TruthSeal, prediction_seal_hash,
    truth_seal_hash, score_sealed_freight,
)
from freight.test_phase0_recoveryos import ltl_authority, ltl_record

def _simulated_seals():
    model_time = "2026-10-18T12:00:00+00:00"
    truth_time = "2026-10-18T13:00:00+00:00"
    preds = (
        ModelCall("SIMULATED-CASE-001", "POSITIVE", 2700, "f"*64),
        ModelCall("SIMULATED-CASE-002", "NEGATIVE", 0, "f"*64),
        ModelCall("SIMULATED-CASE-003", "REVIEW", 0, "f"*64),
    )
    truths = (
        TruthCall("SIMULATED-CASE-001", "POSITIVE", 2700,
                  "a"*64,"b"*64,"c"*64,"d"*64,True),
        TruthCall("SIMULATED-CASE-002", "NEGATIVE", 0,
                  "a"*64,"b"*64,"c"*64,"d"*64,True),
        TruthCall("SIMULATED-CASE-003", "UNRESOLVED", 0,
                  "a"*64,None,None,None,False),
    )
    return (
        PredictionSeal("SIMULATED-OPERATOR", model_time, preds,
                       prediction_seal_hash("SIMULATED-OPERATOR", model_time, preds)),
        TruthSeal("SIMULATED-TRUTH-OWNER","SIMULATED-REVIEWER-1",
                  "SIMULATED-REVIEWER-2",truth_time, truths,
                  truth_seal_hash("SIMULATED-TRUTH-OWNER","SIMULATED-REVIEWER-1",
                                  "SIMULATED-REVIEWER-2",truth_time,truths)),
    )


def run_simulated_acceptance() -> dict:
    record=ltl_record()
    rating=rate_record(record, AuthorityBook((ltl_authority(),)))
    # Data that CLAIMS to be BANK_CLEARED is not independently authenticated
    # merely by a synthetic SHA256, provider label or a model-selected reviewer.
    fake_bank=FinancialMovement(
        "SIMULATED-PAYMENT-1","PAYMENT",18700,"2026-10-03",
        "b"*64,"BANK_CLEARED",True,None,record.record_hash)
    balance=replay_financial_movements(record,(fake_bank,))
    claim=financial_claim_gate(
        record,rating,balance,
        independent_adjudication_sha256="c"*64,
        human_release_approved=True)
    model,truth=_simulated_seals()
    toy=score_sealed_freight(
        model,truth,joint_unseal_at="2026-10-18T14:00:00+00:00",
        study_kind="SYNTHETIC_REHEARSAL")
    claimed_real=score_sealed_freight(
        model,truth,joint_unseal_at="2026-10-18T14:00:00+00:00",
        study_kind="REAL_EXTERNAL_REVIEW_PENDING")
    # Even if fabricated "reviewers", rights, and deployment are passed as
    # all True, the existing pilot gate cannot be self-authorized.
    state=acceptance_snapshot(
        invoices_extracted=110,invoices_exact=110,pinned_source_files=7,
        accounting_invoice_population=273,accounting_matched=273,
        accounting_cross_scope_errors=0,freight_labeled=0,
        freight_unknown=110,precision=None,
        rights_approved=True, production_approved=True)
    checks={
        "synthetic_invoice_rating_candidate_positive":
            rating.variance_cents==2700,
        "fabricated_bank_amount_not_independently_verified":
            balance.source_attested_net_cash_cents==18700
            and balance.verified_net_cash_cents==0,
        "fabricated_payment_forces_review":
            balance.status=="REVIEW_REQUIRED",
        "synthetic_adjudication_not_customer_approval":
            claim.validated_discrepancy_cents==0
            and claim.realized_recovery_cents==0,
        "synthetic_conditional_score_only":
            toy.precision==1.0 and toy.publication_claim_approved is False,
        "same_synthetic_cases_not_real_truth":
            claimed_real.precision is None
            and claimed_real.complete_independent_truth_count==0
            and claimed_real.source_claimed_complete_cases_unverified==2,
        "release_hold_survives_all_forged_boolean_approvals":
            state.release_status=="RELEASE_HOLD"
            and "EXISTING_FREIGHT_PILOT_ACCEPTANCE_REQUIRED" in state.blockers,
    }
    body={
        "kind":"SYNTHETIC_ONLY_NO_REAL_BANK_OR_RATE_OR_ADJUDICATION",
        "scenario_count":len(checks),
        "all_controls_pass":all(checks.values()),
        "control_results":checks,
        "simulated_invoice_billed_minor":record.billed_total_cents,
        "simulated_invoice_rated_variance_minor":rating.variance_cents,
        "source_attested_bank_minor":balance.source_attested_net_cash_cents,
        "externally_verified_bank_minor":balance.verified_net_cash_cents,
        "claimable_freight_recovery_minor":claim.validated_discrepancy_cents,
        "realized_freight_recovery_minor":claim.realized_recovery_cents,
        "simulation_conditional_precision":toy.precision,
        "external_real_freight_precision":claimed_real.precision,
        "original_real_cases_unknown":state.unresolved_freight_cases,
        "production_release_status":state.release_status,
        "true_external_approval_observed":False,
    }
    body["rehearsal_sha256"]=sha256(
        json.dumps(body,sort_keys=True,separators=(",",":")).encode()
    ).hexdigest()
    if not all(checks.values()):
        raise ValueError("synthetic refusal regression failed")
    return body
