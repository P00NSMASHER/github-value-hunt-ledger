"""Offline, review-only connection from Hunter evidence to Freight priorities.

Reads repository records as data. Does not import researched code, fetch URLs,
change gap states, write outcome records, or perform customer/provider actions.
"""
from __future__ import annotations

import argparse
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
import re

from freight.commercial_learning import calibrate_commercial_outcomes
from freight.gap_registry import gap_index

INPUTS = {
    "capabilities": "intelligence/capabilities.jsonl",
    "edges": "intelligence/edges.jsonl",
    "outcomes": "intelligence/outcomes.jsonl",
    "search_runs": "intelligence/search_runs.jsonl",
    "gaps": "freight/GAP_REGISTER.json",
    "mapping": "freight/HUNTER_FREIGHT_MAP.json",
}
DISPOSITIONS = {"USE", "DEFER", "OUT_OF_SCOPE"}
PRIORITIES = {"P0", "P1", "P2", "P3"}


def digest(value: object) -> str:
    return hashlib.sha256(json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False,
        allow_nan=False,
    ).encode()).hexdigest()


def _index(rows: list[dict], key: str) -> dict[str, dict]:
    result = {}
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError(f"{key}: expected object record")
        identity = row.get(key)
        if not isinstance(identity, str) or not identity.strip():
            raise ValueError(f"{key}: missing identity")
        if identity in result:
            raise ValueError(f"{key}: duplicate {identity}")
        result[identity] = row
    return result


def _related_runs(capability_id: str, search_runs: list[dict]) -> list[dict]:
    related = []
    for run in search_runs:
        candidates = [candidate for candidate in run.get("candidate_dispositions", [])
                      if capability_id in candidate.get("capability_ids", [])]
        ids = (run.get("new_capability_ids", [])
               + run.get("strengthened_capability_ids", [])
               + run.get("seed_nodes", []))
        if capability_id not in ids and not candidates:
            continue
        related.append({
            "search_run_id": run["search_run_id"],
            "evidence_path": run.get("durable_evidence_path"),
            "best_result": run.get("best_result"),
            "repositories": [{
                "repository": candidate.get("repository"),
                "revision": candidate.get("revision"),
                "status": candidate.get("status"),
                "reason": candidate.get("reason_detail"),
            } for candidate in candidates],
        })
    return sorted(related, key=lambda row: row["search_run_id"])


def capability_evidence(capability: dict, edges: list[dict], search_runs: list[dict]) -> dict:
    identity = capability["capability_id"]
    return {
        "capability": capability,
        "edges": sorted(
            [edge for edge in edges if identity in (edge.get("from"), edge.get("to"))],
            key=lambda edge: edge["edge_id"],
        ),
        "search_evidence": _related_runs(identity, search_runs),
    }


def _validate_mapping(mapping: dict, gaps: dict[str, dict]) -> dict[str, dict]:
    if mapping.get("schema_version") != 1 or mapping.get("experiment_id") != "EXP-001":
        raise ValueError("mapping must be schema_version 1 and EXP-001")
    if not re.fullmatch(r"[0-9a-f]{40}", mapping.get("reviewed_source_ref", "")):
        raise ValueError("mapping reviewed_source_ref must be a full Git commit")
    rows = _index(mapping.get("capabilities", []), "capability_id")
    if not rows:
        raise ValueError("mapping capabilities must not be empty")
    for identity, row in rows.items():
        if row.get("disposition") not in DISPOSITIONS or row.get("priority") not in PRIORITIES:
            raise ValueError(f"{identity}: invalid disposition or priority")
        for field in ("freight_use", "rationale", "acceptance_test", "limitation"):
            if not isinstance(row.get(field), str) or not row[field].strip():
                raise ValueError(f"{identity}: {field} required")
        if not re.fullmatch(r"[0-9a-f]{64}", row.get("reviewed_evidence_sha256", "")):
            raise ValueError(f"{identity}: reviewed evidence hash required")
        gap_ids = row.get("gap_ids")
        if not isinstance(gap_ids, list) or any(gap not in gaps for gap in gap_ids):
            raise ValueError(f"{identity}: unknown gap or missing gap_ids")
    return rows


def build_report(
    capabilities: list[dict], edges: list[dict], outcomes: list[dict],
    search_runs: list[dict], gap_register: dict, mapping: dict,
    *, source_ref: str | None = None,
) -> dict:
    if source_ref is not None and not re.fullmatch(r"[0-9a-f]{40}", source_ref):
        raise ValueError("source_ref must be a full Git commit when supplied")
    capability_index = _index(capabilities, "capability_id")
    if not capability_index:
        raise ValueError("capability registry is empty")
    _index(edges, "edge_id")
    _index(outcomes, "outcome_id")
    run_index = _index(search_runs, "search_run_id")
    gaps = gap_index(gap_register)
    mapped = _validate_mapping(mapping, gaps)
    review_items = []
    capability_rows = []

    for identity, capability in sorted(capability_index.items()):
        evidence = capability_evidence(capability, edges, search_runs)
        evidence_hash = digest(evidence)
        row = mapped.get(identity)
        review_status = (
            "UNMAPPED" if row is None else
            "SOURCE_CHANGED" if row["reviewed_evidence_sha256"] != evidence_hash else
            "REVIEWED"
        )
        if review_status != "REVIEWED":
            review_items.append({"capability_id": identity, "reason": review_status})
        capability_rows.append({
            "capability_id": identity,
            "name": capability.get("name"),
            "disposition": row["disposition"] if row else "DEFER",
            "priority": row["priority"] if row else "P2",
            "review_status": review_status,
            "freight_use": row["freight_use"] if row else "Owner review required before adoption.",
            "rationale": row["rationale"] if row else "No reviewed Freight application recorded.",
            "gap_ids": row["gap_ids"] if row else [],
            "acceptance_test": row["acceptance_test"] if row else "Define a measurable Freight acceptance test.",
            "freight_limitation": row["limitation"] if row else "Not yet assessed for Freight.",
            "hunter_limitation": capability.get("limitation"),
            "hunter_next_test": capability.get("next_falsifiable_test"),
            "maturity": capability.get("maturity"),
            "evidence_state": capability.get("evidence_state"),
            "source_path": capability.get("source_markdown"),
            "evidence_basis": capability.get("evidence_basis"),
            "reviewed_evidence_sha256": row["reviewed_evidence_sha256"] if row else None,
            "current_evidence_sha256": evidence_hash,
            "graph_evidence": evidence["edges"],
            "search_evidence": evidence["search_evidence"],
            "outcome_ids": sorted(outcome["outcome_id"] for outcome in outcomes
                                  if identity in outcome.get("contributing_capability_ids", [])),
        })
    for identity in sorted(mapped.keys() - capability_index.keys()):
        review_items.append({"capability_id": identity, "reason": "REMOVED_FROM_REGISTRY"})

    freight_outcomes = [outcome for outcome in outcomes if outcome.get("experiment_id") == "EXP-001"]
    outcome_rows, calibrated_records = [], []
    for outcome in sorted(freight_outcomes, key=lambda row: row["outcome_id"]):
        missing_runs = sorted(set(outcome.get("origin_search_ids", [])) - run_index.keys())
        missing_caps = sorted(set(outcome.get("contributing_capability_ids", [])) - capability_index.keys())
        attributed = bool(outcome.get("origin_search_ids") and outcome.get("contributing_capability_ids"))
        location = outcome.get("evidence_location")
        provenance_valid = bool(attributed and not missing_runs and not missing_caps
                                and isinstance(location, str) and location.strip())
        if provenance_valid:
            calibrated_records.append(outcome)
        else:
            review_items.append({"outcome_id": outcome["outcome_id"], "reason": "OUTCOME_PROVENANCE_INCOMPLETE"})
        metrics = outcome.get("freight_metrics") or {}
        outcome_rows.append({
            "outcome_id": outcome["outcome_id"],
            "result": outcome.get("result"),
            "synthetic": metrics.get("synthetic"),
            "external_commercial_evidence_recorded": metrics.get("external_commercial_evidence") is True,
            "evidence_location": outcome.get("evidence_location"),
            "origin_search_ids": outcome.get("origin_search_ids", []),
            "provenance_valid": provenance_valid,
            "missing_search_run_ids": missing_runs,
            "missing_capability_ids": missing_caps,
        })

    gap_priority = {"BLOCKED_EXTERNAL": "P0", "ACTIVE_INTERNAL": "P1", "ACTIVE_DILIGENCE": "P1", "ACTIVE_SEARCH": "P2", "DORMANT_TRIGGERED": "P3", "CLOSED": "P3"}
    backlog = [{
        **gap,
        "priority": gap_priority[gap["status"]],
        "capability_ids": sorted(row["capability_id"] for row in capability_rows if gap_id in row["gap_ids"]),
        "next_action": (
            "Obtain the named external evidence; additional repository research cannot close this gap."
            if gap["status"] == "BLOCKED_EXTERNAL" else
            "Retain dormant state until the registered real-world trigger occurs."
            if gap["status"] == "DORMANT_TRIGGERED" else
            "Review the evidence-to-close checklist with the assigned owner."
        ),
    } for gap_id, gap in gaps.items()]

    return {
        "schema_version": 1,
        "mode": "REVIEW_ONLY",
        "source_ref": source_ref,
        "mapping_reviewed_source_ref": mapping["reviewed_source_ref"],
        "coverage": {
            "registry_capabilities": len(capability_rows),
            "mapped_capabilities": len(capability_index.keys() & mapped.keys()),
            "review_required": len(review_items),
            "dispositions": {name: sum(row["disposition"] == name for row in capability_rows) for name in sorted(DISPOSITIONS)},
        },
        "review_items": review_items,
        "commercial_calibration": asdict(calibrate_commercial_outcomes(calibrated_records)),
        "outcomes": outcome_rows,
        "gap_backlog": sorted(backlog, key=lambda row: (row["priority"], row["gap_id"])),
        "capabilities": sorted(capability_rows, key=lambda row: (row["priority"], row["capability_id"])),
        "boundaries": [
            "Registry coverage is not a claim that every catalog repository has been integrated.",
            "USE means a reviewed application proposal, not installed code or a passed deployment gate.",
            "Source fingerprints identify evidence changes; they do not establish correctness or commercial rights.",
            "Commercial calibration reuses Freight policy and records, not a revenue forecast or independently verified payment total.",
            "Synthetic outcomes do not establish revenue, customer value, or demand.",
            "Gap states, customer-data permission, pricing, outcomes and deployment remain unchanged.",
        ],
    }


def load_report(root: Path, *, source_ref: str | None = None) -> dict:
    records, manifest = {}, []
    for name, relative in INPUTS.items():
        content = (root / relative).read_bytes()
        manifest.append({"path": relative, "sha256": hashlib.sha256(content).hexdigest()})
        text = content.decode("utf-8")
        records[name] = ([json.loads(line) for line in text.splitlines() if line.strip()]
                         if relative.endswith(".jsonl") else json.loads(text))
    report = build_report(
        records["capabilities"], records["edges"], records["outcomes"],
        records["search_runs"], records["gaps"], records["mapping"], source_ref=source_ref,
    )
    catalog_path = "CAPABILITIES.md"
    catalog_hash = hashlib.sha256((root / catalog_path).read_bytes()).hexdigest()
    manifest.append({"path": catalog_path, "sha256": catalog_hash})
    if records["mapping"].get("reviewed_catalog_sha256") != catalog_hash:
        report["review_items"].append({"source_path": catalog_path, "reason": "CANONICAL_CATALOG_CHANGED"})
        report["coverage"]["review_required"] += 1
    report["input_manifest"] = manifest
    return report


def render_markdown(report: dict) -> str:
    def cell(value: object) -> str:
        return str(value).replace("|", "\\|").replace("\n", " ")

    calibration = report["commercial_calibration"]
    lines = [
        "# Hunter to Freight review", "",
        f"Coverage: {report['coverage']['mapped_capabilities']}/{report['coverage']['registry_capabilities']} registry capabilities; {report['coverage']['review_required']} items require review.", "",
        f"Commercial calibration: {calibration['status']}; {calibration['unique_buyers']} eligible buyer cohorts; recommendation {calibration['recommended_action']}.", "",
        "This is an internal review report. USE is an application proposal; it does not authorize a deployment, customer-data intake, or an external action.", "",
        "## Business blockers", "", "| Priority | Gap | State | Evidence needed |", "|---|---|---|---|",
    ]
    for gap in report["gap_backlog"]:
        lines.append("| " + " | ".join(map(cell, [gap["priority"], gap["gap_id"] + ": " + gap["title"], gap["status"], "; ".join(gap["evidence_to_close"])])) + " |")
    lines += ["", "## Capability applications", "", "| Capability | Decision | Review | Freight application | Acceptance test |", "|---|---|---|---|---|"]
    for row in report["capabilities"]:
        lines.append("| " + " | ".join(map(cell, [row["capability_id"] + ": " + row["name"], row["disposition"], row["review_status"], row["freight_use"], row["acceptance_test"]])) + " |")
    lines += ["", "## Review queue", ""]
    lines += [f"- {item.get('capability_id', item.get('outcome_id', item.get('source_path')))}: {item['reason']}" for item in report["review_items"]] or ["No new evidence changes require mapping review."]
    lines += ["", "## Boundaries", ""] + ["- " + value for value in report["boundaries"]]
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--source-ref", help="Exact source Git commit; input hashes are always recorded")
    parser.add_argument("--format", choices=("json", "markdown"), default="json")
    parser.add_argument("--check", action="store_true", help="Exit 1 when evidence or attribution requires review")
    args = parser.parse_args()
    try:
        report = load_report(args.root, source_ref=args.source_ref)
        print(render_markdown(report) if args.format == "markdown" else json.dumps(report, indent=2, sort_keys=True, allow_nan=False))
        return int(args.check and bool(report["review_items"]))
    except (OSError, ValueError, TypeError, KeyError) as exc:
        parser.exit(2, f"Hunter bridge input error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
