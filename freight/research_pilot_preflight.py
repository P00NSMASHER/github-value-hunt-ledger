"""RETALLY Mission 11: non-executing prospective pilot evidence preflight.

This is ONLY a control-plan generator inside existing Research Lab 14.
No customer input, real documents, external approvals, live account links,
download, signed artifacts, storage system, carrier submissions or payments.
Every field declaring a third-party approval MUST remain unverified here.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from html import escape
import json
from pathlib import Path

from freight.research_evidence_gate import canon_hash
from freight.research_validation_protocols import build_protocol_report
from freight.research_data_readiness import build_readiness
from freight.research_rehearsal import run_rehearsal
from freight.research_ground_truth import run_ground_truth

ROOT = Path(__file__).resolve().parent
CONTRACT = ROOT / "research" / "PILOT_PREFLIGHT_20261011.json"
SCOPE = "RETALLY_LAB14_PROSPECTIVE_PILOT_PREFLIGHT_NO_REAL_RECORDS"
STAGES = (
    ("AUTHORITY", "Buyer authority, data rights and representation"),
    ("SECURITY", "Privacy, security and lifecycle"),
    ("EVIDENCE", "Original invoice and governing evidence chain"),
    ("SAMPLING", "Preregistered study design and frame"),
    ("ADJUDICATION", "Blind independent review and disputes"),
    ("ECONOMICS", "Net cash, reversals and publishing controls"),
)
ROLES = {
    "DATA_OWNER", "LEGAL_COUNSEL", "SECURITY_OWNER",
    "RESEARCH_LEAD", "INDEPENDENT_ADJUDICATOR", "FINANCE_CONTROLLER",
}
OWNERS = (
    "DATA_OWNER", "LEGAL_COUNSEL", "DATA_OWNER",
    "SECURITY_OWNER", "SECURITY_OWNER", "SECURITY_OWNER",
    "RESEARCH_LEAD", "LEGAL_COUNSEL", "FINANCE_CONTROLLER",
    "RESEARCH_LEAD", "RESEARCH_LEAD", "RESEARCH_LEAD",
    "INDEPENDENT_ADJUDICATOR", "INDEPENDENT_ADJUDICATOR", "RESEARCH_LEAD",
    "FINANCE_CONTROLLER", "FINANCE_CONTROLLER", "LEGAL_COUNSEL",
)
GATE_KEYS = {
    "id", "stage", "owner_role", "name", "required_evidence",
    "why_missing_blocks", "next_internal_step", "related_studies",
    "status", "verified", "external_signoff_observed",
    "receipt_of_original_evidence", "assigned_real_person",
}
BOOK_KEYS = {
    "schema_version", "scope", "created_on", "status", "proposed_studies",
    "intended_scope", "references", "no_customer_contact_authorized",
    "real_customer_records_received", "approved_data_transfers",
    "real_buyer_authorizations_verified", "real_blind_reviewers_appointed",
    "live_payment_events_examined", "approved_external_study_results",
    "data_collection_enabled", "external_carrier_or_financial_actions_allowed",
    "public_performance_claims_allowed", "privacy_security_clearance_proven",
    "no_new_lab", "stages", "gates",
}
ZERO_BOOK_FLAGS = (
    "real_customer_records_received", "approved_data_transfers",
    "real_buyer_authorizations_verified", "real_blind_reviewers_appointed",
    "live_payment_events_examined", "approved_external_study_results",
)
FALSE_BOOK_FLAGS = (
    "data_collection_enabled", "external_carrier_or_financial_actions_allowed",
    "public_performance_claims_allowed", "privacy_security_clearance_proven",
)
EXPECTED_REFERENCES = {
    "NIST": "https://www.nist.gov/privacy-framework",
    "AAPOR": "https://aapor.org/standards-and-ethics/disclosure-standards/",
}
SUPPORTED_STUDIES = {"M7-01", "M7-06"}


def _iso(raw: object) -> date:
    if type(raw) is not str:
        raise ValueError("ISO date string required")
    value = date.fromisoformat(raw)
    if value.isoformat() != raw:
        raise ValueError("canonical ISO date required")
    return value


def _meaningful(raw: object, minimum: int = 24, maximum: int = 700) -> bool:
    return type(raw) is str and minimum <= len(raw.strip()) <= maximum


def _hash_is_valid(record: object) -> bool:
    if not isinstance(record, dict):
        return False
    digest = record.get("receipt_sha256")
    return (
        isinstance(digest, str) and len(digest) == 64
        and digest == canon_hash({
            k: v for k, v in record.items() if k != "receipt_sha256"
        })
    )


def _reports_are_held(protocols: dict, sources: dict,
                      rehearsal: dict, ground: dict) -> list[str]:
    errors: list[str] = []
    if (not _hash_is_valid(protocols) or
        protocols.get("scope") != "LAB14_INTERNAL_STUDY_DESIGN_REVIEW_ONLY" or
        protocols.get("protocol_count") != 6 or
        protocols.get("new_lab_created") is not False or
        protocols.get("existing_lab_number") != 14 or
        protocols.get("external_studies_executed") != 0 or
        protocols.get("observed_customer_outcomes") != 0 or
        protocols.get("approved_preregistrations") != 0 or
        protocols.get("external_actions_allowed") is not False or
        protocols.get("public_performance_claims_allowed") is not False):
        errors.append("Mission 7 study design was altered or promoted")
    else:
        studies = protocols.get("protocols")
        if (not isinstance(studies, list) or len(studies) != 6 or
            not SUPPORTED_STUDIES <= {p.get("experiment_id") for p in studies
                                      if isinstance(p, dict)} or
            any(p.get("status") != "DESIGN_REVIEW_REQUIRED_NOT_EXECUTED"
                or p.get("can_publish_customer_results") is not False
                for p in studies if isinstance(p, dict))):
            errors.append("Mission 7 protocol status or coverage not held")

    if (not _hash_is_valid(sources) or
        sources.get("scope") != "LAB14_PUBLIC_DATA_DISCOVERY_AND_RIGHTS_HOLD" or
        sources.get("source_leads") != 7 or
        sources.get("rights_cleared_reuse_count") != 0 or
        sources.get("datasets_imported") != 0 or
        sources.get("invoice_ground_truth_benchmarks") != 0 or
        sources.get("live_customer_or_carrier_data_used") is not False or
        sources.get("external_source_content_fetched") is not False or
        sources.get("public_performance_claims_allowed") is not False or
        sources.get("new_lab_created") is not False or
        sources.get("existing_lab_number") != 14):
        errors.append("Mission 9 public source cannot be promoted to approved invoice data")
    if (not _hash_is_valid(rehearsal) or
        rehearsal.get("scope") != "LAB14_SYNTHETIC_ARITHMETIC_AND_DATA_QUALITY_REHEARSAL_ONLY" or
        rehearsal.get("invented_case_records") != 35 or
        rehearsal.get("rehearsed_protocols") != 6 or
        rehearsal.get("independent_customer_observations") != 0 or
        rehearsal.get("external_studies_executed") != 0 or
        rehearsal.get("verified_business_results") is not False or
        rehearsal.get("public_claims_authorized") is not False):
        errors.append("Mission 8 synthetic results have been misrepresented")
    if (not _hash_is_valid(ground) or
        ground.get("scope") != "LAB14_GROUND_TRUTH_INSTRUMENT_ONLY" or
        ground.get("case_count") != 10 or
        ground.get("verified_ground_truth_cases") != 0 or
        ground.get("real_customer_cases") != 0 or
        ground.get("actual_cash_recovered_cents") != 0 or
        ground.get("synthetic_only") is not True or
        ground.get("external_actions_allowed") is not False or
        ground.get("approved_public_performance_benchmark") is not False or
        ground.get("legal_applicability_established") is not False or
        ground.get("new_lab_created") is not False):
        errors.append("Mission 10 synthetic ground truth was promoted or altered")
    if (isinstance(protocols, dict) and isinstance(sources, dict) and
        sources.get("protocol_report_sha256") != protocols.get("receipt_sha256")):
        errors.append("Mission 9 wrong study provenance link")
    if (isinstance(protocols, dict) and isinstance(rehearsal, dict) and
        rehearsal.get("protocol_report_sha256") != protocols.get("receipt_sha256")):
        errors.append("Mission 8 wrong study provenance link")
    if (isinstance(protocols, dict) and isinstance(ground, dict) and
        ground.get("study_design_sha256") != protocols.get("receipt_sha256")):
        errors.append("Mission 10 wrong study provenance link")
    return errors


def validate_preflight(book: dict, protocols: dict, sources: dict,
                       rehearsal: dict, ground: dict,
                       *, as_of: date) -> list[str]:
    """Fail closed on fake consent, real document fields and forged approvals."""
    errors = _reports_are_held(protocols, sources, rehearsal, ground)
    if type(book) is not dict or book.get("schema_version") != 1:
        return errors + ["pilot preflight schema must be an object at v1"]
    if set(book) != BOOK_KEYS:
        errors.append("unexpected pilot fields; signed artifacts and PII not accepted")
    if book.get("scope") != SCOPE:
        errors.append("not a research-only pilot evidence preflight")
    if book.get("status") != "INTERNAL_DESIGN_ONLY_UNAPPROVED":
        errors.append("pilot approval or execution may not be self-declared")
    try:
        if _iso(book.get("created_on")) > as_of:
            errors.append("preflight plan cannot be future-dated")
    except ValueError:
        errors.append("invalid preflight creation date")
    if book.get("proposed_studies") != ["M7-01", "M7-06"]:
        errors.append("unapproved pilot study targets")
    if not _meaningful(book.get("intended_scope"), 50):
        errors.append("prospective pilot purpose and limitations required")
    if book.get("no_customer_contact_authorized") is not True or book.get("no_new_lab") is not True:
        errors.append("pilot planning cannot contact parties or add a new lab")
    for key in ZERO_BOOK_FLAGS:
        if type(book.get(key)) is not int or book[key] != 0:
            errors.append(f"{key}: real-world outcomes, evidence or authorization forbidden")
    for key in FALSE_BOOK_FLAGS:
        if book.get(key) is not False:
            errors.append(f"{key}: external action, publication or clearance forbidden")

    references = book.get("references")
    if type(references) is not list or len(references) != 2:
        errors.append("exactly two methodological references required")
    else:
        seen_orgs = set()
        for ref in references:
            if type(ref) is not dict or set(ref) != {"organization", "url", "why"}:
                errors.append("malformed methodological reference")
                continue
            org = ref.get("organization")
            if type(org) is not str or org not in EXPECTED_REFERENCES or org in seen_orgs:
                errors.append("unsupported/duplicate methodological publisher")
                continue
            seen_orgs.add(org)
            if ref.get("url") != EXPECTED_REFERENCES[org] or not _meaningful(ref.get("why"), 35):
                errors.append(f"{org}: reference meaning, origin or scope altered")
        if seen_orgs != set(EXPECTED_REFERENCES):
            errors.append("required independent research method references missing")

    stage_rows = book.get("stages")
    if type(stage_rows) is not list or len(stage_rows) != len(STAGES):
        errors.append("exactly six pilot review stages required")
    elif any(type(v) is not dict or v != {"id": id_, "name": name}
             for v, (id_, name) in zip(stage_rows, STAGES)):
        errors.append("stage scope/order/purpose changed")
    gates = book.get("gates")
    if type(gates) is not list or len(gates) != 18:
        return errors + ["exactly 18 unmet pilot review controls required"]
    for idx, gate in enumerate(gates):
        gid = f"P11-{idx+1:02}"
        if type(gate) is not dict or set(gate) != GATE_KEYS:
            errors.append(f"{gid}: missing or unexpected key; cannot load real evidence")
            continue
        if gate.get("id") != gid:
            errors.append(f"{gid}: gate id or order was changed")
        if gate.get("stage") != STAGES[idx // 3][0]:
            errors.append(f"{gid}: review stage swapped")
        if gate.get("owner_role") != OWNERS[idx] or gate.get("owner_role") not in ROLES:
            errors.append(f"{gid}: independent owner roles were changed")
        if (gate.get("status") != "NOT_EVIDENCED" or
            gate.get("verified") is not False or
            gate.get("external_signoff_observed") is not False or
            gate.get("assigned_real_person") is not False or
            gate.get("receipt_of_original_evidence") is not None):
            errors.append(f"{gid}: independent signoff/evidence not established")
        for name in ("name", "required_evidence", "why_missing_blocks",
                     "next_internal_step"):
            if not _meaningful(gate.get(name), 12 if name == "name" else 45):
                errors.append(f"{gid}: missing bounded {name}")
        expected_studies = ["M7-06"] if idx in (15, 16) else ["M7-01", "M7-06"]
        if gate.get("related_studies") != expected_studies:
            errors.append(f"{gid}: link to prospective study boundary mismatch")
    return errors


def build_preflight(*, as_of: date, book: dict | None = None,
                    protocols: dict | None = None, sources: dict | None = None,
                    rehearsal: dict | None = None, ground: dict | None = None) -> dict:
    """Assemble an explainable 18-control gap plan; no external approval path."""
    if protocols is None:
        protocols = build_protocol_report(as_of=as_of)
    if book is None:
        book = json.loads(CONTRACT.read_text(encoding="utf-8"))
    if sources is None:
        sources = build_readiness(as_of=as_of, protocols=protocols)
    if rehearsal is None:
        rehearsal = run_rehearsal(as_of=as_of, protocol_report=protocols)
    if ground is None:
        ground = run_ground_truth(as_of=as_of, protocols=protocols)
    errors = validate_preflight(book, protocols, sources, rehearsal, ground,
                                as_of=as_of)
    if errors:
        raise ValueError("INVALID_PILOT_PREFLIGHT: " + "; ".join(errors))
    case_rows = ground["cases"]
    mock_agreement = sum(
        len(p["reviewer_votes"]) == 2 and
        p["reviewer_votes"][0] == p["reviewer_votes"][1]
        for p in case_rows
    )
    missing_by_stage: Counter[str] = Counter()
    required = []
    for idx, gate in enumerate(book["gates"], start=1):
        missing_by_stage[gate["stage"]] += 1
        required.append({
            "id": gate["id"], "order": idx, "stage": gate["stage"],
            "name": gate["name"], "owner_role": gate["owner_role"],
            "evidence_requested_for_future_human_review": gate["required_evidence"],
            "risk_if_unproven": gate["why_missing_blocks"],
            "next_internal_preparation_step": gate["next_internal_step"],
            "related_studies": gate["related_studies"],
            "status": "REQUIRED_INDEPENDENT_PROOF_NOT_RECEIVED",
            "real_world_evidence_observed": False,
            "approval_and_storage_authorized": False,
            "external_actions_permitted": False,
        })
    stages = [{
        "id": id_, "name": name,
        "required_evidence_records": missing_by_stage[id_],
        "actual_verified_records": 0,
        "state": "INDEPENDENT_HUMAN_REVIEW_REQUIRED",
    } for id_, name in STAGES]
    freshness = sources.get("metadata_sources_due_for_recheck", 0)
    report = {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "scope": "LAB14_PROSPECTIVE_PILOT_INTERNAL_READINESS_ONLY",
        "linked_mission_receipts": {
            "M7_protocols": protocols["receipt_sha256"],
            "M8_rehearsal": rehearsal["receipt_sha256"],
            "M9_public_data_readiness": sources["receipt_sha256"],
            "M10_synthetic_invoice": ground["receipt_sha256"],
            "M11_gate_definitions": canon_hash(book),
        },
        "target_studies": ["M7-01", "M7-06"],
        "studies_with_pilot_data": 0,
        "required_controls": len(required),
        "controls_with_independently_verified_external_evidence": 0,
        "unmet_requirements": len(required),
        "workflow_stage_count": len(stages),
        "readiness": "BLOCKED_NO_VERIFIED_BUYER_PERMISSION_OR_REAL_EVIDENCE",
        "source_leads": sources["source_leads"],
        "public_data_sources_due_for_review": freshness,
        "datasets_imported": 0,
        "real_invoices_received": 0,
        "actual_human_independent_reviewers": 0,
        "verified_invoice_overcharges": 0,
        "real_net_recovery_cents": 0,
        "fictional_invoice_cases_used_as_design_tests": ground["case_count"],
        "fictional_test_case_reviewer_concordance": {
            "equal_votes": mock_agreement, "mock_pairs": len(case_rows),
            "agreement_fraction": f"{mock_agreement}/{len(case_rows)}",
            "actual_independent_reviewer_reliability_established": False,
            "why_not_valid": ("Both reviewer votes are generated from the same "
                              "synthetic fixture function; calling them blind "
                              "does not demonstrate human independence or accuracy."),
        },
        "stages": stages,
        "evidence_preparation_queue": required,
        "external_customer_contact": False,
        "live_customer_document_intake": False,
        "external_claim_or_fee_action": False,
        "product_security_or_legal_clearance": False,
        "real_world_study_authorized": False,
        "public_performance_claims_permitted": False,
        "existing_lab_number": 14,
        "new_lab_created": False,
        "limits": ("The gate catalog is a prospective metadata-only checklist, "
                   "not submitted evidence. Hashes establish internal report "
                   "consistency only, not signatures, agreements, third-party "
                   "verification or legal authorization. Human approval must "
                   "occur through separately designed, secure workflows."),
    }
    report["receipt_sha256"] = canon_hash(report)
    return report


def render_html(report: dict) -> str:
    """Static, safe internal review view. Never display customer data."""
    stage_cards = []
    for stage in report["stages"]:
        items = [g for g in report["evidence_preparation_queue"]
                 if g["stage"] == stage["id"]]
        cards = []
        for gate in items:
            cards.append(
                '<article><small>' + escape(gate["id"]) + ' · ' +
                escape(gate["owner_role"].replace("_", " ")) +
                ' · NOT VERIFIED</small><h3>' + escape(gate["name"]) +
                '</h3><p><b>Evidence:</b> ' +
                escape(gate["evidence_requested_for_future_human_review"]) +
                '</p><p><b>Risk:</b> ' + escape(gate["risk_if_unproven"]) +
                '</p><p><b>Internal next step:</b> ' +
                escape(gate["next_internal_preparation_step"]) + '</p></article>'
            )
        stage_cards.append(
            '<section><h2>' + escape(stage["name"]) + '</h2>' +
            '<p>' + str(stage["required_evidence_records"]) +
            ' requirements remain unverified.</p><div class="grid">' +
            "".join(cards) + '</div></section>'
        )
    agreement = report["fictional_test_case_reviewer_concordance"]
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Pilot Readiness</title><style>'
        '*{box-sizing:border-box}body{background:#f6f9f7;color:#19382b;'
        'font:15px/1.6 system-ui,-apple-system,sans-serif;margin:0}'
        'main{max-width:1160px;margin:auto;padding:30px 18px 76px}'
        'header{border-bottom:1px solid #d4e4d8;padding-bottom:24px}'
        'small{color:#547466;font-size:12px;letter-spacing:.06em}'
        'h1{font-size:clamp(31px,5vw,50px);letter-spacing:-.045em;line-height:1.09}'
        'h2{font-size:22px;margin-top:36px}h3{font-size:17px;line-height:1.3}'
        '.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(270px,1fr));gap:15px}'
        'article{background:white;border:1px solid #dce9dd;'
        'border-radius:14px;padding:20px}article p{overflow-wrap:anywhere}'
        'b{color:#19714d}.stats{display:flex;flex-wrap:wrap;gap:24px}'
        '.stats div{background:white;border:1px solid #dce9dd;'
        'border-radius:12px;padding:15px 20px}'
        '.stats strong{display:block;font-size:26px}</style></head>'
        '<body><main><header><small>RETALLY / EXISTING LAB 14 / MISSION 11'
        ' / RESEARCH-ONLY</small>'
        '<h1>Prepare for a real pilot without pretending one happened.</h1>'
        '<p>Metadata-only preparation checklist. No customer consent, no '
        'real invoices, no independent human adjudicators, no transfer '
        'approval, no product security or legal clearance, and no '
        'permission to make carrier claims.</p>'
        '<div class="stats"><div><strong>' +
        str(report["required_controls"]) +
        '</strong>Unverified requirements</div><div><strong>' +
        str(report["real_invoices_received"]) +
        '</strong>Real invoices</div><div><strong>' +
        str(report["studies_with_pilot_data"]) +
        '</strong>Executed buyer pilots</div></div>'
        '<p><b>Mock reviewer concordance: ' +
        escape(agreement["agreement_fraction"]) +
        '</b>. Not independent human reliability: ' +
        escape(agreement["why_not_valid"]) + '</p></header>' +
        "".join(stage_cards) +
        '<footer><small>Internal local receipt: ' +
        escape(report["receipt_sha256"]) +
        '. Passing tests never confers privacy, legal or external '
        'claims authority.</small></footer></main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date", type=date.fromisoformat,
                        default=date.today())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_preflight(as_of=args.as_of_date)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "pilot_preflight.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "pilot_preflight.html").write_text(
        render_html(report), encoding="utf-8"
    )
    print(json.dumps({
        "unverified_controls": report["unmet_requirements"],
        "real_invoices": report["real_invoices_received"],
        "actual_buyers": report["studies_with_pilot_data"],
        "receipt": report["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
