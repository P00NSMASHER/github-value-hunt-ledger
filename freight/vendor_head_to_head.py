"""Read-only, same-population head-to-head audit comparison for RETALLY.

Extends (does not replace) the existing Blind Audit Acceptance Protocol v2.
Competitor output is required from an authorized test; a public API description,
marketing result, or inaccessible private repository is NOT a vendor trial.
No customer records, invoice IDs, private paths, or credentials are exported.
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from freight.audit_acceptance import build_report

VENDORS = (
    "RecoveryOS",
    "Intelligent Audit",
    "Trax",
    "Cass Information Systems",
    "Loop",
    "nVision Global",
)
STUDY_KINDS = {"SYNTHETIC", "BUYER_AUTHORIZED_BLIND"}
SOURCE_KINDS = {"SYNTHETIC_TEST", "AUTHORIZED_VENDOR_EXPORT", "AUTHORIZED_VENDOR_DEMO"}
_SHA = re.compile(r"^[0-9a-f]{64}$")
TRUTH_KEYS = (
    "case_id", "stratum_key", "truth_label", "truth_variance_cents",
    "authority_state", "source_complete", "economic_issue_id",
    "truth_incumbent_known", "reviewer_a_label", "reviewer_b_label",
    "adjudication_note",
)


class ComparisonInvalid(ValueError):
    """The frozen study or a vendor submission is not comparable."""


def _strict_sha(value: Any) -> bool:
    return isinstance(value, str) and bool(_SHA.fullmatch(value))


def _case_truth_signature(pilot: dict) -> tuple:
    cases = pilot["cases"]
    return tuple(
        tuple(case.get(key) for key in TRUTH_KEYS)
        for case in sorted(cases, key=lambda c: c["case_id"])
    )


def _same_study_signature(pilot: dict) -> tuple:
    p = pilot["population"]
    timeline = pilot["timeline"]
    return (
        p["population_hash"], p["sample_hash"], p["truth_manifest_hash"],
        p["incumbent_output_hash"], p["population_size"], p["sample_size"],
        pilot["protocol_id"], pilot["sampling"]["method"],
        pilot["sampling"].get("seed"),
        tuple(sorted(
            (s["key"], s["population_count"], s["sample_target"])
            for s in pilot["sampling"]["strata"]
        )),
        timeline["population_frozen_at"], timeline["truth_frozen_at"],
        timeline["joint_unseal_at"], timeline["incumbent_output_frozen_at"],
        tuple(pilot["roles"].get(k) for k in (
            "truth_owner_id", "reviewer_a_id", "reviewer_b_id",
        )),
        _case_truth_signature(pilot),
    )


def _case_exactness(pilot: dict) -> dict:
    adjudicated = [
        c for c in pilot["cases"] if c["truth_label"] in ("POSITIVE", "NEGATIVE")
    ]
    exact = sum(
        c["predicted_label"] == c["truth_label"]
        and c["predicted_variance_cents"] == c["truth_variance_cents"]
        for c in adjudicated
    )
    abstained = sum(c["predicted_label"] == "REVIEW" for c in adjudicated)
    unresolved = [
        c for c in pilot["cases"] if c["truth_label"] == "UNRESOLVED"
    ]
    safe_unresolved = sum(
        c["predicted_label"] == "REVIEW" for c in unresolved
    )
    return {
        "adjudicated_cases": len(adjudicated),
        "fully_correct_invoice_amount_cases": exact,
        "end_to_end_exact_rate": exact / len(adjudicated) if adjudicated else None,
        "review_on_adjudicated_cases": abstained,
        "unresolved_truth_cases": len(unresolved),
        "safe_unresolved_reviews": safe_unresolved,
    }


def compare_vendor_study(study: dict, policy: dict) -> dict:
    """Compare independently frozen Protocol-v2 vendor runs, not marketing claims.

    This intentionally outputs aggregate results only. A 'sample leader' is
    never called the best product in the market; real recovery, cost, security,
    all-mode coverage and integrations remain separate commercial evidence.
    """
    if not isinstance(study, dict) or study.get("schema_version") != 1:
        raise ComparisonInvalid("head-to-head study schema_version must be 1")
    kind = study.get("study_kind")
    if kind not in STUDY_KINDS:
        raise ComparisonInvalid("study kind must be explicit")
    submissions = study.get("submissions")
    if not isinstance(submissions, list) or len(submissions) > len(VENDORS):
        raise ComparisonInvalid("submissions must be a bounded list")

    seen: set[str] = set()
    reports: dict[str, dict] = {}
    reference: tuple | None = None
    reference_truth: tuple | None = None

    for entry in submissions:
        if not isinstance(entry, dict):
            raise ComparisonInvalid("submission must be an object")
        name = entry.get("vendor")
        if name not in VENDORS or name in seen:
            raise ComparisonInvalid("unsupported or duplicate vendor")
        seen.add(name)
        provenance = entry.get("source_kind")
        if provenance not in SOURCE_KINDS:
            raise ComparisonInvalid("explicit vendor-output source kind required")
        if kind == "BUYER_AUTHORIZED_BLIND" and provenance == "SYNTHETIC_TEST":
            raise ComparisonInvalid("synthetic output is not buyer-authorized evidence")
        if not _strict_sha(entry.get("output_receipt_sha256")):
            raise ComparisonInvalid("source output receipt must be lowercase SHA-256")

        pilot = entry.get("pilot")
        if not isinstance(pilot, dict):
            raise ComparisonInvalid("full frozen Protocol-v2 pilot packet required")
        try:
            report = build_report(pilot, policy)
        except (ValueError, KeyError, TypeError) as exc:
            # Never echo buyer IDs, case labels, private paths or packet content.
            raise ComparisonInvalid("invalid or unverified Protocol-v2 packet") from None
        signature = _same_study_signature(pilot)
        truth = _case_truth_signature(pilot)
        if reference is None:
            reference = signature
            reference_truth = truth
        elif signature != reference or truth != reference_truth:
            raise ComparisonInvalid(
                "vendors were not scored on identical frozen population and truth"
            )

        metrics = report["metrics"]
        reports[name] = {
            "vendor": name,
            "observation": "SYNTHETIC_ONLY" if provenance == "SYNTHETIC_TEST"
                else "VENDOR_OUTPUT_SUBMITTED_NOT_INDEPENDENTLY_ATTESTED",
            "methodology_status": report["status"],
            "failed_acceptance_gates": list(report["failed_gates"]),
            "exactness": _case_exactness(pilot),
            "classification": {
                "true_positive": metrics["classification"]["true_positive"],
                "true_negative": metrics["classification"]["true_negative"],
                "false_positive": metrics["classification"]["false_positive"],
                "false_negative": metrics["classification"]["false_negative"],
            },
            "auto_coverage": metrics["sample"]["auto_coverage"],
            "review_rate": metrics["sample"]["review_rate"],
            "auto_exact_dollar_rate": metrics["dollars"]["auto_exact_dollar_rate"],
            "incumbent_credit_leakage_cents": metrics["dollars"]["incumbent_credit_leakage_cents"],
            "duplicate_net_new_leakage_cents": metrics["dollars"]["duplicate_net_new_leakage_cents"],
            "unverified_receipt_sha256": entry["output_receipt_sha256"],
        }

    missing = tuple(v for v in VENDORS if v not in seen)
    full = len(reports) == len(VENDORS)
    independent = kind == "BUYER_AUTHORIZED_BLIND" and all(
        entry["source_kind"] != "SYNTHETIC_TEST" for entry in submissions
    )
    proof_sufficient = full and independent and all(
        row["methodology_status"] == "AUDIT_QUALITY_PROVEN"
        for row in reports.values()
    )
    # This comparison scores only the same population. It never establishes
    # universal superiority or external bank/security certification.
    sample_leaders = []
    if proof_sufficient:
        rates = {v: row["exactness"]["end_to_end_exact_rate"] for v, row in reports.items()}
        if all(rate is not None for rate in rates.values()):
            high = max(rates.values())
            sample_leaders = [v for v in VENDORS if rates[v] == high]

    return {
        "schema_version": 1,
        "study_kind": kind,
        "comparison_status": (
            "NO_VENDOR_MEASUREMENTS" if not reports else
            "INCOMPLETE_VENDOR_COVERAGE" if missing else
            "SYNTHETIC_REHEARSAL_ONLY" if not independent else
            "SAMPLE_COMPARISON_READY" if proof_sufficient else
            "METHOD_OR_ACCEPTANCE_GATES_NOT_MET"
        ),
        "observed_vendor_count": len(reports),
        "missing_vendors": list(missing),
        "vendor_results": [reports[v] for v in VENDORS if v in reports],
        "sample_leaders_if_independently_proven": sample_leaders,
        "market_best_product_proven": False,
        "verified_realized_recovery": False,
        "source_code_access_inferred": False,
        "claim_boundary": (
            "Public GitHub repositories and API schemas are capability evidence, not a vendor's production source.",
            "Vendor-reported accuracy cannot be compared with a different dataset.",
            "No vendor without a same-population authorized result receives a zero or ranking.",
            "Private competitor source requires owner-granted access; read access alone does not grant reuse rights.",
            "Identical study packets and reported output-receipt hashes are necessary, not sufficient to authenticate a vendor.",
            "This benchmark tests audit accuracy on one population, not overall security, integrations, service scale or market leadership.",
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only RETALLY independent vendor benchmark.")
    parser.add_argument("--study", required=True, help="Local, authorized private study JSON")
    parser.add_argument("--policy", default="freight/AUDIT_ACCEPTANCE_POLICY_V2.json")
    args = parser.parse_args()
    try:
        study = json.loads(Path(args.study).read_text(encoding="utf-8"))
        policy = json.loads(Path(args.policy).read_text(encoding="utf-8"))
        result = compare_vendor_study(study, policy)
    except (ComparisonInvalid, OSError, ValueError, TypeError, KeyError):
        parser.exit(2, "Vendor comparison invalid or private input unavailable; no results released.\n")
    # All case-level customer data stays local; stdout contains aggregate rows.
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
