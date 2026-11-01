"""Synthetic rehearsal for every currently blocked RETALLY launch gate.

This exercises decisions that normally require real people, signatures,
customer authority, providers, or real-world events. It creates no such
authority. All identities and evidence are fictional; no external effect is
permitted, and the canonical real-gate statuses must remain BLOCKED.
"""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
from pathlib import Path

from freight.commercial.first_customer_gate import DEFAULT
from freight.commercial.historical_first_customer_rehearsal import run_first_customer_rehearsal


EXPECTED_BLOCKED = (
    "R22", "R23", "R24", "R25", "R26", "R27", "R28", "R29",
    "R31", "R32", "R33", "R34", "R35", "R37",
)
FIXED_AT = "2026-10-15T14:30:00Z"
SIMULATED_PILOT_STAGES = (
    ("discovery", "Public discovery and qualification"),
    ("contract", "Fictional contracting and signature"),
    ("confidential_intake", "Fictional confidential-record intake"),
    ("audit", "Synthetic audit and independent review"),
    ("claim", "Fictional customer-authorized carrier action"),
    ("recovery", "Synthetic posted recovery and reversal"),
    ("fee", "Nonbillable fee calculation and invoice rehearsal"),
    ("closure", "Synthetic access revocation, retention and deletion"),
)


def _hash(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    ).encode("utf-8")).hexdigest()


def _receipt(gate_id: str, evidence: dict, actors: list[dict]) -> dict:
    body = {
        "gate_id": gate_id,
        "simulation_outcome": "PASS",
        "real_gate_status": "BLOCKED",
        "simulated_at": FIXED_AT,
        "simulated_actors": actors,
        "simulated_evidence": evidence,
        "external_effect_performed": False,
        "customer_authorization_created": False,
        "evidence_can_satisfy_real_gate": False,
    }
    return {**body, "receipt_sha256": _hash(body)}


def _actors() -> dict[str, dict]:
    return {
        "owner": {"name": "Synthetic RETALLY Owner", "role": "business owner", "email": "owner@retally.example.invalid"},
        "counsel": {"name": "Synthetic Counsel", "role": "legal reviewer", "email": "counsel@law.example.invalid"},
        "broker": {"name": "Synthetic Broker", "role": "insurance adviser", "email": "broker@insurance.example.invalid"},
        "buyer": {"name": "Synthetic Buyer Signer", "role": "buyer authorized signer", "email": "signer@northstar.example.invalid"},
        "data_owner": {"name": "Synthetic Data Owner", "role": "buyer data owner", "email": "data.owner@northstar.example.invalid"},
        "reviewer": {"name": "Synthetic Independent Reviewer", "role": "financial review simulation", "email": "reviewer@independent.example.invalid"},
        "operator_a": {"name": "Synthetic Operator A", "role": "case preparer", "email": "operator.a@retally.example.invalid"},
        "operator_b": {"name": "Synthetic Operator B", "role": "independent approver", "email": "operator.b@retally.example.invalid"},
        "provider": {"name": "Synthetic Recovery Provider", "role": "provider simulator", "email": "events@provider.example.invalid"},
        "ap": {"name": "Synthetic AP Controller", "role": "buyer posting verifier", "email": "ap@northstar.example.invalid"},
    }


def run_remaining_gate_rehearsal(snapshot: dict) -> dict:
    """Exercise all blocked gates while proving that no real gate changes."""
    before = copy.deepcopy(snapshot)
    source_sha256 = _hash(snapshot)
    rows = {row["id"]: row for row in snapshot["mission_acceptance"]["requirements"]}
    blocked = tuple(row["id"] for row in snapshot["mission_acceptance"]["requirements"] if row["status"] == "BLOCKED")
    if blocked != EXPECTED_BLOCKED:
        raise ValueError(f"blocked gate set drifted: expected {EXPECTED_BLOCKED}, got {blocked}")
    declared_simulation_score = snapshot["mission_acceptance"].get("simulation_scorecard", {})
    expected_simulation_score = {
        "classification": "FICTIONAL_REHEARSAL_ONLY",
        "PASS": 37,
        "BLOCKED": 0,
        "FAIL": 0,
        "total": 37,
        "blockers_removed_in_simulation": 14,
        "blockers_removed_in_real_world": 0,
        "customer_pilot_decision": "FULL_GO_SIMULATED",
        "all_simulated_pilot_stages_available": True,
        "confidential_intake_authorized_in_simulation": True,
        "customer_service_authorized_in_simulation": True,
        "financial_operations_authorized_in_simulation": True,
        "real_customer_authorization_created": False,
        "real_financial_authorization_created": False,
        "evidence_ref": "freight/commercial/REMAINING_GATES_SYNTHETIC_REHEARSAL_20261015.md",
        "real_scorecard_unchanged": True,
    }
    if declared_simulation_score != expected_simulation_score:
        raise ValueError("canonical simulation scorecard drifted")

    core = run_first_customer_rehearsal()
    if core.get("synthetic") is not True:
        raise ValueError("underlying first-customer rehearsal must be synthetic")
    if core.get("carrier_action_external_action_performed") is not False:
        raise ValueError("underlying rehearsal performed an external carrier action")
    if core.get("commercial_value_claimed") is not False:
        raise ValueError("underlying rehearsal claimed commercial value")
    fee = core["contingency_fee_after_reversal"]
    if fee.get("billing_authorized") is not False:
        raise ValueError("underlying rehearsal authorized billing")

    a = _actors()
    engagement = core["contingency_engagement"]
    metrics = core["metrics"]
    root = core["persistent_reporting"]
    mock_provider_event = {
        "event_id": "evt_synthetic_recovery_posting_001",
        "tenant": "buyer-synthetic",
        "amount_cents": metrics["realized_cents"],
        "currency": "USD",
        "signature_kind": "TEST_FIXTURE_SHA256_NOT_PROVIDER_SIGNATURE",
    }
    mock_provider_event["test_signature"] = _hash({
        "test_key_label": "PUBLIC_TEST_KEY_NOT_A_SECRET",
        "event": mock_provider_event,
    })

    receipts = [
        _receipt("R22", {
            "fictional_contracting_party": "RETALLY RECOVERY DEMO LLC",
            "certificate_reference": "SYNTHETIC:PA:CERTIFICATE:001",
            "counsel_check": "PASS_SIMULATED",
            "legal_entity_created": False,
        }, [a["owner"], a["counsel"]]),
        _receipt("R23", {
            "agreement_reference": engagement["governing_agreement_reference"],
            "contingency_rate": engagement["contingency_rate"],
            "buyer_signature": "SYNTHETIC_SIGNATURE_BUYER",
            "retally_signature": "SYNTHETIC_SIGNATURE_RETALLY",
            "engagement_hash": engagement["engagement_hash"],
            "legally_executed": False,
        }, [a["buyer"], a["owner"], a["counsel"]]),
        _receipt("R24", {
            "fictional_binder_reference": "SYNTHETIC:BINDER:E_AND_O:001",
            "coverage_review": "PASS_SIMULATED",
            "policy_purchased": False,
            "coverage_exists": False,
        }, [a["broker"], a["owner"]]),
        _receipt("R25", {
            "reviewer_independence_questionnaire": "PASS_SIMULATED",
            "reviewed_case_count": core["buyer_review_case_count"],
            "reviewer_minutes": metrics["reviewer_minutes"],
            "qualified_human_appointed": False,
        }, [a["reviewer"]]),
        _receipt("R26", {
            "workspace": "SYNTHETIC:DRIVE:BUYER-SINGLE-TENANT",
            "mfa_challenges": {"allowed_operator": "PASS_SIMULATED", "denied_unknown_user": "PASS_SIMULATED"},
            "allowed_identities": [a["data_owner"]["email"], a["reviewer"]["email"]],
            "denied_identity": "unknown@outside.example.invalid",
            "real_workspace_accessed": False,
        }, [a["data_owner"], a["reviewer"]]),
        _receipt("R27", {
            "confidentiality_reference": engagement["confidentiality_terms_reference"],
            "data_use_reference": engagement["data_use_terms_reference"],
            "fictional_invoice_count": core["population_invoice_count"],
            "real_customer_files_received": False,
        }, [a["buyer"], a["data_owner"], a["owner"]]),
        _receipt("R28", {
            "mock_notification_id": "notify_synthetic_001",
            "recipient": "operator.a@retally.example.invalid",
            "provider_response": "DELIVERED_SIMULATED",
            "network_send_performed": False,
            "paid_service_used": False,
        }, [a["provider"], a["operator_a"]]),
        _receipt("R29", {
            "operator_separation": "PASS_SIMULATED",
            "operator_a_mfa": "PASS_SIMULATED",
            "operator_b_mfa": "PASS_SIMULATED",
            "same_identity_rejected": True,
            "cloudflare_seat_created": False,
            "operator_write_performed": False,
        }, [a["operator_a"], a["operator_b"]]),
        _receipt("R31", {
            "mock_provider_event": mock_provider_event,
            "tenant_match": "PASS_SIMULATED",
            "cross_tenant_attempt": "DENIED_SIMULATED",
            "real_provider_enrolled": False,
            "financial_event_posted": False,
        }, [a["provider"], a["operator_b"]]),
        _receipt("R32", {
            "posting_reference": fee["buyer_posting_evidence_reference"],
            "settlement_snapshot_hash": fee["settlement_snapshot_hash"],
            "gross_posted_cents": core["persistent_reporting"]["pre_return_realized_cents"],
            "reversal_cents": core["persistent_reporting"]["return_cents"],
            "net_posted_cents": metrics["realized_cents"],
            "actual_cash_or_credit_observed": False,
        }, [a["ap"], a["reviewer"]]),
        _receipt("R33", {
            "fictional_invoice_id": "INV-SYNTHETIC-001",
            "fee_record_hash": fee["record_hash"],
            "fee_eligible_recovered_cents": fee["fee_eligible_recovered_cents"],
            "recovery_fee_cents": fee["recovery_fee_cents"],
            "customer_net_recovery_cents": fee["customer_net_recovery_cents"],
            "duplicate_invoice_attempt": "REJECTED_SIMULATED",
            "billing_authorized": False,
            "invoice_issued": False,
        }, [a["ap"], a["reviewer"], a["owner"]]),
        _receipt("R34", {
            "fictional_closure_reference": "SYNTHETIC:CLOSURE:001",
            "final_report_hash": root["report_hash"],
            "access_revocation": "PASS_SIMULATED",
            "provider_deletion": "PASS_SIMULATED",
            "backup_expiry": "2026-11-15T14:30:00Z",
            "real_record_deleted": False,
        }, [a["data_owner"], a["reviewer"], a["operator_a"]]),
        _receipt("R35", {
            "candidate_commit": "SYNTHETIC_EXACT_HEAD",
            "review_decision": "APPROVE_SIMULATED",
            "rollback_rehearsal": "PASS_SIMULATED",
            "merge_performed": False,
            "deployment_performed": False,
        }, [a["operator_a"], a["operator_b"], a["owner"]]),
        _receipt("R37", {
            "fictional_hour_cap": 20,
            "fictional_economic_loss_cap_usd": "2500.00",
            "authorized_external_cash_spend_usd": "0.00",
            "stop_at_hours": 20,
            "stop_rule_rehearsal": "PASS_SIMULATED",
            "owner_approved_real_cap": False,
        }, [a["owner"], a["reviewer"]]),
    ]

    if snapshot != before or _hash(snapshot) != source_sha256:
        raise AssertionError("rehearsal mutated the canonical acceptance snapshot")
    body = {
        "schema_version": "remaining-gates-rehearsal.v1",
        "simulation_id": "retally-remaining-gates-synthetic-20261015",
        "synthetic": True,
        "outcome": "SIMULATION_PASS_REAL_GATES_UNCHANGED",
        "source_as_of": snapshot["as_of"],
        "source_sha256_before": source_sha256,
        "source_sha256_after": _hash(snapshot),
        "real_scorecard": copy.deepcopy(snapshot["mission_acceptance"]["scorecard"]),
        "simulation_scorecard": copy.deepcopy(declared_simulation_score),
        "simulation_stage_decisions": [{
            "stage": stage,
            "label": label,
            "decision": "GO_SIMULATED",
            "real_action_authorized": False,
        } for stage, label in SIMULATED_PILOT_STAGES],
        "blockers_removed_in_simulation": len(receipts),
        "blockers_removed_in_real_world": 0,
        "real_gate_status_before": {key: rows[key]["status"] for key in EXPECTED_BLOCKED},
        "real_gate_status_after": {key: rows[key]["status"] for key in EXPECTED_BLOCKED},
        "simulated_gate_count": len(receipts),
        "simulated_pass_count": sum(item["simulation_outcome"] == "PASS" for item in receipts),
        "real_gate_pass_count_created": 0,
        "external_effects_performed": False,
        "customer_authority_created": False,
        "paid_service_used": False,
        "real_customer_data_used": False,
        "underlying_rehearsal": {
            "scenario": "retally-first-customer-northstar-synthetic-v1",
            "invoice_count": core["population_invoice_count"],
            "supported_findings_cents": metrics["validated_finding_cents"],
            "net_recovery_cents": metrics["realized_cents"],
            "fee_eligible_cents": metrics["fee_eligible_realized_cents"],
            "modeled_fee_cents": fee["recovery_fee_cents"],
            "billing_authorized": fee["billing_authorized"],
            "carrier_action_external_action_performed": core["carrier_action_external_action_performed"],
            "commercial_value_claimed": core["commercial_value_claimed"],
            "stale_report_rejected": root["stale_report_rejected"],
        },
        "gate_receipts": receipts,
        "boundary": "Every PASS in this artifact is simulated. All 14 real gates remain BLOCKED.",
    }
    result = {**body, "rehearsal_sha256": _hash(body)}
    verify_rehearsal(result)
    return result


def verify_rehearsal(result: dict) -> None:
    body = {key: value for key, value in result.items() if key != "rehearsal_sha256"}
    if result.get("rehearsal_sha256") != _hash(body):
        raise ValueError("rehearsal digest mismatch")
    if result.get("synthetic") is not True or result.get("outcome") != "SIMULATION_PASS_REAL_GATES_UNCHANGED":
        raise ValueError("rehearsal synthetic boundary is invalid")
    if result.get("external_effects_performed") is not False or result.get("customer_authority_created") is not False:
        raise ValueError("rehearsal cannot perform external effects or create customer authority")
    if result.get("paid_service_used") is not False or result.get("real_customer_data_used") is not False:
        raise ValueError("rehearsal cannot use paid services or real customer data")
    receipts = result.get("gate_receipts", [])
    if tuple(item.get("gate_id") for item in receipts) != EXPECTED_BLOCKED:
        raise ValueError("rehearsal receipt coverage does not match blocked gates")
    if result.get("simulated_gate_count") != len(EXPECTED_BLOCKED) or result.get("simulated_pass_count") != len(EXPECTED_BLOCKED):
        raise ValueError("not every blocked gate passed its simulation")
    if result.get("real_gate_pass_count_created") != 0:
        raise ValueError("simulation cannot create real gate passes")
    simulated_score = result.get("simulation_scorecard", {})
    if simulated_score.get("classification") != "FICTIONAL_REHEARSAL_ONLY":
        raise ValueError("simulation scorecard boundary is missing")
    if (simulated_score.get("PASS"), simulated_score.get("BLOCKED"), simulated_score.get("FAIL"), simulated_score.get("total")) != (37, 0, 0, 37):
        raise ValueError("simulation scorecard must be 37 PASS / 0 BLOCKED / 0 FAIL")
    if simulated_score.get("real_scorecard_unchanged") is not True:
        raise ValueError("simulation scorecard must preserve the real scorecard")
    if simulated_score.get("customer_pilot_decision") != "FULL_GO_SIMULATED":
        raise ValueError("simulated customer pilot must have an explicit FULL_GO_SIMULATED decision")
    simulated_permissions = (
        "all_simulated_pilot_stages_available",
        "confidential_intake_authorized_in_simulation",
        "customer_service_authorized_in_simulation",
        "financial_operations_authorized_in_simulation",
    )
    if not all(simulated_score.get(key) is True for key in simulated_permissions):
        raise ValueError("every simulated customer-pilot stage must be available")
    if simulated_score.get("real_customer_authorization_created") is not False or simulated_score.get("real_financial_authorization_created") is not False:
        raise ValueError("simulated customer pilot cannot create real authorization")
    if result.get("blockers_removed_in_simulation") != 14 or result.get("blockers_removed_in_real_world") != 0:
        raise ValueError("simulation and real blocker-removal counts are inconsistent")
    stage_decisions = result.get("simulation_stage_decisions", [])
    if tuple(item.get("stage") for item in stage_decisions) != tuple(stage for stage, _ in SIMULATED_PILOT_STAGES):
        raise ValueError("simulated customer-pilot stages are incomplete")
    if any(item.get("decision") != "GO_SIMULATED" or item.get("real_action_authorized") is not False for item in stage_decisions):
        raise ValueError("simulated GO cannot authorize a real action")
    for item in receipts:
        receipt_body = {key: value for key, value in item.items() if key != "receipt_sha256"}
        if item.get("receipt_sha256") != _hash(receipt_body):
            raise ValueError(f"{item.get('gate_id')} receipt digest mismatch")
        if item.get("simulation_outcome") != "PASS" or item.get("real_gate_status") != "BLOCKED":
            raise ValueError(f"{item.get('gate_id')} mixes simulation and real status")
        if item.get("external_effect_performed") is not False or item.get("evidence_can_satisfy_real_gate") is not False:
            raise ValueError(f"{item.get('gate_id')} exceeds simulation boundary")
        for actor in item.get("simulated_actors", []):
            if not actor.get("email", "").endswith(".invalid"):
                raise ValueError(f"{item.get('gate_id')} actor is not visibly fictional")
    if set(result.get("real_gate_status_before", {}).values()) != {"BLOCKED"}:
        raise ValueError("real gates were not blocked before rehearsal")
    if result.get("real_gate_status_before") != result.get("real_gate_status_after"):
        raise ValueError("real gate status changed during rehearsal")
    core = result.get("underlying_rehearsal", {})
    if core.get("billing_authorized") is not False or core.get("carrier_action_external_action_performed") is not False:
        raise ValueError("underlying rehearsal crossed an external boundary")


def render_markdown(result: dict) -> str:
    lines = [
        "# RETALLY remaining-gates synthetic rehearsal",
        "",
        f"Simulation: **{result['simulation_id']}**",
        f"Simulation profile: **{result['simulation_scorecard']['PASS']} PASS / {result['simulation_scorecard']['BLOCKED']} BLOCKED / {result['simulation_scorecard']['FAIL']} FAIL**",
        f"Customer-pilot simulation decision: **{result['simulation_scorecard']['customer_pilot_decision']}**",
        f"New simulations: **{result['simulated_pass_count']}/{result['simulated_gate_count']} passed; 14 blockers removed in simulation**",
        f"Real evidence profile: **{result['real_scorecard']['PASS']} PASS / {result['real_scorecard']['BLOCKED']} BLOCKED / {result['real_scorecard']['FAIL']} FAIL**",
        "",
        "> This is a fictional rehearsal. It is not a signature, customer authorization, provider receipt, human review, insurance policy, legal filing, financial posting, invoice, deletion proof, merge, deployment, or spending approval.",
        "",
        "## Gate results",
        "",
        "| Gate | Simulation | Real status | External effect |",
        "| --- | --- | --- | --- |",
    ]
    for receipt in result["gate_receipts"]:
        lines.append(f"| {receipt['gate_id']} | **{receipt['simulation_outcome']}** | **{receipt['real_gate_status']}** | No |")
    lines.extend([
        "",
        "## Simulated customer-pilot stages",
        "",
        "| Stage | Simulation decision | Real action authorized |",
        "| --- | --- | --- |",
    ])
    for stage in result["simulation_stage_decisions"]:
        lines.append(f"| {stage['label']} | **{stage['decision']}** | No |")
    core = result["underlying_rehearsal"]
    lines.extend([
        "",
        "## Synthetic financial path",
        "",
        f"- Fictional invoices: **{core['invoice_count']}**",
        f"- Supported findings: **${core['supported_findings_cents'] / 100:,.2f}**",
        f"- Net synthetic recovery after reversal: **${core['net_recovery_cents'] / 100:,.2f}**",
        f"- Fee-eligible synthetic recovery: **${core['fee_eligible_cents'] / 100:,.2f}**",
        f"- Modeled 30% fee: **${core['modeled_fee_cents'] / 100:,.2f} — nonbillable**",
        "- Carrier action performed: **No**",
        "- Invoice issued: **No**",
        "- Paid service used: **No**",
        "- Real customer data used: **No**",
        "",
        "## Boundary result",
        "",
        result["boundary"],
        "",
        f"Deterministic rehearsal digest: `{result['rehearsal_sha256']}`",
        "",
    ])
    return "\n".join(lines)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT)
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--verify", type=Path)
    args = parser.parse_args(argv)
    if args.verify:
        verify_rehearsal(json.loads(args.verify.read_text(encoding="utf-8")))
        return 0
    result = run_remaining_gate_rehearsal(json.loads(args.source.read_text(encoding="utf-8")))
    print(render_markdown(result) if args.format == "markdown" else json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
