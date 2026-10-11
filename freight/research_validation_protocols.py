"""RETALLY Lab 14 Mission 7: falsifiable, non-executing research protocols.

The frozen designs are NOT approved preregistrations, empirical findings,
authorization to recruit, validation of customer outcomes, or product approval.
No networking, customer data, carrier operations or payments occur here.
"""
from __future__ import annotations

import argparse
from datetime import date
from html import escape
import json
from pathlib import Path
import re

from freight.research_evidence_gate import canon_hash, run_mission

ROOT = Path(__file__).resolve().parent
BOOK = ROOT / "research" / "VALIDATION_PROTOCOLS_20261010.json"
SCOPE = "RETALLY_LAB14_PRE_REGISTERED_DESIGNS_RESEARCH_ONLY"
DECISIONS = {f"M4-{n:02}" for n in range(1, 7)}
STUDY_TYPES = {
    "BLINDED_REFERENCE_ADJUDICATION",
    "TEMPORAL_BOUNDARY_REGRESSION",
    "CONTROLLED_RANDOMIZED_SURVEY",
    "STRATIFIED_ACCOUNT_SAMPLE",
    "COMMON_FIXTURE_COMPARISON",
    "RECONCILED_COHORT_ACCOUNTING",
}
TEXT_FIELDS = (
    "name", "unit_of_analysis", "population_frame", "sample_selection",
    "comparison_group", "positive_signal", "negative_signal",
    "independent_reviewer", "missingness_policy", "stop_rule",
    "next_internal_step",
)
FALSE_FIELDS = (
    "preregistration_approved", "threshold_approved",
    "sample_size_approved", "published_performance_claim",
    "contact_or_carrier_action_authorized", "financial_action_authorized",
)
ZERO_FIELDS = ("observed_sample_count", "independently_verified_outcomes")
METRIC_FIELDS = ("name", "numerator", "denominator", "unit", "formula")
HEX_EXPERIMENT = re.compile(r"^M7-0[1-6]$")


def _day(value: object, field: str, errors: list[str]) -> date | None:
    if type(value) is not str:
        errors.append(f"{field}: date string required")
        return None
    try:
        day = date.fromisoformat(value)
        if day.isoformat() != value:
            raise ValueError("noncanonical date")
        return day
    except ValueError:
        errors.append(f"{field}: canonical ISO date required")
        return None


def _nonempty(value: object) -> bool:
    return type(value) is str and 15 <= len(value.strip()) <= 3000


def validate_protocols(book: dict, decision_register: dict, *, as_of: date) -> list[str]:
    """Reject fraudulent progress, unbound research and unusable study designs."""
    if type(book) is not dict or book.get("schema_version") != 1:
        return ["schema_version must be 1"]
    errors: list[str] = []
    if book.get("scope") != SCOPE:
        errors.append("unauthorized research protocol scope")
    created = _day(book.get("created_on"), "created_on", errors)
    if created is not None and created > as_of:
        errors.append("future research design date")
    if book.get("public_performance_claims_authorized") is not False:
        errors.append("research cannot authorize public performance claims")
    if type(book.get("actual_external_experiments_run")) is not int or book["actual_external_experiments_run"] != 0:
        errors.append("external study execution cannot be asserted")
    if type(decision_register) is not dict or type(decision_register.get("decisions")) is not list:
        return errors + ["bound opposition decision register required"]
    rows = decision_register["decisions"]
    try:
        decisions = {r["id"]: r for r in rows}
    except (TypeError, KeyError):
        return errors + ["invalid opposition decisions"]
    if len(rows) != 6 or set(decisions) != DECISIONS:
        errors.append("all six existing opposition decisions required")
    if book.get("intended_decisions") != sorted(DECISIONS):
        errors.append("intended decision census or ordering differs")
    references = book.get("methodological_references")
    if not isinstance(references, list) or len(references) < 2:
        errors.append("methodological references required")
    else:
        for ref in references:
            if (not isinstance(ref, dict) or
                not _nonempty(ref.get("role")) or
                type(ref.get("organization")) is not str or not ref["organization"].strip() or
                type(ref.get("url")) is not str or not ref["url"].startswith("https://")):
                errors.append("invalid methodological reference")
    protocols = book.get("experiments")
    if not isinstance(protocols, list) or len(protocols) != 6:
        return errors + ["exactly six protocols required"]
    seen = set()
    study_types = set()
    linked = set()
    for i, p in enumerate(protocols):
        if type(p) is not dict:
            errors.append(f"protocol {i}: object required")
            continue
        pid = p.get("experiment_id")
        if not isinstance(pid, str) or HEX_EXPERIMENT.fullmatch(pid) is None or pid in seen:
            errors.append(f"protocol {i}: invalid or duplicate experiment_id")
            continue
        seen.add(pid)
        did = p.get("decision_id")
        if did not in decisions:
            errors.append(f"{pid}: unknown opposition decision")
            continue
        if did in linked:
            errors.append(f"{pid}: duplicate decision binding")
        linked.add(did)
        expected_pid = "M7-" + did[-2:]
        if pid != expected_pid:
            errors.append(f"{pid}: protocol ID must match linked decision number")
        decision = decisions[did]
        if p.get("dependent_claim_ids") != decision.get("claim_ids"):
            errors.append(f"{pid}: research dependencies are not exactly source-bound")
        if p.get("study_type") not in STUDY_TYPES:
            errors.append(f"{pid}: unsupported study method")
        elif p["study_type"] in study_types:
            errors.append(f"{pid}: duplicate study design category")
        study_types.add(p.get("study_type"))
        for key in TEXT_FIELDS:
            if not _nonempty(p.get(key)):
                errors.append(f"{pid}: missing or short {key}")
        for key in ("required_evidence", "confounders"):
            value = p.get(key)
            if (not isinstance(value, list) or len(value) < 3 or len(value) > 12
                    or len(set(str(v) for v in value)) != len(value)
                    or any(not _nonempty(v) for v in value)):
                errors.append(f"{pid}: three or more distinct {key} entries required")
        metric = p.get("primary_metric")
        if not isinstance(metric, dict):
            errors.append(f"{pid}: primary metric object required")
        else:
            for key in METRIC_FIELDS:
                if not _nonempty(metric.get(key)):
                    errors.append(f"{pid}: missing metric {key}")
            formula = metric.get("formula", "")
            if isinstance(formula, str) and (" / " not in formula or "denominator=0" not in formula):
                errors.append(f"{pid}: numerator/denominator and zero-denominator treatment required")
        if p.get("source_data_mode") != "DESIGN_ONLY_NO_CUSTOMER_DATA":
            errors.append(f"{pid}: design-only data boundary violated")
        for key in FALSE_FIELDS:
            if p.get(key) is not False:
                errors.append(f"{pid}: unapproved {key} assertion")
        for key in ZERO_FIELDS:
            if type(p.get(key)) is not int or p[key] != 0:
                errors.append(f"{pid}: no external outcomes may be claimed")
        if p.get("decision_threshold") is not None or p.get("sample_size_target") is not None:
            errors.append(f"{pid}: numerical decision thresholds/sample sizes require separate approved preregistration")
        if p.get("protocol_execution_status") != "NOT_RUN":
            errors.append(f"{pid}: research protocols cannot self-certify execution")
    if linked != DECISIONS:
        errors.append("research decision coverage incomplete")
    if len(seen) != 6:
        errors.append("duplicate or missing protocol identities")
    if study_types != STUDY_TYPES:
        errors.append("all six distinct research methods required")
    return errors


def build_protocol_report(*, as_of: date, decisions: dict | None = None,
                          book: dict | None = None) -> dict:
    """Only produce a design-review queue; never a trial verdict."""
    if decisions is None:
        _, decisions = run_mission(as_of=as_of)
    if book is None:
        book = json.loads(BOOK.read_text(encoding="utf-8"))
    errors = validate_protocols(book, decisions, as_of=as_of)
    if errors:
        raise ValueError("INVALID_VALIDATION_PROTOCOLS: " + "; ".join(errors))
    decision_by_id = {d["id"]: d for d in decisions["decisions"]}
    protocols = []
    for p in book["experiments"]:
        decision = decision_by_id[p["decision_id"]]
        blockers = [
            "NO_RESEARCH_STUDY_OR_INDEPENDENT_CUSTOMER_OUTCOME_RECORDED",
            "STUDY_PERMISSIONS_AND_DATA_RIGHTS_NOT_GRANTED",
            "SAMPLE_SIZE_AND_DECISION_THRESHOLDS_NOT_PREAPPROVED",
            "BLIND_OR_INDEPENDENT_ADJUDICATION_NOT_EXECUTED",
        ]
        if decision.get("research_blocked_claim_ids"):
            blockers.append("DEPENDENT_SOURCE_OBSERVATIONS_STILL_REQUIRE_REVIEW")
        protocols.append({
            "experiment_id": p["experiment_id"],
            "decision_id": p["decision_id"],
            "title": p["name"],
            "study_type": p["study_type"],
            "priority_score_ordinal_not_forecast": decision["priority_score_ordinal_not_forecast"],
            "source_claim_ids": p["dependent_claim_ids"],
            "unresolved_source_claim_ids": decision.get("research_blocked_claim_ids", []),
            "unit_of_analysis": p["unit_of_analysis"],
            "sample_selection": p["sample_selection"],
            "comparison_group": p["comparison_group"],
            "primary_metric": p["primary_metric"],
            "positive_signal_not_approval": p["positive_signal"],
            "negative_signal": p["negative_signal"],
            "confounders": p["confounders"],
            "missingness_policy": p["missingness_policy"],
            "stop_rule": p["stop_rule"],
            "required_evidence": p["required_evidence"],
            "independent_reviewer": p["independent_reviewer"],
            "next_internal_step": p["next_internal_step"],
            "status": "DESIGN_REVIEW_REQUIRED_NOT_EXECUTED",
            "blocking_gates": blockers,
            "actual_sample_count": 0,
            "independently_validated_outcomes": 0,
            "external_actions_allowed": False,
            "can_publish_customer_results": False,
        })
    protocols.sort(key=lambda x: (-x["priority_score_ordinal_not_forecast"], x["decision_id"]))
    report = {
        "schema_version": 1,
        "scope": "LAB14_INTERNAL_STUDY_DESIGN_REVIEW_ONLY",
        "as_of": as_of.isoformat(),
        "protocol_book_sha256": canon_hash(book),
        "opposition_receipt_sha256": decisions["receipt_sha256"],
        "protocol_count": len(protocols),
        "external_studies_executed": 0,
        "observed_customer_outcomes": 0,
        "approved_preregistrations": 0,
        "new_lab_created": False,
        "existing_lab_number": 14,
        "external_actions_allowed": False,
        "public_performance_claims_allowed": False,
        "protocols": protocols,
        "boundary": (
            "Research designs are not empirical evidence, sample-size approvals, "
            "independent verification or authorization to recruit, use customer records, "
            "make legal claims, charge fees, contact carriers or publish marketing results."
        ),
    }
    report["receipt_sha256"] = canon_hash(report)
    return report


def render_html(report: dict) -> str:
    cards = []
    for p in report["protocols"]:
        metric = p["primary_metric"]
        confounders = "".join("<li>" + escape(x) + "</li>" for x in p["confounders"])
        required = "".join("<li>" + escape(x) + "</li>" for x in p["required_evidence"])
        blockers = "".join("<li>" + escape(x.replace("_", " ").lower()) + "</li>" for x in p["blocking_gates"])
        cards.append(
            '<article><small>' + escape(p["experiment_id"]) +
            " · opposition " + escape(p["decision_id"]) +
            ' · ordinal priority ' + str(p["priority_score_ordinal_not_forecast"]) +
            '</small><h2>' + escape(p["title"]) + '</h2><p><b>Unit:</b> ' +
            escape(p["unit_of_analysis"]) + '</p><p><b>Sampling:</b> ' +
            escape(p["sample_selection"]) + '</p><p><b>Comparator:</b> ' +
            escape(p["comparison_group"]) + '</p><p><b>Primary measure:</b> ' +
            escape(metric["name"]) + ' (' + escape(metric["unit"]) + ')</p>' +
            '<p><b>Numerator:</b> ' + escape(metric["numerator"]) +
            '</p><p><b>Denominator:</b> ' + escape(metric["denominator"]) +
            '</p><p><b>What could disprove it?</b> ' + escape(p["negative_signal"]) +
            '</p><h3>Bias and missing-data review</h3><ul>' + confounders +
            '</ul><p>' + escape(p["missingness_policy"]) +
            '</p><h3>Evidence needed</h3><ul>' + required +
            '</ul><h3>Blocking approvals</h3><ul>' + blockers +
            '</ul><p><b>Next internal step:</b> ' + escape(p["next_internal_step"]) +
            '</p></article>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Validation Protocols</title><style>'
        '*{box-sizing:border-box}body{margin:0;background:#f5f8f6;color:#172e27;'
        'font:15px/1.6 system-ui,-apple-system,sans-serif}main{max-width:1100px;'
        'margin:0 auto;padding:28px 18px 72px}h1{font-size:clamp(30px,5vw,50px);'
        'letter-spacing:-.04em;line-height:1.1}h2{font-size:23px;line-height:1.25}'
        'small{font-size:12px;color:#60736a}article{border:1px solid #dce7e0;'
        'border-radius:15px;background:white;margin:20px 0;padding:22px}'
        'b{color:#145e3e}h3{font-size:15px;margin-bottom:0}li{padding:3px 0}'
        '.eyebrow{text-transform:uppercase;letter-spacing:.14em;color:#146c48;'
        'font-size:12px;font-weight:700}</style></head><body><main>'
        '<div class="eyebrow">RETALLY / RESEARCH LAB 14 / MISSION 7</div>'
        '<h1>Prove it or disprove it.</h1>'
        '<p>Six linked, not-yet-approved study designs. Zero independent customer '
        'outcomes. No external testing, pricing change or public performance claim '
        'is authorized. Scores rank internal research effort only.</p>' +
        "".join(cards) +
        '<footer><small>Internal evidence-research artifact · Receipt SHA-256: ' +
        escape(report["receipt_sha256"]) + '</small></footer></main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date", type=date.fromisoformat,
                        default=date.today())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = build_protocol_report(as_of=args.as_of_date)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "validation_protocols.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "validation_protocols.html").write_text(
        render_html(report), encoding="utf-8"
    )
    print(json.dumps({"protocol_count": report["protocol_count"],
                      "external_studies": report["external_studies_executed"],
                      "receipt": report["receipt_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
