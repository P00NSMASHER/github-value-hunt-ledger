#!/usr/bin/env python3
"""Prepare an incomplete prospective run without publishing telemetry.

No template values, dispatch packets, or shadow state are execution evidence.
Assignment provenance is copied only from one persisted CLAIM event.  The draft
is written to stdout, or to a new file outside intelligence/ with --output.
"""

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import re
import sys
import uuid

from ti_common import INTEL, slug


# Destination field -> authoritative CLAIM event field.  Both parent-ticket
# names are needed: the schema and execution matcher currently use different
# spellings.  They always receive the same observed value.
CLAIM_FIELDS = {
    "execution_claim_id": "claim_id",
    "execution_slot_id": "slot_id",
    "execution_worker_id": "worker_id",
    "assignment_work_item_id": "work_item_id",
    "dispatch_parent_ticket_id": "parent_dispatch_ticket_id",
    "parent_dispatch_ticket_id": "parent_dispatch_ticket_id",
    **{key: key for key in (
        "assignment_id", "allocator_generation_id", "portfolio_policy_generation_id",
        "assignment_slot_role", "assignment_work_kind", "assignment_source_id",
        "assignment_score", "routing_generation_id", "worker_profile_generation_id",
        "routing_score", "dispatch_ticket_id", "dispatch_generation_id",
        "routing_learning_generation_id", "route_override_reason", "dispatch_kind",
        "presence_generation_id", "presence_event_id", "activation_id",
        "activation_generation_id",
    )},
}
COUNTS = ("candidate_count", "deep_inspected", "retained_count", "master_promoted_count",
          "elapsed_minutes", "tool_calls", "candidate_preflight_checks",
          "known_candidate_preflight_hits", "duplicate_deep_inspections_avoided")


def read_rows(path):
    if not path.exists():
        return []
    rows = []
    for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        if line.strip():
            row = json.loads(line)
            if not isinstance(row, dict):
                raise ValueError(f"{path}:{number}: expected JSON object")
            rows.append(row)
    return rows


def read_config(path, default):
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else default


def real_claim(intel, claim_id, worker):
    """Read actual event logs, never generated history, packets, or shadow data."""
    events = []
    for path in sorted((intel / "execution_events").glob("SLOT-*.jsonl")):
        for event in read_rows(path):
            if event.get("claim_id") == claim_id:
                if event.get("slot_id") != path.stem:
                    raise ValueError("claim slot does not match its event file")
                events.append(event)
    claims = [event for event in events if event.get("event_type") == "CLAIM"]
    if len(claims) != 1:
        raise ValueError(f"claim {claim_id} requires exactly one stored CLAIM event; found {len(claims)}")
    claim = claims[0]
    if worker and worker != claim.get("worker_id"):
        raise ValueError("--worker does not match the stored claim worker")
    if any(event.get("worker_id") != claim.get("worker_id") or
           event.get("slot_id") != claim.get("slot_id") for event in events):
        raise ValueError("stored events disagree about the claim worker or slot")
    if any(event.get("event_type") in {"COMPLETE", "FAIL", "RELEASE"} for event in events):
        raise ValueError("claim has already ended; prepare a new claim or an unallocated run")
    if any(row.get("execution_claim_id") == claim_id for row in read_rows(intel / "search_runs.jsonl")):
        raise ValueError("claim already has canonical search-run telemetry")
    if (claim.get("measurement_quality") not in {None, "prospective"}
            or claim.get("shadow") or claim.get("benchmark_task_ids")
            or claim.get("evaluation_set_id") or claim.get("_draft")):
        raise ValueError("benchmark, retrospective, or shadow claims are not prospective evidence")
    required = ("claim_id", "slot_id", "worker_id", "event_id", "timestamp",
                "assignment_id", "allocator_generation_id", "portfolio_policy_generation_id",
                "work_item_id", "assignment_slot_role", "assignment_work_kind",
                "assignment_source_id", "assignment_score")
    if any(claim.get(key) is None or claim.get(key) == "" for key in required):
        raise ValueError("stored claim has incomplete assignment provenance")
    for key, value in claim.items():
        if isinstance(value, str) and ("000000000000" in value or "replace-with" in value):
            raise ValueError(f"stored claim contains placeholder provenance in {key}")
    return claim


def assignment_for_claim(intel, claim):
    """Only an exact assignment match may supply planned strategy/objective."""
    matches = [row for row in read_rows(intel / "hunt_allocations.jsonl")
               if row.get("assignment_id") == claim.get("assignment_id")]
    if len(matches) > 1:
        raise ValueError("ambiguous assignment records for claim")
    if not matches:
        return {}
    assignment = matches[0]
    for source, target in (("slot_id", "slot_id"), ("work_item_id", "work_item_id"),
                           ("allocator_generation_id", "allocator_generation_id"),
                           ("portfolio_policy_generation_id", "portfolio_policy_generation_id"),
                           ("slot_role", "assignment_slot_role"),
                           ("work_kind", "assignment_work_kind"),
                           ("source_id", "assignment_source_id"), ("final_score", "assignment_score")):
        if assignment.get(source) != claim.get(target):
            raise ValueError(f"assignment disagrees with stored claim: {source}")
    # Frozen benchmark strategy_measurement assignments require separate
    # benchmark metadata and can never be relabeled as ordinary prospective
    # discovery. Adaptive learning_measurement is a distinct live work kind.
    if assignment.get("work_kind") == "strategy_measurement":
        raise ValueError("frozen strategy measurement requires the separate benchmark workflow")
    return assignment


def validate_provenance(draft, intel):
    """Check copied scalar provenance against the repository's schema vocabulary."""
    schema = read_config(intel / "schemas" / "search_run.schema.json", {})
    properties = schema.get("properties")
    if not properties:
        raise ValueError("search-run schema is missing")
    for key in (*CLAIM_FIELDS, "routing_mode", "allocation_mode", "work_action", "strategy_id",
                "query_family_id", "search_objective_id", "search_run_id"):
        spec = properties.get(key)
        if not spec:  # parent_dispatch_ticket_id is the execution matcher's alias.
            continue
        value = draft.get(key)
        types = spec.get("type", [])
        types = [types] if isinstance(types, str) else types
        if value is None and "null" not in types:
            raise ValueError(f"{key} must not be null")
        if value is not None and types:
            expected_string = "string" in types and isinstance(value, str)
            expected_number = "number" in types and type(value) in {int, float}
            if not (expected_string or expected_number):
                raise ValueError(f"{key} has the wrong value type")
        if "enum" in spec and value not in spec["enum"]:
            raise ValueError(f"{key} has an unsupported value")
        if value is not None and "pattern" in spec and not re.fullmatch(spec["pattern"], value):
            raise ValueError(f"{key} does not match the schema identifier format")


def prepare_run(*, worker=None, claim_id=None, strategy=None, query_family=None,
                objective=None, work_action=None, intel=INTEL):
    intel = Path(intel)
    claim = real_claim(intel, claim_id, worker) if claim_id else None
    assignment = assignment_for_claim(intel, claim) if claim else {}
    if claim and claim.get("assignment_work_kind") == "strategy_measurement":
        raise ValueError("frozen strategy measurement requires the separate benchmark workflow")
    actions = {"search", "verify_artifact", "execute_fixture", "await_external"}
    if work_action is not None and work_action not in actions:
        raise ValueError("unsupported work_action")
    if claim:
        stored_action = assignment.get("work_action", claim.get("work_action"))
        if claim.get("work_action") and stored_action != claim["work_action"]:
            raise ValueError("assignment work_action disagrees with stored claim")
        if work_action is not None and work_action != stored_action:
            raise ValueError("--work-action disagrees with the stored claim/assignment action")
        work_action = stored_action
    else:
        work_action = work_action or "search"
    worker = claim["worker_id"] if claim else worker
    workers = {row.get("worker_id") for row in read_rows(intel / "worker_profiles.jsonl")}
    if worker not in workers:
        raise ValueError("provide --worker identifying a registered worker")
    for given, key in ((strategy, "strategy_id"), (objective, "search_objective_id")):
        if given and assignment.get(key) and given != assignment[key]:
            raise ValueError(f"explicit {key} disagrees with the claim's exact assignment")
    strategy = strategy or assignment.get("strategy_id")
    objective = objective or assignment.get("search_objective_id")
    strategies = {row.get("strategy_id") for row in read_rows(intel / "search_strategies.jsonl")}
    if strategy not in strategies:
        raise ValueError("provide --strategy with a registered strategy ID")
    objectives = read_config(intel / "search_objectives.json", {}).get("objectives", [])
    if objective not in {row.get("search_objective_id") for row in objectives}:
        raise ValueError("provide --objective with a controlled search objective ID")
    if not isinstance(query_family, str) or not query_family.strip():
        raise ValueError("provide --query-family with the reusable hypothesis label or registered QF ID")
    query_family = query_family.strip()
    if query_family.startswith("QF:"):
        matches = [row for row in read_rows(intel / "query_families.jsonl")
                   if row.get("query_family_id") == query_family]
        if len(matches) != 1 or not matches[0].get("label"):
            raise ValueError("--query-family ID must identify one registered label")
        query_family = matches[0]["label"]
    raw_qid = "QF:" + slug(query_family)[:120]
    aliases = read_config(intel / "query_family_aliases.json", {})
    qid = aliases.get(raw_qid, raw_qid)
    if not re.fullmatch(r"QF:[a-z0-9-]+", qid) or "replace-with" in qid:
        raise ValueError("--query-family must describe a real reusable hypothesis")

    now = datetime.now(timezone.utc)
    timestamp = now.isoformat().replace("+00:00", "Z")
    draft = {
        "schema_version": 16,
        "search_run_id": f"RUN:{now.strftime('%Y%m%dT%H%M%SZ')}:{worker}:{uuid.uuid4().hex[:12]}",
        "timestamp": timestamp,
        "hunter_role": None,
        "strategy_id": strategy,
        "query_family": query_family,
        "query_family_id": qid,
        "search_objective_id": objective,
        "measurement_quality": "prospective",
        "work_action": work_action,
        **{key: None for key in COUNTS},
        "recall_rescue_used": None,
        "recall_rescue_type": None,
        "recall_rescue_found_qualifying_candidate": None,
        "stop_reason": None,
        "stop_reason_standard": None,
        "best_result": None,
        "durable_evidence_path": None,
        "notes": "INCOMPLETE DRAFT: record actual observations and review before publication. No run has been completed.",
        **{key: [] for key in ("lane_ids", "seed_nodes", "search_surfaces", "queries",
                              "new_capability_ids", "strengthened_capability_ids", "experiment_ids",
                              "candidate_dispositions", "benchmark_task_ids", "seed_ids",
                              "adjacency_ids", "adjacency_types", "adjacency_root_nodes", "coverage_gap_ids",
                              "coordination_signal_ids", "consumed_coordination_signal_ids", "search_moves")},
        "comparison_group_id": None,
        "evaluation_set_id": None,
        "seed_mode": "free_exploration",
        "adjacency_mode": "none",
        "coverage_mode": "none",
        "allocation_mode": "unallocated",
        "routing_mode": "unrouted",
        **{key: None for key in CLAIM_FIELDS},
        "_draft": {
            "status": "incomplete",
            "created_at": timestamp,
            "claim_event_id": claim.get("event_id") if claim else None,
            "instructions": "Fill only observed queries, surfaces, denominators, dispositions, costs, and evidence. Remove _draft only after observation and review, then validate before publishing; this helper does not publish or complete a claim.",
        },
    }
    draft["execution_worker_id"] = worker
    if claim:
        draft.update({target: claim.get(source) for target, source in CLAIM_FIELDS.items()})
        draft["allocation_mode"] = claim.get("allocation_mode") or (
            "manual_override" if claim.get("routing_mode") == "manual_override" else "generated")
        draft["routing_mode"] = claim.get("routing_mode") or "unrouted"
        if claim["assignment_source_id"].startswith("SEED:"):
            draft["seed_mode"] = "generated"
            draft["seed_ids"] = [claim["assignment_source_id"]]
    validate_provenance(draft, intel)
    return draft


def write_draft(draft, output, *, intel=INTEL):
    """Exclusive creation prevents overwrites; canonical ingestion paths are barred."""
    path = Path(output).expanduser()
    resolved = path.resolve()
    if resolved == Path(intel).resolve() or Path(intel).resolve() in resolved.parents:
        raise ValueError("draft output must be outside intelligence/; canonical and spool writes are forbidden")
    if path.suffix.lower() != ".json":
        raise ValueError("draft output must use a .json filename")
    with path.open("x", encoding="utf-8") as handle:
        handle.write(json.dumps(draft, indent=2, ensure_ascii=False) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--claim-id", help="bind to exactly one actual stored CLAIM event")
    parser.add_argument("--worker", help="registered worker; inferred from a claim when omitted")
    parser.add_argument("--strategy", help="registered STRAT ID; inferred only from an exact assignment")
    parser.add_argument("--query-family", required=True, help="reusable hypothesis label or registered QF ID")
    parser.add_argument("--objective", help="controlled OBJ ID; inferred only from an exact assignment")
    parser.add_argument("--work-action", choices=("search", "verify_artifact", "execute_fixture", "await_external"),
                        help="unallocated default: search; bound runs copy the stored action or remain unknown")
    parser.add_argument("--output", type=Path, help="new .json file outside intelligence/; default is stdout")
    args = parser.parse_args(argv)
    try:
        draft = prepare_run(worker=args.worker, claim_id=args.claim_id, strategy=args.strategy,
                            query_family=args.query_family, objective=args.objective, work_action=args.work_action)
        if args.output:
            write_draft(draft, args.output)
            print(f"Incomplete draft created: {args.output}", file=sys.stderr)
        else:
            print(json.dumps(draft, indent=2, ensure_ascii=False))
    except (OSError, ValueError) as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
