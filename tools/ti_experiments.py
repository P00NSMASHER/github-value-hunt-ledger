#!/usr/bin/env python3
import re
from ti_common import ROOT, INTEL, write_jsonl

queue_text = (ROOT / "SEARCH_QUEUE.md").read_text(encoding="utf-8")
exp_text = (ROOT / "EXPERIMENTS.md").read_text(encoding="utf-8")

priority_weight = {"P0": 3.0, "P0/P1": 2.5, "P1": 2.0, "P1/P2": 1.5, "P2": 1.0}
queue = {}

for line in queue_text.splitlines():
    m = re.match(r"^##\s+\d+\.\s+(.+?)\s+—\s+(P0/P1|P1/P2|P0|P1|P2)(?:\s+/\s+(EXP-\d+))?\s*$", line)
    if not m or not m.group(3):
        continue
    queue[m.group(3)] = {
        "queue_name": m.group(1).strip(),
        "priority": m.group(2),
        "priority_weight": priority_weight[m.group(2)]
    }

heads = list(re.finditer(r"^###\s+(EXP-\d+)\s+—\s+(.+)$", exp_text, re.M))
rows = []

def field(block, label):
    m = re.search(r"^-\s*" + re.escape(label) + r":\s*(.*)$", block, re.I | re.M)
    return m.group(1).strip() if m else None

for i, h in enumerate(heads):
    exp_id = h.group(1)
    block = exp_text[h.end(): heads[i+1].start() if i + 1 < len(heads) else len(exp_text)]
    status_raw = field(block, "Status")
    status = status_raw.replace("*", "").replace(chr(96), "").strip(" .") if status_raw else None
    capabilities_raw = field(block, "Capabilities") or ""
    capabilities = sorted(set(re.findall(r"CAP-\d+", capabilities_raw)))
    q = queue.get(exp_id, {})
    rows.append({
        "experiment_id": exp_id,
        "name": h.group(2).strip(),
        "opportunity": field(block, "Opportunity"),
        "status": status,
        "priority": q.get("priority"),
        "priority_weight": q.get("priority_weight", 1.0),
        "queue_name": q.get("queue_name"),
        "capability_ids": capabilities,
        "hypothesis": field(block, "Hypothesis"),
        "next_action": field(block, "Next action")
    })

rows.sort(key=lambda x: (-x["priority_weight"], x["experiment_id"]))
write_jsonl("experiment_registry.jsonl", rows)

lines = [
    "# EXPERIMENT PORTFOLIO", "",
    "The hunt should optimize for information that unblocks high-priority falsifiable experiments, not simply for more repositories.", "",
    "| Experiment | Priority | State | Capabilities | Next action |",
    "|---|---|---|---|---|"
]
for row in rows:
    lines.append(
        f"| {row['experiment_id']} — {row['name']} | {row.get('priority') or 'unranked'} | "
        f"{row.get('status') or 'unknown'} | {', '.join(row['capability_ids']) or '—'} | "
        f"{row.get('next_action') or '—'} |"
    )

lines += [
    "", "## Allocation principle", "",
    "- P0/P1 priority changes the information value of a search, not the truth of its findings.",
    "- BLOCKED_EXTERNAL experiments should not trigger broad repository hunting when the named blocker is customer data or access.",
    "- READY experiments should generally prefer execution over additional discovery unless execution exposes a concrete missing capability.", ""
]
(INTEL / "EXPERIMENT_PORTFOLIO.md").write_text("\n".join(lines), encoding="utf-8")
print(f"experiments={len(rows)}")
