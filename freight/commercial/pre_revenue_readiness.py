"""Read-only, zero-new-spend operating plan for RETALLY's first potential customer.

This is an internal readiness packet, not a legal opinion, an approval engine,
a prospect database, or a request to incur costs. It never contacts anyone,
changes production settings, files registrations, opens financial access or
turns synthetic approval metadata into genuine customer authorization.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from freight.commercial.first_customer_gate import DEFAULT, evaluate

# External actions have deliberately NO approval path in this source-only tool.
FORBIDDEN_AUTOMATIC_ACTIONS = (
    "business_registration",
    "new_vendor_spending",
    "outbound_customer_contact",
    "confidential_customer_intake",
    "customer_onboarding_or_service",
    "production_deployment",
    "carrier_claim",
    "invoice_or_fee_issuance",
    "bank_or_stripe_transaction",
    "hosted_financial_posting",
)
EXTERNAL_GATE_IDS = (
    "R22",  # lawful business/contracting party
    "R23",  # executed customer commercial terms
    "R24",  # insurance decision
    "R25",  # independent qualified human
    "R26",  # actual buyer-specific MFA and access
    "R27",  # actual confidentiality and records authority
    "R30",  # hosted receipt custody - known failure
    "R31",  # real hosted identity and provider proof
    "R32",  # actual settlement posting
    "R33",  # actual fee authority
    "R34",  # lawful retention/disposal
    "R35",  # exact-source release approval
)


def build_plan(snapshot: dict) -> dict:
    """Expose a phased, non-executing plan; never change an acceptance result."""
    checked = evaluate(snapshot)
    production = snapshot["production"]
    release_is_review_only = snapshot.get("release_policy") == "REVIEW_ONLY_NO_CUSTOMER_DATA"
    automated_inquiry_off = (
        production.get("online_inquiry_status") == "DISABLED_BY_POLICY"
        and production.get("inquiry_get_body", {}).get("online") is False
    )
    safe_source_state = release_is_review_only and automated_inquiry_off
    manual_draft_exists = production.get("public_fallback") == "browser_prepared_email_draft"
    rows = snapshot["mission_acceptance"]["requirements"]
    if not isinstance(rows, list) or not all(isinstance(row, dict) for row in rows):
        raise ValueError("acceptance ledger must contain requirement objects")
    indexed = {row["id"]: row for row in rows}
    if len(indexed) != len(rows):
        raise ValueError("duplicate acceptance requirement IDs")
    missing = set(EXTERNAL_GATE_IDS) - indexed.keys()
    if missing:
        raise ValueError("missing external gate IDs: " + ", ".join(sorted(missing)))
    external_holds = {
        key: indexed[key]["status"]
        for key in EXTERNAL_GATE_IDS
        if indexed[key].get("status") != "PASS"
    }
    return {
        "classification": "READ_ONLY_PRE_REVENUE_PREPARATION",
        "source_as_of": snapshot["as_of"],
        "new_external_spend_authorized_usd": "0.00",
        "registration_action": "DEFER_NO_FILING_FROM_THIS_PLAN",
        "no_spend_preparation": "SOURCE_AND_SYNTHETIC_ONLY" if safe_source_state else "HOLD_SOURCE_OR_INQUIRY_DRIFT",
        "safe_pre_revenue_mode": safe_source_state,
        "prepared_manual_email_draft": manual_draft_exists,
        "manual_draft_is_verified_delivery": False,
        "zoho_owner_attestation": production.get("inbound_zoho_status", "UNVERIFIED"),
        "automatic_permissions": {name: False for name in FORBIDDEN_AUTOMATIC_ACTIONS},
        "source_only_gate_status": checked["gates"],
        "historical_external_requirement_status": external_holds,
        "next_steps": {
            "before_a_real_prospect": [
                "Keep the existing public site and manual email draft; leave online intake disabled.",
                "Use current synthetic rehearsals, onboarding templates and bounded cost models.",
                "No paid subscriptions, filings, purchases, outreach, real records or production changes.",
            ],
            "when_a_credible_prospect_appears": [
                "Request owner permission before any reply; capture only non-sensitive qualification metadata.",
                "Check customer identity, freight mode/date range, approximate volume and prior-auditor overlap.",
                "Do not request invoices, bank details, rate sheets or shipment documents yet.",
                "Decide whether the opportunity is worth completing the legal and security gates.",
            ],
            "before_contract_or_confidential_service": [
                "Confirm lawful contracting identity and any required registration BEFORE doing business under RETALLY.",
                "Complete applicable counsel, commercial terms, signature and insurance decisions.",
                "Set actual independent-reviewer capacity, effort hours and a cash cost cap.",
                "Prove buyer-specific consent/source rights and an approved MFA-restricted workspace.",
                "Verify authority and safety of the exact manual or hosted route; no implicit reuse of staging.",
            ],
            "later_if_claims_or_money_are_approved": [
                "Get claim-specific buyer approval before any carrier communication.",
                "Separate possible findings, accepted credits, posted recovery and fee-eligible actual value.",
                "Authorize invoices, refunds or payment only with real signed terms and reviewed custody evidence.",
                "Keep Stripe/hosted financial posting off until their independent release gates pass.",
            ],
        },
        "not_a_customer_launch_authorization": True,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, default=DEFAULT)
    parser.add_argument("--require-safe-pre-revenue-mode", action="store_true",
                        help="Exit 2 if review-only or disabled-inquiry invariants drift.")
    args = parser.parse_args(argv)
    snapshot = json.loads(args.source.read_text(encoding="utf-8"))
    plan = build_plan(snapshot)
    print(json.dumps(plan, indent=2, sort_keys=True))
    if args.require_safe_pre_revenue_mode and not plan["safe_pre_revenue_mode"]:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
