#!/usr/bin/env python3
import json, re
from ti_common import INTEL, ROOT, load_jsonl, slug

def unique(rows, key, name):
    seen = {}
    for n, obj in enumerate(rows, 1):
        value = obj.get(key)
        if not value:
            raise SystemExit(f"{name}:{n}: missing {key}")
        if value in seen:
            raise SystemExit(f"{name}:{n}: duplicate {key}={value}; first line {seen[value]}")
        seen[value] = n
    return set(seen)

caps = load_jsonl("capabilities.jsonl")
strats = load_jsonl("search_strategies.jsonl")
runs = load_jsonl("search_runs.jsonl")
outs = load_jsonl("outcomes.jsonl")
qfs = load_jsonl("query_families.jsonl")
curated_edges = load_jsonl("edges.jsonl")
derived_edges = load_jsonl("derived_edges.jsonl") if (INTEL / "derived_edges.jsonl").exists() else []

cap_ids = unique(caps, "capability_id", "capabilities.jsonl")
strat_ids = unique(strats, "strategy_id", "search_strategies.jsonl")
run_ids = unique(runs, "search_run_id", "search_runs.jsonl")
out_ids = unique(outs, "outcome_id", "outcomes.jsonl")
qf_ids = unique(qfs, "query_family_id", "query_families.jsonl")
unique(curated_edges, "edge_id", "edges.jsonl")
unique(derived_edges, "edge_id", "derived_edges.jsonl")

query_aliases = json.loads((INTEL / "query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL / "query_family_aliases.json").exists() else {}
reason_catalog = json.loads((INTEL / "reason_codes.json").read_text(encoding="utf-8")) if (INTEL / "reason_codes.json").exists() else {}
standard_reasons = set(v for vals in reason_catalog.values() for v in vals)

def canonical_qf(label):
    raw = "QF:" + (slug(label or "unknown")[:120] or "unknown")
    return query_aliases.get(raw, raw)

for n, c in enumerate(caps, 1):
    if not re.match(r"^CAP-\d{3,}$", c["capability_id"]):
        raise SystemExit(f"capabilities.jsonl:{n}: bad capability id")
    if c.get("confidence") not in {"low", "medium", "high"}:
        raise SystemExit(f"capabilities.jsonl:{n}: bad confidence")

for n, s in enumerate(strats, 1):
    parent = s.get("parent_strategy_id")
    if parent and parent not in strat_ids:
        raise SystemExit(f"search_strategies.jsonl:{n}: missing parent strategy {parent}")

for n, r in enumerate(runs, 1):
    sid = r.get("strategy_id")
    if sid not in strat_ids:
        raise SystemExit(f"search_runs.jsonl:{n}: unknown strategy_id {sid}")
    expected_qf = canonical_qf(r.get("query_family"))
    if expected_qf not in qf_ids:
        raise SystemExit(f"search_runs.jsonl:{n}: derived query family missing {expected_qf}")
    if r.get("query_family_id") and r["query_family_id"] != expected_qf:
        raise SystemExit(f"search_runs.jsonl:{n}: query_family_id drift; expected {expected_qf}")
    for key in ["candidate_count", "deep_inspected", "retained_count", "master_promoted_count"]:
        value = r.get(key)
        if value is not None and (not isinstance(value, int) or value < 0):
            raise SystemExit(f"search_runs.jsonl:{n}: {key} must be null or nonnegative integer")
    c, d, k, m = r.get("candidate_count"), r.get("deep_inspected"), r.get("retained_count"), r.get("master_promoted_count")
    if c is not None and d is not None and d > c:
        raise SystemExit(f"search_runs.jsonl:{n}: deep_inspected > candidate_count")
    if d is not None and k is not None and k > d:
        raise SystemExit(f"search_runs.jsonl:{n}: retained_count > deep_inspected")
    if k is not None and m is not None and m > k:
        raise SystemExit(f"search_runs.jsonl:{n}: master_promoted_count > retained_count")
    for cid in r.get("new_capability_ids", []) + r.get("strengthened_capability_ids", []):
        if cid not in cap_ids:
            raise SystemExit(f"search_runs.jsonl:{n}: unknown capability {cid}")
    seen_disp = set()
    for disp in r.get("candidate_dispositions", []) or []:
        key = (disp.get("repository"), disp.get("revision"))
        if key in seen_disp and key != (None, None):
            raise SystemExit(f"search_runs.jsonl:{n}: duplicate candidate disposition {key}")
        seen_disp.add(key)
        for cid in disp.get("capability_ids") or []:
            if cid not in cap_ids:
                raise SystemExit(f"search_runs.jsonl:{n}: candidate references unknown capability {cid}")
        if (r.get("schema_version") or 0) >= 3:
            std = disp.get("reason_code_standard")
            if not std:
                raise SystemExit(f"search_runs.jsonl:{n}: V3 candidate missing reason_code_standard")
            if std not in standard_reasons:
                raise SystemExit(f"search_runs.jsonl:{n}: unknown reason_code_standard {std}")
    if (r.get("schema_version") or 0) >= 3 and r.get("query_family_id") != expected_qf:
        raise SystemExit(f"search_runs.jsonl:{n}: V3 run must persist canonical query_family_id")

for n, o in enumerate(outs, 1):
    if len(o.get("origin_search_ids", [])) != len(set(o.get("origin_search_ids", []))):
        raise SystemExit(f"outcomes.jsonl:{n}: duplicate origin_search_ids")
    for rid in o.get("origin_search_ids", []):
        if rid not in run_ids:
            raise SystemExit(f"outcomes.jsonl:{n}: unknown origin_search_id {rid}")
    if len(o.get("contributing_capability_ids", [])) != len(set(o.get("contributing_capability_ids", []))):
        raise SystemExit(f"outcomes.jsonl:{n}: duplicate contributing_capability_ids")
    for cid in o.get("contributing_capability_ids", []):
        if cid not in cap_ids:
            raise SystemExit(f"outcomes.jsonl:{n}: unknown capability {cid}")
    low, high = o.get("engineering_days_saved_low"), o.get("engineering_days_saved_high")
    if low is not None and high is not None and low > high:
        raise SystemExit(f"outcomes.jsonl:{n}: engineering_days_saved_low > high")

known = cap_ids | strat_ids | run_ids | out_ids | qf_ids
for name, edges in [("edges.jsonl", curated_edges), ("derived_edges.jsonl", derived_edges)]:
    for n, e in enumerate(edges, 1):
        for side in ("from", "to"):
            value = e.get(side)
            if not value:
                raise SystemExit(f"{name}:{n}: missing {side}")
            if value.startswith(("CAP-", "STRAT:", "RUN:", "OUT:", "QF:")) and value not in known:
                raise SystemExit(f"{name}:{n}: dangling {side} reference {value}")

registry_path = INTEL / "registry_metrics.json"
if registry_path.exists():
    registry = json.loads(registry_path.read_text(encoding="utf-8"))
    master_text = (ROOT / "MASTER.md").read_text(encoding="utf-8")
    master_repo_count = len(set(re.findall(r"^###\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)", master_text, re.M)))
    if master_repo_count and registry.get("master_promoted_repositories") != master_repo_count:
        raise SystemExit(
            f"registry_metrics.json: MASTER count drift {registry.get('master_promoted_repositories')} != {master_repo_count}"
        )

attr_path = INTEL / "attribution_metrics.json"
if attr_path.exists():
    attr = json.loads(attr_path.read_text(encoding="utf-8"))
    totals = attr.get("totals", {})
    by_run = attr.get("by_run", [])
    checks = [
        ("revenue_usd", "revenue_usd_credit"),
        ("customer_value_usd", "customer_value_usd_credit"),
        ("engineering_days_saved_low", "engineering_days_saved_low_credit"),
        ("engineering_days_saved_high", "engineering_days_saved_high_credit")
    ]
    for total_key, credit_key in checks:
        credited = sum((x.get(credit_key) or 0) for x in by_run)
        actual = totals.get(total_key) or 0
        if abs(credited - actual) > 1e-6:
            raise SystemExit(f"attribution_metrics.json: {credit_key}={credited} does not conserve {total_key}={actual}")

domain_expectations = {}
domain_policy_path = INTEL / "domain_search_policies.json"
if domain_policy_path.exists():
    domain_config = json.loads(domain_policy_path.read_text(encoding="utf-8"))
    if domain_config.get("schema_version") != 1:
        raise SystemExit("domain_search_policies.json: unsupported schema_version")
    seen_domains = set()
    for n, domain in enumerate(domain_config.get("domains", []), 1):
        domain_id = domain.get("domain_id")
        if not domain_id or domain_id in seen_domains:
            raise SystemExit(f"domain_search_policies.json:{n}: missing/duplicate domain_id")
        seen_domains.add(domain_id)
        if domain.get("gate_type") != "gap_registry_active_search":
            raise SystemExit(f"domain_search_policies.json:{n}: unsupported gate_type")
        gate_path = domain.get("gate_path")
        if not gate_path or not (ROOT / gate_path).exists():
            raise SystemExit(f"domain_search_policies.json:{n}: missing gate_path")
        register = json.loads((ROOT / gate_path).read_text(encoding="utf-8"))
        gaps = {g.get("gap_id"): g for g in register.get("gaps", []) if g.get("gap_id")}
        active_gap_ids = sorted(gid for gid, gap in gaps.items() if gap.get("status") == "ACTIVE_SEARCH" and gap.get("search_allowed") is True)
        active_set = set(active_gap_ids)
        capability_gap_map = domain.get("capability_gap_map") or {}
        if not isinstance(capability_gap_map, dict) or not capability_gap_map:
            raise SystemExit(f"domain_search_policies.json:{n}: capability_gap_map required")
        authorized, blocked = [], []
        for cid, gap_ids in capability_gap_map.items():
            if cid not in cap_ids:
                raise SystemExit(f"domain_search_policies.json:{n}: unknown capability {cid}")
            if not isinstance(gap_ids, list) or not gap_ids:
                raise SystemExit(f"domain_search_policies.json:{n}: {cid} must map to non-empty gap list")
            unknown_gaps = sorted(set(gap_ids) - set(gaps))
            if unknown_gaps:
                raise SystemExit(f"domain_search_policies.json:{n}: {cid} maps unknown gaps {unknown_gaps}")
            (authorized if active_set.intersection(gap_ids) else blocked).append(cid)
        for cid in domain.get("shared_capability_ids") or []:
            if cid not in cap_ids:
                raise SystemExit(f"domain_search_policies.json:{n}: unknown shared capability {cid}")
        domain_expectations[domain_id] = {
            "search_authorized": bool(active_gap_ids),
            "active_search_gap_ids": active_gap_ids,
            "authorized_exclusive_capability_ids": sorted(authorized),
            "blocked_exclusive_capability_ids": sorted(blocked),
        }

policy_path = INTEL / "search_policy.json"
if policy_path.exists():
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    allocations = policy.get("strategy_allocation", [])
    if allocations:
        total = sum(x.get("allocation", 0) for x in allocations)
        if not 0.999 <= total <= 1.001:
            raise SystemExit(f"search_policy.json: allocations sum to {total}, expected 1")
    constraints = {x.get("domain_id"): x for x in policy.get("domain_constraints", [])}
    priority_ids = {x.get("capability_id") for x in policy.get("priority_capability_gaps", [])}
    for domain_id, expected in domain_expectations.items():
        actual = constraints.get(domain_id)
        if not actual:
            raise SystemExit(f"search_policy.json: missing domain constraint {domain_id}")
        for key in ("search_authorized","active_search_gap_ids","authorized_exclusive_capability_ids","blocked_exclusive_capability_ids"):
            actual_value = actual.get(key)
            expected_value = expected[key]
            if isinstance(expected_value, list):
                actual_value = sorted(actual_value or [])
            if actual_value != expected_value:
                raise SystemExit(f"search_policy.json: domain {domain_id} {key} drift")
        leaked = priority_ids.intersection(expected["blocked_exclusive_capability_ids"])
        if leaked:
            raise SystemExit(f"search_policy.json: blocked domain capabilities leaked into priority gaps: {sorted(leaked)}")

print(
    f"OK capabilities={len(caps)} strategies={len(strats)} query_families={len(qfs)} runs={len(runs)} "
    f"outcomes={len(outs)} curated_edges={len(curated_edges)} derived_edges={len(derived_edges)} "
    f"domains={len(domain_expectations)}"
)
