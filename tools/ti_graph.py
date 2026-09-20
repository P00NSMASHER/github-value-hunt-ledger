#!/usr/bin/env python3
import hashlib
from collections import Counter, defaultdict
from ti_common import (
    INTEL,
    canonical_query_family,
    load_jsonl,
    outcome_search_weights,
    write_jsonl,
)

caps = load_jsonl("capabilities.jsonl")
runs = load_jsonl("search_runs.jsonl")
outs = load_jsonl("outcomes.jsonl")
curated = load_jsonl("edges.jsonl")
query_families = load_jsonl("query_families.jsonl")

def edge_id(a, t, b):
    return "EDGE:" + hashlib.sha1((a + "|" + t + "|" + b).encode()).hexdigest()[:12]

derived = []
seen = set()

def add(a, t, b, evidence, **extra):
    key = (a, t, b)
    if key in seen:
        return
    seen.add(key)
    edge = {
        "edge_id": edge_id(a, t, b),
        "from": a,
        "type": t,
        "to": b,
        "confidence": "high",
        "evidence_ref": evidence,
        "provenance": "derived_structured_event"
    }
    edge.update(extra)
    derived.append(edge)

for r in runs:
    rid = r["search_run_id"]
    sid = r.get("strategy_id")
    qid = canonical_query_family(r)

    if sid:
        add(sid, "PRODUCED", rid, "intelligence/search_runs.jsonl")
    if qid:
        add(qid, "PRODUCED", rid, "intelligence/search_runs.jsonl")

    for cid in r.get("new_capability_ids", []):
        add(rid, "PRODUCED", cid, "intelligence/search_runs.jsonl")
    for cid in r.get("strengthened_capability_ids", []):
        add(rid, "STRENGTHENS", cid, "intelligence/search_runs.jsonl")
    for exp in r.get("experiment_ids", []):
        add(rid, "CONTRIBUTED_TO", exp, "intelligence/search_runs.jsonl")
    for disposition in r.get("candidate_dispositions", []) or []:
        repository = disposition.get("repository")
        if repository:
            node = "REPO:" + repository + ("@" + disposition["revision"] if disposition.get("revision") else "")
            add(rid, "DISCOVERED", node, "intelligence/search_runs.jsonl")

for o in outs:
    oid = o["outcome_id"]
    weights = outcome_search_weights(o)
    for rid, weight in weights.items():
        add(
            rid,
            "PRODUCED",
            oid,
            "intelligence/outcomes.jsonl",
            credit_weight=weight
        )
    for cid in o.get("contributing_capability_ids", []):
        add(cid, "CONTRIBUTED_TO", oid, "intelligence/outcomes.jsonl")
    if o.get("experiment_id"):
        add(oid, "VALIDATES", o["experiment_id"], "intelligence/outcomes.jsonl")

write_jsonl("derived_edges.jsonl", sorted(derived, key=lambda x: x["edge_id"]))

attention = Counter()
experiments = defaultdict(set)
for r in runs:
    for cid in r.get("new_capability_ids", []) + r.get("strengthened_capability_ids", []):
        attention[cid] += 1
        for exp in r.get("experiment_ids", []):
            experiments[cid].add(exp)

support = {}
for c in caps:
    components = len(c.get("primary_components") or [])
    targets = len(c.get("reusable_targets") or [])
    score = 0
    if c.get("evidence_state") == "watch":
        score += 3
    elif c.get("evidence_state") == "source_or_test_validated":
        score += 2
    elif c.get("evidence_state") == "benchmarked":
        score += 1
    if c.get("missing_piece"):
        score += 2
    if components < 2:
        score += 2
    if attention[c["capability_id"]] == 0:
        score += 1
    support[c["capability_id"]] = {
        "components": components,
        "targets": targets,
        "attention": attention[c["capability_id"]],
        "experiments": len(experiments[c["capability_id"]]),
        "gap_score": score
    }

priority = sorted(caps, key=lambda c: (-support[c["capability_id"]]["gap_score"], c["capability_id"]))[:12]

credit_edge_total = sum(
    float(e.get("credit_weight") or 0)
    for e in derived
    if e.get("to", "").startswith("OUT:")
)

lines = [
    "# GRAPH HEALTH REPORT", "",
    f"- Curated edges: **{len(curated)}**",
    f"- Derived attribution edges: **{len(derived)}**",
    f"- Query-family nodes: **{len(query_families)}**",
    f"- Capability nodes: **{len(caps)}**",
    f"- Capabilities touched by measured search runs: **{sum(1 for c in caps if attention[c['capability_id']] > 0)}**",
    f"- Total weighted search->outcome edge credit: **{credit_edge_total:.2f}**", "",
    "## Highest-priority capability gaps", "",
    "| Capability | Evidence | Components | Run attention | Experiments | Gap score | Missing piece |",
    "|---|---|---:|---:|---:|---:|---|"
]
for c in priority:
    s = support[c["capability_id"]]
    lines.append(
        f"| {c['capability_id']} — {c['name']} | {c.get('evidence_state')} | {s['components']} | "
        f"{s['attention']} | {s['experiments']} | {s['gap_score']} | {c.get('missing_piece') or '—'} |"
    )

lines += [
    "", "## Graph policy", "",
    "- Search-to-outcome edges carry fractional credit; weights for one outcome sum to 1.00.",
    "- Query families and search strategies are separate nodes: a strong literal family does not automatically validate the strategy that happened to use it.",
    "- High gap score means information value, not commercial priority.",
    "- Prefer searches that close a named missing edge in an active experiment over searches that add another similar implementation.",
    "- Independent challengers and negative controls can be more valuable than a second implementation of the same mechanism.", ""
]

(INTEL / "GRAPH_HEALTH.md").write_text("\n".join(lines), encoding="utf-8")
print(f"derived_edges={len(derived)} weighted_outcome_credit={credit_edge_total:.2f}")
