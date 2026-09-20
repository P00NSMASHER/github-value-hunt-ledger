#!/usr/bin/env python3
import json
from collections import Counter, defaultdict
from ti_common import INTEL, parse_hunter_records, status_bucket

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

status_counts = Counter()
for o in by_key.values():
    order = ["master", "strong", "watch", "rejected", "quarantined", "unknown"]
    bucket = next((x for x in order if x in o["statuses"]), "unknown")
    status_counts[bucket] += 1

top_repeat = sorted(by_key.values(), key=lambda x: (-x["observations"], x["repository"]))[:20]
cross_catalog = sum(1 for srcs in repo_sources.values() if len(srcs) > 1)
unknown_rev = sum(1 for (_, rev) in by_key if rev == "unknown")
unique_repos = len(repo_sources)
unique_repo_revisions = len(by_key)
duplicates = max(0, len(records) - unique_repo_revisions)

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
    "status_counts": dict(status_counts)
}
(INTEL / "registry_metrics.json").write_text(json.dumps(metrics, indent=2) + "\n", encoding="utf-8")

lines = [
    "# REPOSITORY REGISTRY REPORT", "",
    "Generated directly from the hunter Markdown corpus; no monolithic registry file is round-tripped through the GitHub connector.", "",
    f"- Repository observations: **{len(records):,}**",
    f"- Unique repositories: **{unique_repos:,}**",
    f"- Unique repository/revision keys: **{unique_repo_revisions:,}**",
    f"- Observations beyond the first occurrence of a repo/revision: **{duplicates:,} ({metrics['duplicate_observation_rate']:.1%})**",
    f"- Repo/revision records with unknown revision: **{unknown_rev:,}**",
    f"- Repositories appearing in more than one catalog/file: **{cross_catalog:,}**",
    f"- Hunter Markdown files scanned: **{len(catalog_counts):,}**", "",
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
          "- Repeated observations are useful only when they add new evidence, a new revision, a new capability edge or an experiment/outcome link.",
          "- A high duplicate-observation rate is not automatically bad, but repeated deep inspections without capability/evidence delta should reduce future search priority.",
          "- Unknown revision records should be resolved before promotion whenever the repository is load-bearing.",
          "- This registry is recomputed from source catalogs, so it cannot silently lose older records because of connector truncation.", ""]

(INTEL / "REGISTRY_REPORT.md").write_text("\n".join(lines), encoding="utf-8")
print(json.dumps(metrics))
