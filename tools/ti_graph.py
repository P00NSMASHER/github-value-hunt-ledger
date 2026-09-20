#!/usr/bin/env python3
import hashlib, json
from collections import Counter, defaultdict
from ti_common import INTEL, load_jsonl, slug, write_jsonl

caps = load_jsonl("capabilities.jsonl")
runs = load_jsonl("search_runs.jsonl")
outs = load_jsonl("outcomes.jsonl")
curated = load_jsonl("edges.jsonl")
query_families = load_jsonl("query_families.jsonl")
query_aliases = json.loads((INTEL / "query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL / "query_family_aliases.json").exists() else {}

def edge_id(a, t, b):
    return "EDGE:" + hashlib.sha1((a + "|" + t + "|" + b).encode()).hexdigest()[:12]

def qfid(run):
    raw = "QF:" + (slug(run.get("query_family") or "unknown")[:120] or "unknown")
    return query_aliases.get(raw, raw)

derived = []
seen = set()

def add(a, t, b, evidence):
    if not a or not b:
        return
    key = (a, t, b)
    if key in seen:
        return
    seen.add(key)
    derived.append({
        "edge_id": edge_id(a, t, b),
        "from": a,
        "type": t,
        "to": b,
        "confidence": "high",
        "evidence_ref": evidence,
        "provenance": "derived_structured_event"
    })

for r in runs:
    rid = r["search_run_id"]
    sid = r.get("strategy_id")
    if sid:
        add(sid, "PRODUCED", rid, "intelligence/search_runs.jsonl")
    add(qfid(r), "PRODUCED", rid, "intelligence/search_runs.jsonl")
    for surface in sorted(set(r.get("search_surfaces") or [])):
        add(rid, "USED_SURFACE", "SURFACE:" + slug(surface), "intelligence/search_runs.jsonl")
    for cid in r.get("new_capability_ids", []):
        add(rid, "PRODUCED", cid, "intelligence/search_runs.jsonl")
    for cid in r.get("strengthened_capability_ids", []):
        add(rid, "STRENGTHENS", cid, "intelligence/search_runs.jsonl")
    for exp in r.get("experiment_ids", []):
        add(rid, "CONTRIBUTED_TO", exp, "intelligence/search_runs.jsonl")
    for disposition in r.get("candidate_dispositions", []) or []:
        repository = disposition.get("repository")
        if not repository:
            continue
        node = "REPO:" + repository + ("@" + disposition["revision"] if disposition.get("revision") else "")
        add(rid, "DISCOVERED", node, "intelligence/search_runs.jsonl")
        for cid in disposition.get("capability_ids") or []:
            add(node, "STRENGTHENS", cid, "intelligence/search_runs.jsonl")

for o in outs:
    oid = o["outcome_id"]
    for rid in o.get("origin_search_ids", []):
        add(rid, "PRODUCED", oid, "intelligence/outcomes.jsonl")
    for cid in o.get("contributing_capability_ids", []):
        add(cid, "CONTRIBUTED_TO", oid, "intelligence/outcomes.jsonl")
    for repository in o.get("contributing_repositories", []) or []:
        node = "REPO:" + repository
        add(node, "CONTRIBUTED_TO", oid, "intelligence/outcomes.jsonl")
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

all_edges = curated + derived
support_count = Counter()
for e in all_edges:
    if e.get("to", "").startswith("CAP-") and e.get("from", "").startswith(("REPO:", "SOURCE:", "DATA:")):
        support_count[e["to"]] += 1

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
        "graph_support": support_count[c["capability_id"]],
        "gap_score": score
    }

priority = sorted(caps, key=lambda c: (-support[c["capability_id"]]["gap_score"], c["capability_id"]))[:12]
surface_nodes = {e["to"] for e in derived if e.get("to", "").startswith("SURFACE:")}
lines = [
    "# GRAPH HEALTH REPORT", "",
    f"- Curated edges: **{len(curated)}**",
    f"- Derived attribution edges: **{len(derived)}**",
    f"- Capability nodes: **{len(caps)}**",
    f"- Query-family nodes: **{len(query_families)}**",
    f"- Search-surface nodes touched: **{len(surface_nodes)}**",
    f"- Capabilities touched by measured search runs: **{sum(1 for c in caps if attention[c['capability_id']] > 0)}**", "",
    "## Highest-priority capability gaps", "",
    "| Capability | Evidence | Components | Graph support | Run attention | Experiments | Gap score | Missing piece |",
    "|---|---|---:|---:|---:|---:|---:|---|"
]
for c in priority:
    s = support[c["capability_id"]]
    lines.append(f"| {c['capability_id']} — {c['name']} | {c.get('evidence_state')} | {s['components']} | {s['graph_support']} | {s['attention']} | {s['experiments']} | {s['gap_score']} | {c.get('missing_piece') or '—'} |")
lines += [
    "", "## Graph policy", "",
    "- High gap score means **information value**, not commercial priority.",
    "- Prefer searches that close a named missing edge in an active experiment over searches that add another similar implementation.",
    "- Query-family and surface nodes preserve discovery provenance without pretending those edges are causal.",
    "- A capability with many repositories but no experiment or outcome edge is a research cluster, not yet a validated asset.",
    "- Independent challengers and negative controls can be more valuable than a second implementation of the same mechanism.", ""
]
(INTEL / "GRAPH_HEALTH.md").write_text("\n".join(lines), encoding="utf-8")
print(f"derived_edges={len(derived)} query_families={len(query_families)} surfaces={len(surface_nodes)}")
