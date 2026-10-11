"""RETALLY Lab 14 Mission 8: offline failure-mode rehearsals with INVENTED data.

Never use customer files, private competitor code, real shipments, requests,
network services, authorization or money. Metric arithmetic tested here cannot
validate the business hypothesis, grant approval or establish real-world outcomes.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from datetime import date
from html import escape
import json
from pathlib import Path
import re

from freight.research_evidence_gate import canon_hash
from freight.research_validation_protocols import build_protocol_report

ROOT = Path(__file__).resolve().parent
FIXTURES = ROOT / "research" / "SYNTHETIC_REHEARSALS_20261010.json"
SCOPE = "RETALLY_LAB14_EXPLICITLY_INVENTED_SYNTHETIC_REHEARSALS"
PROTOCOL_IDS = {f"M7-0{i}" for i in range(1, 7)}
ID_PATTERN = re.compile(r"^SIM-0[1-6]-[0-9]{2}$")
AMOUNT_FIELDS = ("cash_fee_collected_cents", "carrier_credit_cents",
                 "fee_refunds_cents", "labor_cents", "acquisition_cents",
                 "processing_cents", "writeoffs_cents")
BASE_FIELDS = {"protocol_id", "case_id"}
FIELDS = {
    "M7-01": BASE_FIELDS | {"alert", "adjudication"},
    "M7-02": BASE_FIELDS | {"shipment_on", "synthetic_effective_on",
                          "authority_available", "contract_override", "engine_decision"},
    "M7-03": BASE_FIELDS | {"arm", "response"},
    "M7-04": BASE_FIELDS | {"frame_status"},
    "M7-05": BASE_FIELDS | {"fixture_id", "system", "access", "resolution"},
    "M7-06": BASE_FIELDS | {"case_state"} | set(AMOUNT_FIELDS),
}
EXPECTED_STUDIES = {
    "M7-01": "BLINDED_REFERENCE_ADJUDICATION",
    "M7-02": "TEMPORAL_BOUNDARY_REGRESSION",
    "M7-03": "CONTROLLED_RANDOMIZED_SURVEY",
    "M7-04": "STRATIFIED_ACCOUNT_SAMPLE",
    "M7-05": "COMMON_FIXTURE_COMPARISON",
    "M7-06": "RECONCILED_COHORT_ACCOUNTING",
}
TOP_KEYS = {"schema_version", "scope", "created_on", "data_origin",
            "synthetic_only", "external_source_records", "human_respondents",
            "real_carrier_or_customer_records", "external_actions_authorized",
            "purpose", "cases"}


def _iso(value: object) -> date:
    if type(value) is not str:
        raise ValueError("date must be an ISO date string")
    result = date.fromisoformat(value)
    if result.isoformat() != value:
        raise ValueError("noncanonical ISO date")
    return result


def _fraction(numerator: int, denominator: int) -> dict:
    """Keep exact integer counts rather than misleading rounded percentages."""
    return {"numerator": numerator, "denominator": denominator,
            "fraction": f"{numerator}/{denominator}" if denominator else None}


def _boolean(v: object) -> bool:
    return type(v) is bool


def _error(errors: list[str], ident: str, message: str) -> None:
    errors.append(f"{ident}: {message}")


def validate_fixture_book(book: dict, protocol_report: dict, *, as_of: date) -> list[str]:
    errors: list[str] = []
    if type(book) is not dict:
        return ["fixture document must be object"]
    if set(book) != TOP_KEYS:
        errors.append("fixture document keys not exactly recognized; no external metadata")
    if type(book.get("schema_version")) is not int or book["schema_version"] != 1:
        errors.append("invalid fixture schema")
    if book.get("scope") != SCOPE:
        errors.append("wrong synthetic-only scope")
    try:
        if _iso(book.get("created_on")) > as_of:
            errors.append("rehearsal book recorded in future")
    except ValueError:
        errors.append("invalid fixture creation date")
    if book.get("data_origin") != "HAND_AUTHORED_FICTITIOUS_CASES_NOT_MODELLED_FROM_CUSTOMERS":
        errors.append("invented-data provenance declaration missing")
    if book.get("synthetic_only") is not True or book.get("external_actions_authorized") is not False:
        errors.append("rehearsals must prohibit real or external execution")
    for key in ("external_source_records", "human_respondents",
                "real_carrier_or_customer_records"):
        if type(book.get(key)) is not int or book[key] != 0:
            errors.append(f"{key} must be exact integer zero")
    if type(book.get("purpose")) is not str or len(book["purpose"]) < 60:
        errors.append("explicit invented-case disclaimer required")
    if (type(protocol_report) is not dict or
        protocol_report.get("scope") != "LAB14_INTERNAL_STUDY_DESIGN_REVIEW_ONLY" or
        protocol_report.get("external_studies_executed") != 0 or
        protocol_report.get("public_performance_claims_allowed") is not False):
        return errors + ["original Mission 7 blocked protocol report required"]
    original_protocols = protocol_report.get("protocols")
    if type(original_protocols) is not list or len(original_protocols) != 6:
        return errors + ["all six validated Mission 7 protocols required"]
    try:
        declared = {p["experiment_id"]: p["study_type"] for p in original_protocols}
    except (KeyError, TypeError):
        return errors + ["malformed Mission 7 study bindings"]
    if declared != EXPECTED_STUDIES:
        errors.append("study methods must exactly match existing protocol register")
    cases = book.get("cases")
    if type(cases) is not list or not 20 <= len(cases) <= 90:
        return errors + ["bounded set of at least 20 synthetic cases required"]
    seen = set()
    cohort: dict[str, list[dict]] = defaultdict(list)
    for i, row in enumerate(cases):
        if type(row) is not dict:
            _error(errors, str(i), "synthetic case object required")
            continue
        pid = row.get("protocol_id")
        cid = row.get("case_id")
        if type(pid) is not str or pid not in PROTOCOL_IDS:
            _error(errors, str(i), "unknown protocol")
            continue
        if type(cid) is not str or not ID_PATTERN.fullmatch(cid) or cid[4:6] != pid[3:]:
            _error(errors, str(i), "non-invented or mismatched case identifier")
            continue
        if cid in seen:
            _error(errors, cid, "duplicate case; double-counting prohibited")
            continue
        seen.add(cid)
        if set(row) != FIELDS[pid]:
            _error(errors, cid, "unexpected or missing keys; no customer data accepted")
            continue
        cohort[pid].append(row)
        if pid == "M7-01":
            if not _boolean(row["alert"]) or row["adjudication"] not in {
                "SUBSTANTIATED", "NOT_SUBSTANTIATED", "UNRESOLVED"}:
                _error(errors, cid, "invalid alert or independent adjudication")
        elif pid == "M7-02":
            if not _boolean(row["authority_available"]) or not _boolean(row["contract_override"]):
                _error(errors, cid, "invalid availability or signed-contract scenario")
            if row["engine_decision"] not in {"APPLY", "IGNORE", "HOLD"}:
                _error(errors, cid, "invalid rule engine decision")
            try:
                ship = _iso(row["shipment_on"])
                effective = _iso(row["synthetic_effective_on"])
                if effective.year < 2029 or ship.year < 2028:
                    _error(errors, cid, "hypothetical dates must not impersonate historical observed shipments")
            except ValueError:
                _error(errors, cid, "malformed temporal fixture")
        elif pid == "M7-03":
            if row["arm"] not in {"POSTED", "NEGOTIATED"} or row["response"] not in {
                "CORRECT", "INCORRECT", "NONRESPONSE"}:
                _error(errors, cid, "invalid randomization or survey response")
        elif pid == "M7-04":
            if row["frame_status"] not in {"QUALIFIED", "INELIGIBLE", "NONRESPONSE", "UNKNOWN"}:
                _error(errors, cid, "invalid sampled-frame state")
        elif pid == "M7-05":
            if row["system"] not in {"RETALLY", "OTHER_LICENSED_VENDOR"}:
                _error(errors, cid, "unknown or real competitor identity")
            if type(row["fixture_id"]) is not str or not re.fullmatch(r"SIM-C[0-9]{2}", row["fixture_id"]):
                _error(errors, cid, "unapproved fixture identifier")
            if row["access"] not in {"AUTHORIZED", "NOT_TESTED"} or row["resolution"] not in {
                "SUPPORTED_CORRECT", "INCORRECT", "ABSTAIN", "NOT_TESTED"}:
                _error(errors, cid, "invalid capability run state")
            elif (row["access"] == "NOT_TESTED") != (row["resolution"] == "NOT_TESTED"):
                _error(errors, cid, "missing vendor access cannot become a zero-score test")
        elif pid == "M7-06":
            if row["case_state"] not in {"RECOVERED", "ZERO_RECOVERY", "REVERSED", "PENDING"}:
                _error(errors, cid, "invalid financial case state")
            if any(type(row[k]) is not int or not 0 <= row[k] <= 100000000 for k in AMOUNT_FIELDS):
                _error(errors, cid, "all cents require bounded nonnegative exact integers")
            else:
                fee = row["cash_fee_collected_cents"]
                refund = row["fee_refunds_cents"]
                state = row["case_state"]
                if (state in {"ZERO_RECOVERY", "PENDING"} and (fee or refund)) or (
                    state == "RECOVERED" and not fee) or (
                    state == "REVERSED" and (not fee or not refund)):
                    _error(errors, cid, "cash chronology inconsistent with fictional episode state")
                if refund > fee:
                    _error(errors, cid, "fee refunds cannot exceed tracked collected fees")
    if set(cohort) != PROTOCOL_IDS or any(len(cohort.get(pid, [])) < 3 for pid in PROTOCOL_IDS):
        errors.append("all six synthetic cohorts require three or more distinct cases")
    arms = Counter(r["arm"] for r in cohort["M7-03"])
    if set(arms) != {"POSTED", "NEGOTIATED"} or any(n < 2 for n in arms.values()):
        errors.append("both fictional randomized survey arms required")
    systems: dict[str, set[str]] = defaultdict(set)
    for row in cohort["M7-05"]:
        fid = row["fixture_id"]
        sys = row["system"]
        if sys in systems[fid]:
            errors.append(f"{fid}: duplicate comparison run for same system")
        systems[fid].add(sys)
    if len(systems) < 2 or any(v != {"RETALLY", "OTHER_LICENSED_VENDOR"} for v in systems.values()):
        errors.append("paired common-fixture comparator coverage required")
    return errors


def _metric(pid: str, rows: list[dict]) -> dict:
    """Compute transparent denominators; never calculate study p-values or ROI."""
    if pid == "M7-01":
        positives = [r for r in rows if r["alert"]]
        supported = sum(r["adjudication"] == "SUBSTANTIATED" for r in positives)
        fp = sum(r["adjudication"] == "NOT_SUBSTANTIATED" for r in positives)
        indeterminate = sum(r["adjudication"] == "UNRESOLVED" for r in positives)
        missed = sum(not r["alert"] and r["adjudication"] == "SUBSTANTIATED" for r in rows)
        return {"metric": "synthetic_supported_alert_fraction_including_unknowns",
                "primary": _fraction(supported, len(positives)),
                "alerts_not_substantiated": fp, "positive_alerts_unresolved": indeterminate,
                "false_negative_reference_cases": missed,
                "selection_warning": "This is alert precision among flagged cases, not recall or invoice accuracy."}
    if pid == "M7-02":
        expected = []
        retroactive = []
        for r in rows:
            sh = _iso(r["shipment_on"])
            eff = _iso(r["synthetic_effective_on"])
            reference = ("HOLD" if not r["authority_available"] else
                         "IGNORE" if sh < eff or r["contract_override"] else "APPLY")
            expected.append(reference)
            if sh < eff and r["engine_decision"] == "APPLY":
                retroactive.append(r["case_id"])
        agreement = sum(x == r["engine_decision"] for x, r in zip(expected, rows))
        return {"metric": "synthetic_temporal_boundary_agreement",
                "primary": _fraction(agreement, len(rows)),
                "future_rule_leakage_case_ids": retroactive,
                "cannot_infer_legal_applicability": True,
                "selection_warning": "All dates and precedence scenarios are fictional; no shipment-specific legal opinion."}
    if pid == "M7-03":
        by_arm = {}
        for arm in ("POSTED", "NEGOTIATED"):
            arm_rows = [r for r in rows if r["arm"] == arm]
            by_arm[arm] = {"comprehension": _fraction(
                sum(r["response"] == "CORRECT" for r in arm_rows), len(arm_rows)),
                "nonresponse_count": sum(r["response"] == "NONRESPONSE" for r in arm_rows)}
        return {"metric": "synthetic_fee_comprehension_all_randomized",
                "primary": _fraction(sum(r["response"] == "CORRECT" for r in rows), len(rows)),
                "arm_breakdown": by_arm, "causal_comparison_authorized": False,
                "selection_warning": "Fictional survey units are NOT people, randomization or observed preferences."}
    if pid == "M7-04":
        status = Counter(r["frame_status"] for r in rows)
        return {"metric": "synthetic_qualified_reachable_share_of_full_frame",
                "primary": _fraction(status["QUALIFIED"], len(rows)),
                "nonresponse": status["NONRESPONSE"], "unknown": status["UNKNOWN"],
                "ineligible": status["INELIGIBLE"],
                "market_extrapolation_authorized": False,
                "selection_warning": "Synthetic shipper counts cannot establish a serviceable market size."}
    if pid == "M7-05":
        by_system = {}
        for system in ("RETALLY", "OTHER_LICENSED_VENDOR"):
            all_rows = [r for r in rows if r["system"] == system]
            tested = [r for r in all_rows if r["access"] == "AUTHORIZED"]
            by_system[system] = {
                "supported_correct": _fraction(sum(
                    r["resolution"] == "SUPPORTED_CORRECT" for r in tested),
                    len(tested)),
                "not_tested": len(all_rows) - len(tested),
                "abstentions": sum(r["resolution"] == "ABSTAIN" for r in tested),
                "denominator_excludes_unlicensed_runs": True}
        return {"metric": "synthetic_supported_resolution_by_authorized_system",
                "by_system": by_system, "head_to_head_ranking_authorized": False,
                "selection_warning": "Unequal access and artificial fixtures prohibit product superiority claims."}
    if pid == "M7-06":
        revenue = sum(r["cash_fee_collected_cents"] for r in rows)
        credit = sum(r["carrier_credit_cents"] for r in rows)
        refunds = sum(r["fee_refunds_cents"] for r in rows)
        costs = sum(sum(r[k] for k in ("labor_cents", "acquisition_cents",
                                     "processing_cents", "writeoffs_cents")) for r in rows)
        net = revenue - refunds - costs
        return {"metric": "synthetic_net_fee_contribution_per_initiated_case_cents",
                "primary": _fraction(net, len(rows)), "net_contribution_cents": net,
                "collected_fee_cents": revenue, "carrier_credit_not_counted_as_cash_cents": credit,
                "fee_refunds_cents": refunds, "attributable_costs_cents": costs,
                "cases_including_zero_pending_and_reversed": len(rows),
                "real_cash_or_bank_data_observed": False,
                "selection_warning": "Carrier credits are not fees collected; zero and reversed cases remain in denominator."}
    raise ValueError("unsupported Mission 7 protocol")


def run_rehearsal(*, as_of: date, book: dict | None = None,
                  protocol_report: dict | None = None) -> dict:
    if protocol_report is None:
        protocol_report = build_protocol_report(as_of=as_of)
    if book is None:
        book = json.loads(FIXTURES.read_text(encoding="utf-8"))
    errors = validate_fixture_book(book, protocol_report, as_of=as_of)
    if errors:
        raise ValueError("INVALID_SYNTHETIC_REHEARSAL: " + "; ".join(errors))
    cohorts = {pid: [] for pid in sorted(PROTOCOL_IDS)}
    for row in book["cases"]:
        cohorts[row["protocol_id"]].append(row)
    output = []
    for pid, rows in cohorts.items():
        outcome = _metric(pid, rows)
        output.append({
            "protocol_id": pid,
            "study_type": EXPECTED_STUDIES[pid],
            "synthetic_case_count": len(rows),
            "only_invented_data": True,
            "test_arithmetic_not_business_hypothesis": True,
            "external_study_completed": False,
            "marketing_result_authorized": False,
            "measure": outcome,
        })
    report = {
        "schema_version": 1,
        "as_of": as_of.isoformat(),
        "scope": "LAB14_SYNTHETIC_ARITHMETIC_AND_DATA_QUALITY_REHEARSAL_ONLY",
        "fixture_sha256": canon_hash(book),
        "protocol_report_sha256": protocol_report["receipt_sha256"],
        "rehearsed_protocols": len(output),
        "invented_case_records": len(book["cases"]),
        "independent_customer_observations": 0,
        "external_studies_executed": 0,
        "human_respondents": 0,
        "production_code_executed": False,
        "new_lab_created": False,
        "lab_number": 14,
        "external_actions_allowed": False,
        "verified_business_results": False,
        "public_claims_authorized": False,
        "rehearsals": output,
        "boundary": (
            "Rehearsals exercise denominator integrity and known synthetic counterexamples. "
            "They do not measure actual RETALLY customer demand, recoveries, market share, "
            "pricing causality, vendor accuracy, cash balance, tariff compliance or legal rights."
        ),
    }
    report["receipt_sha256"] = canon_hash(report)
    return report


def render_html(report: dict) -> str:
    cards = []
    for row in report["rehearsals"]:
        metric = row["measure"]
        if "primary" in metric:
            primary = metric["primary"]["fraction"] or "not defined"
        elif "by_system" in metric:
            primary = ", ".join(f"{sys}: {values['supported_correct']['fraction']}"
                                for sys, values in metric["by_system"].items())
        else:
            primary = "not applicable"
        cards.append(
            '<article><small>' + escape(row["protocol_id"]) + ' · ' +
            escape(row["study_type"].replace("_", " ")) +
            '</small><h2>' + escape(metric["metric"].replace("_", " ").title()) +
            '</h2><p><b>Illustrative fraction:</b> ' + escape(primary) +
            '</p><p><b>Rehearsal cases:</b> ' + str(row["synthetic_case_count"]) +
            '</p><p>' + escape(metric["selection_warning"]) +
            '</p><pre>' + escape(json.dumps(metric, indent=2, sort_keys=True)) +
            '</pre></article>'
        )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Synthetic Research Rehearsal</title><style>'
        '*{box-sizing:border-box}body{margin:0;background:#f5f8f6;'
        'font:15px/1.6 system-ui,-apple-system,sans-serif;color:#1a3229}'
        'main{max-width:1020px;margin:auto;padding:28px 18px 60px}'
        'h1{font-size:clamp(31px,5vw,48px);letter-spacing:-.045em;line-height:1.1}'
        'article{background:#fff;border:1px solid #dae8df;border-radius:16px;'
        'padding:22px;margin:18px 0}h2{font-size:21px;line-height:1.3}'
        'small{letter-spacing:.09em;color:#50705f;font-size:12px}b{color:#187249}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere;font-size:12px;'
        'background:#eff4ef;border-radius:10px;padding:12px}</style></head>'
        '<body><main><small>RETALLY / LAB 14 / MISSION 8 / INVENTED DATA</small>'
        '<h1>Rehearse the failure before trusting the result.</h1>'
        '<p><b>These numbers describe invented test cases, not customer outcomes.</b> '
        'No recruitment, outside source verification, legal clearance or financial '
        'activity has occurred. No statistically valid inference is possible.</p>' +
        "".join(cards) +
        '<footer><small>Fixture receipt (not external truth): ' +
        escape(report["receipt_sha256"]) + '</small></footer></main></body></html>'
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--as-of-date", type=date.fromisoformat, default=date.today())
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    report = run_rehearsal(as_of=args.as_of_date)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "synthetic_rehearsals.json").write_text(
        json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    (args.out / "synthetic_rehearsals.html").write_text(
        render_html(report), encoding="utf-8"
    )
    print(json.dumps({"rehearsed_protocols": report["rehearsed_protocols"],
                      "invented_cases": report["invented_case_records"],
                      "external_studies": report["external_studies_executed"],
                      "receipt": report["receipt_sha256"]}, sort_keys=True))


if __name__ == "__main__":
    main()
