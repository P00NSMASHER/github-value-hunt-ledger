# Pair 6 — EXPERIMENT persistent state

## Validated reusable lessons
- Task 37: For heterogeneous ingestion systems, the strongest evidence is the conjunction of connector implementation + historical-state invariants + semantic regression tests. Provider count alone is insufficient: `PermitBuild` became strong only after source/tests showed append-only `PermitVersion` snapshots, old/new field diffs, monotonic version numbering, and mapping regressions for domain errors such as permit-fee-vs-project-valuation confusion.
- Task 37: Red-team the difference between a broad connector plane and an evidence-grade history plane. `urban-signal` demonstrated a much broader multi-platform municipal ingestion ecosystem and extensive per-city field-map contract tests, but an equivalent immutable permit-version/diff model was not established during this task; breadth should not substitute for the missing target invariant.

## Failed search patterns
- Generic repository-name searches such as “building permits municipal data” produced many datasets/dashboards and little durable ingestion logic. They were materially noisier than code/signature searches.
- Several plausible names surfaced through stale/global code indexing but returned 404 on repository fetch. Treat code-index hits as leads only; require canonical repository fetch before spending deep-inspection budget.

## Useful terminology / signatures
- `permit_versions`, `PermitVersion`, `changed_fields`, immutable snapshot, version-number race, same-batch duplicate permit number.
- `field-completeness audit`, fee-vs-valuation, source-schema metadata audit, field-map regression, non-unique permit identifier, mapping semantic QA.
- Provider-family signatures: Socrata, ArcGIS FeatureServer, Accela/Citizen Access, CKAN, CARTO plus jurisdiction-level mapping configuration.

## Candidate search skills awaiting second-task confirmation
- SKILL NAME: Invariant-triad code search for ingestion planes
  - WHEN TO USE: A benchmark asks for a heterogeneous ingestion platform where historical correctness and semantic normalization matter more than frontend breadth.
  - PROCEDURE: Search separately for (1) connector-family/provider signatures, (2) immutable/version/diff primitives, and (3) domain-semantic regression vocabulary; intersect candidates only after each axis is evidenced in source/tests/history. Red-team whether “history” is just a mutable latest-state table and whether “mapping QA” tests semantics rather than key presence.
  - WHY IT WORKED ON TASK 37: It surfaced the zero-star `adamleap02/PermitBuild`, whose exact target combination was much clearer in source/tests than in generic repository-name search.
  - STATUS: one-task evidence only; do not promote to SEARCH_SKILLS until it succeeds on another distinct benchmark task or Hunt 15 approves it.
