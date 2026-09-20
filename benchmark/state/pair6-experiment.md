# Pair 6 — EXPERIMENT persistent state

## Validated reusable lessons
- Task 37: For heterogeneous ingestion systems, the strongest evidence is the conjunction of connector implementation + historical-state invariants + semantic regression tests. Provider count alone is insufficient: `PermitBuild` became strong only after source/tests showed append-only `PermitVersion` snapshots, old/new field diffs, monotonic version numbering, and mapping regressions for domain errors such as permit-fee-vs-project-valuation confusion.
- Task 37: Red-team the difference between a broad connector plane and an evidence-grade history plane. `urban-signal` demonstrated a much broader multi-platform municipal ingestion ecosystem and extensive per-city field-map contract tests, but an equivalent immutable permit-version/diff model was not established during this task; breadth should not substitute for the missing target invariant.
- Task 38: The same provider + temporal-evidence + run-health decomposition generalized to government acquisition forecasts. Generic GovCon searches were noisy, while independent symbol searches for source families (`gsa_gateway`, `dhs_apfs`, `state_forecast`), temporal primitives (`first_seen_at`, `history`, `changes`) and run-state semantics (`success`, `partial`, `failed`) converged on `davidlarrimore/curatore-v2`.
- Task 38: Do not accept a `history` field as proof of usable change intelligence. Trace the read path to the actual diff algorithm. In `curatore-v2`, `ForecastService.get_forecast_history()` calls `_compute_history_changes()`, which compares consecutive snapshots and classifies fields into added, removed and modified `{from,to}` values; the CWR primitive exposes those diffs alongside first-seen/last-updated timestamps.
- Task 38: Source-run enums are not sufficient proof of trustworthy feed health. The outer forecast task correctly distinguishes success/partial/failure from processing/error counts, but the APFS fetcher can turn an unexpected response shape into an empty list without raising, creating a false-green zero-record success path. Red-team ingestion systems for empty-success and parser-suppression states.
- Task 38: Identity design is part of version-history correctness. The State connector intentionally excludes volatile fields such as estimated value from row identity and semantic history to reduce false churn, but its title + NAICS + fiscal-year identity can still split continuity if the title itself changes.
- Task 38: Absence of a dedicated domain regression suite should cap evidence quality even when source/schema/migrations are strong. The pinned `backend/tests` tree contains no forecast-specific regression file, so capability existence is strong but production reliability remains less proven.

## Failed search patterns
- Generic repository-name searches such as “building permits municipal data” produced many datasets/dashboards and little durable ingestion logic. They were materially noisier than code/signature searches.
- Several plausible names surfaced through stale/global code indexing but returned 404 on repository fetch. Treat code-index hits as leads only; require canonical repository fetch before spending deep-inspection budget.
- Generic “government acquisition forecast” / “GovCon forecast platform” searches were similarly noisy and tended to return dashboards, datasets or broad procurement tools without temporal provenance or explicit source-run semantics. Use them for vocabulary only, then pivot to invariant symbols.

## Useful terminology / signatures
- `permit_versions`, `PermitVersion`, `changed_fields`, immutable snapshot, version-number race, same-batch duplicate permit number.
- `field-completeness audit`, fee-vs-valuation, source-schema metadata audit, field-map regression, non-unique permit identifier, mapping semantic QA.
- Provider-family signatures: Socrata, ArcGIS FeatureServer, Accela/Citizen Access, CKAN, CARTO plus jurisdiction-level mapping configuration.
- Acquisition-forecast signatures: `gsa_gateway`, `dhs_apfs`, `state_forecast`, `ForecastSync`, `first_seen_at`, `last_updated_at`, JSONB `history`, `get_forecast_history`, `_compute_history_changes`, `last_sync_status`, `partial`, `failed`.
- Reliability anti-pattern to search for: parser/fetch layers returning `[]` after structural-response errors while outer orchestration interprets zero errors as success.

## Candidate search skill — two-task evidence, eligible for promotion later
- SKILL NAME: Invariant-triad code search for ingestion planes
  - WHEN TO USE: A benchmark asks for a heterogeneous ingestion platform where historical correctness, semantic normalization and operational source health matter more than frontend breadth.
  - PROCEDURE: Search separately for (1) connector-family/provider signatures, (2) immutable/version/diff primitives, and (3) domain-semantic or run-health invariants; intersect candidates only after each axis is evidenced in source/tests/schema/history. Then independently trace the diff algorithm and red-team whether a source can false-green an empty/invalid fetch.
  - WHY IT WORKED ON TASK 37: It surfaced the zero-star `adamleap02/PermitBuild`, whose connector + append-only version/diff + semantic mapping-QA combination was much clearer in source/tests than in generic repository-name search.
  - WHY IT WORKED ON TASK 38: It surfaced `davidlarrimore/curatore-v2`, where GSA/DHS/State connector signatures intersected with explicit history/diff code and success/partial/failure orchestration; generic GovCon searches were materially noisier.
  - FAILURE MODES: Field/status names can be decorative; require execution-path verification. Stored snapshots are not enough unless a usable diff/read path exists. Run-state enums can still conceal false-green parser behavior. Identity keys can break continuity even when history arrays are correct.
  - STATUS: supported by two distinct benchmark tasks (37 and 38), therefore eligible for later SEARCH_SKILLS promotion under the benchmark rule. Not promoted in this write to avoid widening benchmark scope and central-file race risk.
