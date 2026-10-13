"""RETALLY Lab 14 / M40: independent disposition of historical lab findings.

Only a frozen register, a semantically checked local experiment ledger and
explicitly UNVERIFIED per-case classifications. A self-asserted 'repair'
receipt is NOT a reproduced old counterexample, an independently reviewed
patch, closed historical finding, real customer evidence or deployment right.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import date
from hashlib import sha1
from html import escape
import json
from pathlib import Path

from freight.lab_assurance import digest
from freight.lab_experiment_ledger import ExperimentLedger

BOOK = Path(__file__).parent / "research/LAB_FINDINGS_CUMULATIVE.json"
BOOK_GIT_BLOB_SHA1 = "8a97b74432b82b34468bbb57cbc14d869258b77c"
SCOPE = "RETALLY_LAB14_M40_FROZEN_FINDING_LEDGER_AUDIT_NO_AUTOMATIC_CLOSURE"
LOCAL_REPAIR = "REPAIR_DEMONSTRATED_IN_STATED_TEST_SCOPE_ONLY"
DECLARATIONS = {
    "INCONCLUSIVE",
    "DEFECT_STILL_REPRODUCED",
    LOCAL_REPAIR,
}
GATE_IDS = ("GATE-001", "GATE-002")


def _git_blob(raw: bytes) -> str:
    return sha1(b"blob " + str(len(raw)).encode("ascii") + b"\0" + raw).hexdigest()


def _book() -> dict:
    raw = BOOK.read_bytes()
    if _git_blob(raw) != BOOK_GIT_BLOB_SHA1:
        raise ValueError("M40_FROZEN_HISTORICAL_FINDING_REGISTER_CHANGED")
    book = json.loads(raw.decode("utf-8"))
    if (type(book) is not dict or book.get("schema_version") != 1
        or book.get("status") != "RELEASE_FINANCIAL_ASSURANCE_BLOCKED"
        or book.get("historical_open_findings") != 26
        or book.get("new_research_gate_findings") != 2
        or book.get("entries_total") != 28
        or book.get("first_audit_entries") != 8
        or book.get("second_audit_entries") != 18):
        raise ValueError("M40_HISTORICAL_FINDING_COUNTS_OR_RELEASE_SCOPE_CHANGED")
    rows = book.get("entries")
    if type(rows) is not list or len(rows) != 28:
        raise ValueError("M40_MISSING_REGISTERED_ORIGINAL_FINDING")
    ids = [x.get("id") if type(x) is dict else None for x in rows]
    if len(set(ids)) != 28 or ids[-2:] != list(GATE_IDS):
        raise ValueError("M40_FINDING_IDENTITIES_CHANGED_OR_REORDERED")
    expected_clusters = Counter(x["root_cause_cluster"] for x in rows)
    if expected_clusters != book.get("cluster_counts"):
        raise ValueError("M40_FINDING_CLUSTER_COUNTS_CHANGED")
    for row in rows[:-2]:
        if (row.get("remediation") != "OPEN_UNVERIFIED"
            or row.get("evidence") != "REPRODUCED_OFFLINE_PRIOR_AUDIT"
            or row.get("customer_or_production_impact") != "NOT_ESTABLISHED"):
            raise ValueError("M40_OLD_FINDINGS_FALSELY_MARKED_CLOSED")
    for row in rows[-2:]:
        if (row["remediation"] != "FIXED_AND_REGRESSION_TESTED_RESEARCH_GATE_ONLY"
            or row["evidence"] != "REPRODUCED_AND_REPAIRED_IN_STANDALONE_RESEARCH_GATE"
            or row["root_cause_cluster"] != "release-gate-signal-integrity"):
            raise ValueError("M40_RESEARCH_GATE_ONLY_FIX_MISREPORTED_AS_RECOVERYOS")
    return book


def audit(*, ledger_path: str | Path) -> dict:
    book = _book()
    path = Path(ledger_path)
    if not path.is_file():
        raise ValueError("M40_LOCAL_EXPERIMENT_LEDGER_MISSING")
    records = ExperimentLedger(path).read_and_verify()
    entries = book["entries"]
    known = {x["id"] for x in entries}
    by_finding: dict[str, list[dict]] = {x["id"]: [] for x in entries}
    seen_experiments: set[str] = set()
    for record in records:
        finding_id = record["finding_id"]
        if finding_id not in known:
            raise ValueError("M40_UNREGISTERED_FINDING_ADDED_TO_LEDGER")
        if record["experiment_id"] in seen_experiments:
            raise ValueError("M40_DUPLICATE_EXPERIMENT_ID")
        seen_experiments.add(record["experiment_id"])
        if record["verdict"] not in DECLARATIONS:
            raise ValueError("M40_UNSUPPORTED_LOCAL_DISPOSITION")
        by_finding[finding_id].append(record)
    repaired_claims = [r for r in records if r["verdict"] == LOCAL_REPAIR]
    rows = []
    for finding in entries[:26]:
        history = by_finding[finding["id"]]
        last = history[-1] if history else None
        rows.append({
            "finding_id": finding["id"],
            "severity": finding["severity"],
            "root_cause_cluster": finding["root_cause_cluster"],
            "historical_evidence": "REPRODUCED_OFFLINE_PRIOR_AUDIT",
            "status": "OPEN_UNVERIFIED",
            "unproven_customer_or_production_impact": True,
            "experiment_records": len(history),
            "latest_local_declaration_not_independently_attested":
                last["verdict"] if last else None,
            "local_repair_asserted_but_not_approved":
                any(x["verdict"] == LOCAL_REPAIR for x in history),
            "original_counterexample_replayed_in_this_audit": False,
            "independent_baseline_and_candidate_bytes_verified": False,
            "historical_defect_closed": False,
        })
    if len(rows) != 26 or any(x["historical_defect_closed"] for x in rows):
        raise ValueError("M40_UNAUTHORIZED_HISTORICAL_DEFECT_CLOSURE")
    gate = [
        {
            "finding_id": x["id"],
            "recorded_status": "RESEARCH_GATE_ONLY_FIXED_NOT_RECOVERYOS",
            "local_experiment_records": len(by_finding[x["id"]]),
            "represents_historical_RecoveryOS_repair": False,
        }
        for x in entries[-2:]
    ]
    answer = {
        "schema_version": 1,
        "scope": SCOPE,
        "existing_lab_number": 14,
        "new_lab_created": False,
        "original_historical_findings": 26,
        "original_historical_findings_open": 26,
        "original_historical_findings_closed_by_local_reports": 0,
        "additional_research_gate_only_fixed_items": 2,
        "all_registered_items_including_gate_corrections": 28,
        "local_experiments_recorded": len(records),
        "distinct_original_findings_with_experiments":
            sum(bool(by_finding[x["id"]]) for x in entries[:26]),
        "local_repair_assertions_not_attested": len(repaired_claims),
        "original_counterexamples_independently_reproduced_in_this_audit": 0,
        "independent_regression_or_repair_signoffs": 0,
        "real_customer_pilot_invoices_seen": 0,
        "independent_customer_human_pilot_gates_unmet": 18,
        "external_publication_authority": False,
        "real_customer_recovery_or_fee_established": False,
        "release_status": "BLOCKED_PENDING_INDEPENDENT_ORIGINAL_DEFECT_REPRODUCTION",
        "original_finding_register_git_blob_sha1": BOOK_GIT_BLOB_SHA1,
        "original_finding_register_sha256": digest(book),
        "ledger_last_local_receipt_sha256":
            records[-1]["receipt_sha256"] if records else None,
        "historical_findings": rows,
        "separate_research_gate_corrections": gate,
        "no_customer_data_import_contact_deployment_or_schedule": True,
        "caveat": (
            "A locally consistent experiment hash chain is not an independent "
            "reproducer or authoritative original bug closure. An all-true "
            "Experiment payload can declare a repair in its stated test scope "
            "but supplies no original frozen baseline/candidate bytes or "
            "separate human verification. Every one of 26 historical "
            "RecoveryOS findings remains OPEN_UNVERIFIED. The two earlier "
            "research-gate-only fixes do not repair RecoveryOS. Do not use "
            "source reports, synthetic invoices or local CI as proof of actual "
            "customer refunds, contract authority or marketable performance."
        ),
    }
    answer["receipt_sha256"] = digest(answer)
    return answer


def render_html(report: dict) -> str:
    rows = "".join(
        "<tr><th>" + escape(item["finding_id"]) +
        "</th><td>" + escape(item["severity"]) +
        "</td><td>" + escape(item["root_cause_cluster"]) +
        "</td><td>" + str(item["experiment_records"]) +
        "</td><td>OPEN — unverified</td></tr>"
        for item in report["historical_findings"]
    )
    return (
        '<!doctype html><html lang="en"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1">'
        '<title>RETALLY | Historical finding disposition</title>'
        '<style>body{font:15px/1.5 system-ui;background:#f5f7f4;'
        'color:#1b3428;max-width:1100px;margin:auto;padding:24px}'
        'table{width:100%;border-collapse:collapse;background:white}'
        'td,th{text-align:left;border-bottom:1px solid #dfebdf;padding:10px}'
        'small{color:#65746c}</style></head><body>'
        '<small>RETALLY / LAB 14 / M40 / RESEARCH-ONLY</small>'
        '<h1>Repair claims are not defect closure.</h1>'
        '<p>Original historical findings: <strong>26 open / 0 closed</strong>. '
        'The two independently identified research-gate fixes are separate.'
        ' Local experiment assertions: <strong>' +
        str(report["local_experiments_recorded"]) +
        '</strong>, self-declared repairs needing independent proof: <strong>' +
        str(report["local_repair_assertions_not_attested"]) +
        '</strong>. No original counterexample bytes independently replayed, '
        'no real customer settlements, no public claim authority.</p>'
        '<table><thead><tr><th>ID</th><th>Severity</th><th>Cluster</th>'
        '<th>Local entries</th><th>Original status</th></tr></thead>'
        '<tbody>' + rows + '</tbody></table><p><small>' +
        escape(report["caveat"]) + '</small></p></body></html>'
    )


def main() -> None:
    ap = argparse.ArgumentParser(description="Offline original-finding disposition audit")
    ap.add_argument("--ledger", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()
    report = audit(ledger_path=args.ledger)
    args.out.mkdir(parents=True, exist_ok=True)
    (args.out / "historical_finding_disposition.json").write_text(
        json.dumps(report, sort_keys=True, indent=2) + "\n", encoding="utf-8"
    )
    (args.out / "historical_finding_disposition.html").write_text(
        render_html(report), encoding="utf-8"
    )
    print(json.dumps({
        "historical_original_open": 26,
        "original_automatically_closed": 0,
        "experiment_records": report["local_experiments_recorded"],
        "unattested_local_repair_assertions":
            report["local_repair_assertions_not_attested"],
        "external_authority": False,
        "receipt_sha256": report["receipt_sha256"],
    }, sort_keys=True))


if __name__ == "__main__":
    main()
