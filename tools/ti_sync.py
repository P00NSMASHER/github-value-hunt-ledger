#!/usr/bin/env python3
import json
from ti_common import INTEL, load_jsonl, parse_capabilities, parse_search_skills, write_jsonl

caps = parse_capabilities()
write_jsonl("capabilities.jsonl", caps)

strategies = {x["strategy_id"]: x for x in parse_search_skills()}
aliases_path = INTEL / "strategy_aliases.json"
aliases = json.loads(aliases_path.read_text(encoding="utf-8")) if aliases_path.exists() else {}
runs = load_jsonl("search_runs.jsonl")

counts = {}
for run in runs:
    sid = run.get("strategy_id")
    if sid:
        counts[sid] = counts.get(sid, 0) + 1

for sid, count in counts.items():
    if sid in strategies:
        strategies[sid]["observed_run_count"] = count
        continue
    parent = aliases.get(sid)
    strategies[sid] = {
        "strategy_id": sid,
        "name": "Observed strategy variant: " + sid.removeprefix("STRAT:").replace("-", " "),
        "when_to_use": None,
        "procedure": [],
        "why_it_worked": None,
        "examples": [],
        "failure_modes": [],
        "next_improvement": "Formalize this observed variant in SEARCH_SKILLS.md or map it to a parent strategy.",
        "status": "observed_variant" if parent else "unregistered_observed",
        "parent_strategy_id": parent,
        "observed_run_count": count,
        "source_markdown": None
    }

rows = sorted(strategies.values(), key=lambda x: x["strategy_id"])
write_jsonl("search_strategies.jsonl", rows)
print(f"synced capabilities={len(caps)} strategies={len(rows)} observed_variants={sum(1 for x in rows if x['status']!='active')}")
