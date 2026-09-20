#!/usr/bin/env python3
import json
from collections import Counter, defaultdict
import re
from ti_common import ROOT, INTEL, parse_hunter_records, status_bucket

def parse_master_promotions():
    text = (ROOT / "MASTER.md").read_text(encoding="utf-8")
    lines = text.splitlines()
    promoted = set()
    repositories = set()
    heading = re.compile(r"^###\s+([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)(?:\s+—\s+.*)?$")
    for i, line in enumerate(lines):
        match = heading.match(line)
        if not match:
            continue
        repo = match.group(1)
        revision = None
        for j in range(i + 1, min(len(lines), i + 12)):
            if lines[j].startswith("### ") or lines[j].startswith("## "):
                break
            rm = re.search(r"^-\s*(?:Revision|Commit):\s*`?([0-9a-f]{7,40})", lines[j], re.I)
            if rm:
                revision = rm.group(1)
                break
        repositories.add(repo)
        if revision:
            promoted.add((repo, revision))
    return promoted, repositories

master_promotions, master_repositories = parse_master_promotions()
records = parse_hunter_records(include_archive=True)
by_key = {}
repo_sources = defaultdict(set)
catalog_counts = Counter()
state_counts = Counter()

for r in records:
    key = (r["repository"], r["revision"] or "unknown")
    o = by_key.setdefault(key, {
        "repository": r["repository"],
        "revision": r["revision"],
        "observations": 0,
        "statuses": set(),
        "catalogs": set(),
        "states": set()
    })
    o["observations"] += 1
    o["statuses"].add(status_bucket(r.get("status")))
    o["catalogs"].add(r["source_catalog"])
    o["states"].add(r["source_state"])
    repo_sources[r["repository"]].add(r["source_catalog"])
    catalog_counts[r["source_catalog"]] += 1
    state_counts[r["source_state"]] += 1

master_missing_hunter = sum(1 for key in master_promotions if key not in by_key)
for repo, revision in master_promotions:
    key = (repo, revision)
    if key not in by_key:
        by_key[key] = {
            "repository": repo,
            "revision": revision,
            "observations": 0,
            "statuses": {"master"},
            "catalogs": {"MASTER.md"},
            "states": {"master"}
        }
    repo_sources[repo].add("MASTER.md")

status_counts = Counter()
for key, o in by_key.items():
    if key in master_promotions:
        bucket = "master"
    else:
        order = ["strong", "watch", "rejected", "quarantined", "unknown"]
        bucket = next((x for x in order if x in o["statuses"]), "unknown")
    o["registry_bucket"] = bucket
    status_counts[bucket] += 1

top_repeat = sorted(
    [x for x in by_key.values() if x["observations"] > 0],
    key=lambda x: (-x["observations"], x["repository"])
)[:20]
cross_catalog = sum(1 for srcs in repo_sources.values() if len([s for s in srcs if s != "MASTER.md"]) > 1)
unknown_rev = sum(1 for (_, rev) in by_key if rev == "unknown")
unique_repos = len(repo_sources)
unique_repo_revisions = len(by_key)
duplicates = max(0, len(records) - len({(r["repository"], r["revision"] or "unknown") for r in records}))

metrics = {
    "observations": len(records),
    "unique_repositories": unique_repos,
    "unique_repository_revisions": unique_repo_revisions,
    "unknown_revision_records": unknown_rev,
    "duplicate_observations": duplicates,
    "duplicate_observation_rate": (duplicates / len(records)) if records else 0,
    "cross_catalog_repositories": cross_catalog,
    "source_files_scanned": len(catalog_counts),
    "source_state_counts": dict(state_counts),
    "status_counts": dict(status_counts),
    "master_promoted_repositories": len(master_repositories),
    "master_promoted_repo_revisions": len(master_promotions),
    "master_promotions_without_hunter_observation": master_missing_hunter
}
(INTEL / "registry_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

lines = [
    "# REPOSITORY REGISTRY REPORT", "",
    "Generated directly from the hunter Markdown corpus plus the current elite set in MASTER.md.", "",
    f"- Repository observations: **{len(records):,}**",
    f"- Unique repositories (including MASTER-only entries): **{unique_repos:,}**",
    f"- Unique repository/revision keys: **{unique_repo_revisions:,}**",
    f"- Observations beyond the first occurrence of a repo/revision: **{duplicates:,} ({metrics['duplicate_observation_rate']:.1%})**",
    f"- Repo/revision records with unknown revision: **{unknown_rev:,}**",
    f"- Repositories appearing in more than one hunter catalog/file: **{cross_catalog:,}**",
    f"- Hunter Markdown files scanned: **{len(catalog_counts):,}**",
    f"- Current MASTER-promoted repositories: **{len(master_repositories):,}**",
    f"- Current MASTER-promoted exact repo/revisions: **{len(master_promotions):,}**",
    f"- MASTER promotions without a matching hunter-catalog observation: **{master_missing_hunter:,}**", "",
    "## Disposition mix", "",
    "| Bucket | Repo/revision records |",
    "|---|---:|"
]
for k in ["master","strong","watch","rejected","quarantined","unknown"]:
    lines.append(f"| {k} | {status_counts.get(k,0):,} |")

lines += ["", "## Most repeatedly observed repo/revisions", "",
          "| Repository | Revision | Observations | Catalogs | Dispositions |",
          "|---|---|---:|---:|---|"]
for o in top_repeat:
    lines.append(f"| {o['repository']} | {o['revision'] or 'unknown'} | {o['observations']} | {len(o['catalogs'])} | {', '.join(sorted(o['statuses']))} |")

lines += ["", "## Interpretation", "",
          "- MASTER.md is authoritative for elite promotion; hunter prose saying contender/referral does not equal promotion.",
          "- Repeated observations are useful only when they add new evidence, a new revision, a new capability edge or an experiment/outcome link.",
          "- Repeated deep inspections without capability/evidence delta should reduce future search priority.",
          "- Unknown revision records should be resolved before promotion whenever the repository is load-bearing.",
          "- MASTER-only records are retained rather than silently disappearing from registry counts.", ""]

(INTEL / "REGISTRY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps(metrics))
