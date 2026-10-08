"""Read-only executive triage of the pinned synthetic laboratory finding register.

No product scans, system modifications, external calls, or real money impacts.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from freight.lab_intelligence import ExperimentCandidate, prioritize_experiments

ROOT = Path(__file__).resolve().parent
CLUSTER_PLAN = {
    "state-journal-replay": ((2, 5, 8, 11), 12, "replay money against separate source/receipt proofs"),
    "source-entitlement": ((1, 4, 6), 16, "reject foreign source and altered invoice ownership"),
    "blind-prediction-oracle": ((1, 3, 12), 12, "run held-out blind truth and wrongful-claim checks"),
    "authorization-fee-terms": ((2, 5, 8), 14, "bind fees to signed historical terms and revocation rules"),
    "partial-allocations-reversals": ((2, 5, 8), 16, "reconcile split credits, reversals and receivables"),
    "identity-display-namespace": ((2, 6), 6, "keep distinct canonical customer/source identities"),
    "external-effect-idempotency": ((2, 5, 11), 10, "simulate timeout, ambiguous provider response and actor replay"),
    "model-metric-integrity": ((8, 11, 13), 8, "reject impossible metrics and retain negative modeled margins"),
    "evidence-source-admission": ((3, 10, 14), 8, "independently verify primary evidence and source claims"),
    "release-completeness": ((4, 11), 10, "cold-restore exact required archive population"),
    "release-gate-signal-integrity": ((6, 11), 6, "require fail-closed exit code and known-good positive control"),
}


def make_control_room(register: dict, *, limit: int | None = None) -> dict:
    rows = register["entries"]
    if not isinstance(rows, list):
        raise ValueError("finding entries must be a list")
    original = [r for r in rows if r["remediation"] == "OPEN_UNVERIFIED"]
    if len({r["id"] for r in rows}) != len(rows):
        raise ValueError("duplicate finding identity")
    if len(original) != register["historical_open_findings"]:
        raise ValueError("historical finding count inconsistent")
    if len(rows) != register["entries_total"]:
        raise ValueError("cumulative finding count inconsistent")
    candidates = []
    indexed = {}
    for row in original:
        cluster = row["root_cause_cluster"]
        if cluster not in CLUSTER_PLAN:
            raise ValueError("unrecognized finding cluster: " + cluster)
        labs, effort, action = CLUSTER_PLAN[cluster]
        indexed[row["id"]] = (row, labs, effort, action)
        candidates.append(ExperimentCandidate(
            finding_id=row["id"], severity=row["severity"],
            evidence="REPRODUCED_OFFLINE" if row["evidence"] == "REPRODUCED_OFFLINE_PRIOR_AUDIT" else "INSPECTED",
            affected_labs=labs, effort_hours=effort, reproduction_available=True,
        ))
    rankings = prioritize_experiments(candidates)
    if limit is not None:
        if type(limit) is not int or limit < 1:
            raise ValueError("limit must be a positive integer")
        rankings = rankings[:limit]
    ranked = []
    for finding_id, score in rankings:
        row, labs, hours, action = indexed[finding_id]
        ranked.append({"finding_id": finding_id,
                       "severity": row["severity"],
                       "cluster": row["root_cause_cluster"],
                       "finding": row["summary"],
                       "priority_points": score,
                       "affected_labs_planning_assumption": list(labs),
                       "effort_hours_planning_assumption": hours,
                       "recommended_next_experiment": action,
                       "candidate_donors": row.get("candidate_sources", []),
                       "evidence": row["evidence"],
                       "remediation": "OPEN_UNVERIFIED"})
    return {
        "status": "RESEARCH_TRIAGE_ONLY_RELEASE_BLOCKED",
        "source_register_date": register.get("recorded_at"),
        "historical_open_findings": len(original),
        "cumulative_findings": len(rows),
        "priority_model": "TRANSPARENT_HEURISTIC_NOT_EXPECTED_FINANCIAL_ROI",
        "real_world_customer_impact": "NOT_ESTABLISHED",
        "next_experiments": ranked,
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=ROOT / "research" / "LAB_FINDINGS_CUMULATIVE.json")
    parser.add_argument("--limit", type=int, default=10)
    args = parser.parse_args()
    data = json.loads(args.registry.read_text(encoding="utf-8"))
    print(json.dumps(make_control_room(data, limit=args.limit), sort_keys=True, indent=2))


if __name__ == "__main__":
    main()
