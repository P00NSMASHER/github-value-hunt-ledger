"""RETALLY first-customer gate evaluation. No network, credentials or client data.

The evidence register is a bounded, explicitly unapproved snapshot. A status is not
VERIFIED unless independent owner/reviewer/timestamp/source evidence is present.
Exit 2 on requested but blocked readiness. No tool can authorize a customer itself.
"""
from __future__ import annotations
import argparse
from datetime import date
from decimal import Decimal
import json
from pathlib import Path

DEFAULT = Path(__file__).with_name("first_customer_acceptance_m2g.json")
# This CLI consumes self-asserted repository JSON. A complete set of strings
# must never be mistaken for independently authenticated customer approval.
EXTERNAL_AUTHORIZATION_STAGES = frozenset({
    "qualified_proposal", "confidential_pilot", "claims_recovery",
    "sample_publication",
})
EXTERNAL_APPROVAL_BLOCKER = "independent_out_of_band_release_approval_required"

ZERO_SPEND_REQUIRED_PROHIBITIONS = frozenset({
    "automatic_online_inquiry",
    "customer_record_ingestion",
    "confidential_file_processing",
    "operator_case_mutation",
    "carrier_or_customer_outreach",
    "provider_financial_event_ingestion",
    "payment_instruction_release",
    "customer_billing",
    "production_release_of_draft_329_or_332",
})


def verified(item):
    if item.get("status") != "VERIFIED":
        return False
    for key in ("evidence_ref", "reviewed_by", "reviewed_at"):
        if not isinstance(item.get(key), str) or not item[key].strip():
            return False
    try:
        date.fromisoformat(item["reviewed_at"][:10])
    except ValueError:
        return False
    return True


def evaluate_zero_spend_profile(snapshot):
    """Prove the already-live public/manual surface needs no blocked subsystem.

    This is a scope-removal gate, not customer or financial authorization. It
    passes only while every automated, confidential, operator-write and money
    capability remains explicitly unavailable.
    """
    profile = snapshot["zero_spend_launch_profile"]
    production = snapshot["production"]
    prohibited = set(profile.get("prohibited_capabilities", ()))
    non_dependencies = profile.get("non_dependencies", {})
    checks = {
        "existing_public_site_live": (
            production.get("deployment_status") == "success"
            and production.get("domain_status") == "active"
        ),
        "automated_inquiry_off": (
            production.get("inquiry_get_body", {}).get("online") is False
            and production.get("online_inquiry_status") == "DISABLED_BY_POLICY"
        ),
        "zero_new_spend": profile.get("new_external_spend_authorized_usd") == "0.00",
        "no_new_deployment": profile.get("requires_new_deployment") is False,
        "dangerous_capabilities_prohibited": ZERO_SPEND_REQUIRED_PROHIBITIONS <= prohibited,
        "optional_blockers_removed_from_scope": (
            {"R28", "R29", "R30", "R31", "R35"} <= set(non_dependencies)
        ),
        "no_customer_authorization": profile.get("customer_service_authorized") is False,
        "no_financial_authorization": profile.get("financial_operations_authorized") is False,
        "no_full_production_claim": profile.get("full_production_authorized") is False,
    }
    return {
        "id": profile.get("id"),
        "ready": all(checks.values()),
        "decision": profile.get("decision"),
        "checks": checks,
        "blocked_subsystems_are_not_bypassed": True,
        "customer_kickoff_authorized": False,
        "financial_operations_authorized": False,
    }


def evaluate(snapshot):
    f = snapshot["published_synthetic_sample"]
    D = lambda k: Decimal(f[k])
    if D("gross_recovered_usd")-D("reversals_usd") != D("net_recovered_usd"):
        raise ValueError("gross/net sample arithmetic inconsistent")
    if D("net_recovered_usd")-D("published_fee_eligible_usd") != D("unallocated_difference_usd"):
        raise ValueError("sample eligibility delta inconsistent")
    if f.get("customer_result") is not False:
        raise ValueError("synthetic example must not be designated customer proof")
    status = snapshot["requirements"]
    gates = {}
    for name, required in snapshot["readiness_gates"].items():
        unknown = [key for key in required if key not in status]
        if unknown:
            raise ValueError(f"unknown required evidence fields: {unknown}")
        missing = [key for key in required if not verified(status[key])]
        if name in ("claims_recovery",) and snapshot["founding_offer"]["actual_contingency_rate"] == "NOT_APPROVED":
            missing.append("approved_actual_contingency_terms")
        # Stage evidence is a source-only checklist, not a signature, a bank
        # posting, a reviewer appointment, or a release decision. In particular,
        # neither changing release_policy nor filling every JSON field can
        # promote these stages to READY without a separate trusted verifier.
        claimed_fields_complete = not missing
        if name in EXTERNAL_AUTHORIZATION_STAGES:
            missing.append(EXTERNAL_APPROVAL_BLOCKER)
        gates[name] = {
            "ready": not missing, "missing":missing,
            "declared_fields_complete": claimed_fields_complete,
        }
    if snapshot["production"]["inquiry_get_body"].get("online") is False and snapshot["production"]["online_inquiry_status"] != "DISABLED_BY_POLICY":
        raise ValueError("inquiry readiness contradicts observed disabled capability")
    zero_spend = evaluate_zero_spend_profile(snapshot)
    return {
        "as_of": snapshot["as_of"], "release_policy": snapshot["release_policy"],
        "sample_fee_eligibility_verified":verified(status["synthetic_fee_eligibility_reconciled"]),
        "gates": gates,
        "all_customer_pilot_gates_ready": gates["confidential_pilot"]["ready"] and gates["qualified_proposal"]["ready"],
        "customer_kickoff_authorized": False,
        "actual_financial_operations_authorized": False,
        "source_only_not_external_attestation": True,
        "zero_spend_public_manual_profile": zero_spend,
    }


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT)
    parser.add_argument("--require", choices=["contact","qualified_proposal","confidential_pilot","claims_recovery","sample_publication","zero_spend_public_manual"])
    args=parser.parse_args()
    result=evaluate(json.loads(args.source.read_text(encoding="utf-8")))
    print(json.dumps(result,indent=2,sort_keys=True))
    if args.require:
        if args.require == "zero_spend_public_manual":
            if not result["zero_spend_public_manual_profile"]["ready"]:
                return 2
        elif not result["gates"][args.require]["ready"]:
            return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
