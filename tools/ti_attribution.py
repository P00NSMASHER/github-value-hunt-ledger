#!/usr/bin/env python3
import json
from collections import defaultdict
from ti_common import INTEL, load_jsonl, slug

runs = {r["search_run_id"]: r for r in load_jsonl("search_runs.jsonl")}
outs = [o for o in load_jsonl("outcomes.jsonl") if o.get("result") != "INVALID"]
strategies = {s["strategy_id"]: s for s in load_jsonl("search_strategies.jsonl")}
strategy_aliases = json.loads((INTEL / "strategy_aliases.json").read_text(encoding="utf-8")) if (INTEL / "strategy_aliases.json").exists() else {}
query_aliases = json.loads((INTEL / "query_family_aliases.json").read_text(encoding="utf-8")) if (INTEL / "query_family_aliases.json").exists() else {}

def canonical_strategy(sid):
    s = strategies.get(sid)
    if s and s.get("parent_strategy_id"):
        return s["parent_strategy_id"]
    return strategy_aliases.get(sid, sid)

def qfid(run):
    raw = "QF:" + (slug(run.get("query_family") or "unknown")[:120] or "unknown")
    return query_aliases.get(raw, raw)

def add(bucket, key, outcome, share):
    x = bucket.setdefault(key, {
        "assisted_outcomes": set(),
        "fractional_outcome_equivalents": 0.0,
        "fractional_passed_equivalents": 0.0,
        "revenue_usd_credit": 0.0,
        "customer_value_usd_credit": 0.0,
        "engineering_days_saved_low_credit": 0.0,
        "engineering_days_saved_high_credit": 0.0
    })
    x["assisted_outcomes"].add(outcome["outcome_id"])
    x["fractional_outcome_equivalents"] += share
    if outcome.get("result") == "PASSED":
        x["fractional_passed_equivalents"] += share
    x["revenue_usd_credit"] += (outcome.get("revenue_usd") or 0) * share
    x["customer_value_usd_credit"] += (outcome.get("customer_value_usd") or 0) * share
    x["engineering_days_saved_low_credit"] += (outcome.get("engineering_days_saved_low") or 0) * share
    x["engineering_days_saved_high_credit"] += (outcome.get("engineering_days_saved_high") or 0) * share

by_strategy, by_query, by_surface, by_run = {}, {}, {}, {}
outcome_rows = []
for o in outs:
    origins = []
    seen = set()
    for rid in o.get("origin_search_ids", []):
        if rid in runs and rid not in seen:
            origins.append(rid); seen.add(rid)
    if not origins:
        continue
    run_share = 1.0 / len(origins)
    outcome_rows.append({
        "outcome_id": o["outcome_id"],
        "result": o.get("result"),
        "origin_count": len(origins),
        "credit_per_origin": run_share,
        "revenue_usd": o.get("revenue_usd"),
        "customer_value_usd": o.get("customer_value_usd")
    })
    for rid in origins:
        r = runs[rid]
        add(by_run, rid, o, run_share)
        add(by_strategy, canonical_strategy(r.get("strategy_id")), o, run_share)
        add(by_query, qfid(r), o, run_share)
        surfaces = sorted(set(r.get("search_surfaces") or []))
        if surfaces:
            surface_share = run_share / len(surfaces)
            for s in surfaces:
                add(by_surface, "SURFACE:" + slug(s), o, surface_share)

def freeze(bucket):
    rows = []
    for key, x in bucket.items():
        y = dict(x)
        y["id"] = key
        y["assisted_outcome_count"] = len(y.pop("assisted_outcomes"))
        rows.append(y)
    return sorted(rows, key=lambda x: (-x["fractional_outcome_equivalents"], x["id"]))

metrics = {
    "method": "equal_touch_across_unique_origin_runs; surface credit additionally split across surfaces used by each credited run",
    "causal_claim": False,
    "valid_outcomes": len(outs),
    "outcomes_with_attributable_origins": len(outcome_rows),
    "outcomes": outcome_rows,
    "by_run": freeze(by_run),
    "by_strategy": freeze(by_strategy),
    "by_query_family": freeze(by_query),
    "by_surface": freeze(by_surface),
    "totals": {
        "revenue_usd": sum((o.get("revenue_usd") or 0) for o in outs),
        "customer_value_usd": sum((o.get("customer_value_usd") or 0) for o in outs),
        "engineering_days_saved_low": sum((o.get("engineering_days_saved_low") or 0) for o in outs),
        "engineering_days_saved_high": sum((o.get("engineering_days_saved_high") or 0) for o in outs)
    }
}
(INTEL / "attribution_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

lines = [
    "# OUTCOME ATTRIBUTION REPORT", "",
    "This is an accounting attribution layer, **not a causal claim**. When an outcome cites multiple origin search runs, realized value is split equally across those unique runs. Each run remains an assisted contributor. Surface-level credit is split again across the surfaces used by that run.", "",
    f"- Valid outcomes: **{len(outs)}**",
    f"- Outcomes with attributable search origins: **{len(outcome_rows)}**", "",
    "## Strategy attribution", "",
    "| Strategy | Assisted outcomes | Fractional outcome eq. | Passed eq. | Revenue credit | Customer-value credit | Engineering-days credit |",
    "|---|---:|---:|---:|---:|---:|---|"
]
for x in metrics["by_strategy"]:
    lines.append(
        f"| {x['id']} | {x['assisted_outcome_count']} | {x['fractional_outcome_equivalents']:.2f} | "
        f"{x['fractional_passed_equivalents']:.2f} | ${x['revenue_usd_credit']:,.0f} | "
        f"${x['customer_value_usd_credit']:,.0f} | "
        f"{x['engineering_days_saved_low_credit']:.1f}–{x['engineering_days_saved_high_credit']:.1f} |"
    )
if not metrics["by_strategy"]:
    lines.append("| — | 0 | 0.00 | 0.00 | $0 | $0 | 0–0 |")

lines += ["", "## Attribution guardrails", "",
          "- Equal-touch credit prevents the same realized dollars from being counted in full for every origin run.",
          "- Assisted-outcome counts are useful for lineage; fractional value credit is useful for accounting; neither proves causal contribution.",
          "- Do not infer that a strategy causes revenue until controlled or repeated outcome evidence exists.",
          "- Outcome values remain zero/null unless directly evidenced in OUTCOMES.md / outcomes.jsonl.", ""]
(INTEL / "ATTRIBUTION_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps({"valid_outcomes": len(outs), "attributable": len(outcome_rows)}))
