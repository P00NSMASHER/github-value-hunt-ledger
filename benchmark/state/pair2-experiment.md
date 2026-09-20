# Pair 2 — EXPERIMENT persistent state

## Task completion
- 09 — COMPLETE (2026-09-20): official FAR machine-source/provenance benchmark completed with GSA/GSA-Acquisition-FAR at `da52ccbbe114e1f031a7f4c59195c508dbfa485f` as the accepted strong candidate.
- 10 — COMPLETE (2026-09-20): official federal spending backend/ETL benchmark completed with fedspendingtransparency/usaspending-api at `1692d484b38c66361c54faa221548527cae29964` as the accepted strong candidate.
- 11 — COMPLETE (2026-09-20): official DATA Act award/entity normalization benchmark completed with fedspendingtransparency/data-act-broker-backend at `76dcae4ccbf6951223608bc1d8fd0c5b03da5d68` as the accepted strong candidate.
- 12 — COMPLETE (2026-09-20): heterogeneous restore-verification benchmark completed with RamazanKara/restore-drill at `dea374da3b340f53b798112eee82bd7ed1224572` as STRONG, with an explicit zero-check false-green caveat.
- 13 — UNFINISHED
- 14 — UNFINISHED
- 15 — UNFINISHED

## Validated reusable lessons
- On official regulatory/procurement corpora, the public reading website can be weaker for automation than the agency's production-source repository. In Task 09, the GSA DITA source exposed solicitation fill-ins (`xtrf="GFI"`) and documented FM change-marker conventions that were not the point of the rendered reading surface.
- README version text is not sufficient evidence of currentness. Task 09's README snapshot information lagged later repository history, so exact commit pinning plus history and independent first-party publication cross-checks are required.
- Negative verification is useful: Task 09 did not substantiate a repo-local acquisition-specific XSD, so schema claims must remain limited to the standard DITA DOCTYPE/schema family actually observed.
- Task 10 independently confirmed the broader production-source triangulation pattern on an official data platform: the public API name/surface understated the repository's actual role. Source inspection exposed Broker ingestion, award/account transformations, normalized Django/search schemas, materialized-view/data-loader setup and integration tests. For official systems, require operational transform code + internal schema + tests/fixtures + exact deploy/history evidence before calling a repository the real backend.
- Distinguish pipeline stages instead of collapsing all first-party repositories into one authority claim. For Task 10, `data-act-broker-backend` is the upstream DATA Act submission/validation plane, while `usaspending-api` is the downstream USAspending normalization/public-serving backend. The exact commercial capability depends on which boundary is being reused.
- An exact production-deploy commit is stronger evidence than repository activity timestamps. Task 10 pinned master at the signed `Sprint 225 Prod Deploy` merge rather than assuming later pushes on other refs were deployed.
- Task 11 showed that evidence-grade identity claims need executable conflict behavior, not just identifier columns. The Broker's SAM recipient loader rejects inconsistent DUNS/UEI matches with `ValueError`, while its deterministic award keys encode PIID/agency/referenced-IDV context and its C11 rule tests PIID/ParentAwardId linkage across reporting files.
- For entity/award normalization, keep source-system identity, canonical normalized identity and downstream public-serving aggregation as separate layers. The Broker normalizes SAM/contract source semantics; `usaspending-api` consumes that plane for downstream award/search state.
- Task 12 showed that restore verification should be evaluated as a chain, not a backup-status feature: scratch target creation → real provider restore → post-restore semantic checks → expected/actual evidence → preserved failure state. `restore-drill` implements and integration-tests that chain across PostgreSQL, MySQL/MariaDB, Redis and etcd.
- Exact-revision integration CI materially strengthened Task 12. The pinned commit's CI succeeded with real Docker provider integration tests and a Kubernetes smoke path, so the core recovery claims were not inferred from README prose alone.
- Task 12 also exposed an important trusted-state boundary failure: configuration validation permits zero checks, while the engine initializes `allPassed := true`; therefore a successful restore can yield `ValidationPassed=true` without a semantic assertion. Strong restore coverage does not substitute for a minimum-evidence gate.
- Machine-readable evidence can be independently inspectable without being tamper-evident. Task 12's result schema preserves provider/status/timing and per-check expected/actual/pass/error state, and incident mode can retain the restored target for external inspection, but no cryptographic binding of the report to the backup artifact/config was verified.
- Operational-readiness evidence must include current negative signals. On 2026-09-20, the scheduled `govulncheck` workflow for the pinned Task 12 commit failed; the failure was recorded as an operational caveat rather than converted into an unverified vulnerability claim.

## Failed search patterns
- Treating eCFR alone as the complete answer for acquisition automation: authoritative machine-readable regulation, but Task 09 did not verify solicitation-specific fill-in semantics there.
- Treating Federal Register alone as the complete corpus: strong amendment provenance, but not the consolidated current clause/provision source needed for fill-in extraction.
- Inferring current regulatory version from README date strings without checking commit history and the official publication surface.
- Treating a repository ending in `-api` as an endpoint wrapper without source inspection. Task 10 showed that `usaspending-api` also owns substantial ETL, normalization, derived award state and test-backed schema logic.
- Treating the upstream DATA Act Broker as interchangeable with the public USAspending data plane. They are connected but implement different authority/normalization stages.
- Using the obsolete historic-loader section of `loading_data.md` as current production evidence; current evidence came from the Broker-backed loader, models, integration tests and exact history.
- Treating UEI/DUNS/name fields alone as proof of entity resolution. Task 11's strong evidence came from source mappings, deterministic reference keys and a negative ambiguity test; no fuzzy name/address resolver was verified.
- Treating C11 as universal award-linkage proof. It is conditional on a non-null obligation and has allocation-transfer-agency exceptions, so its semantics must not be generalized beyond the tested rule.
- Treating “restore command exited zero” as equivalent to verified recovery. Task 12 required post-restore database/keyspace assertions with expected/actual evidence and real integration fixtures.
- Treating report generation as proof of fail-closed semantics. Task 12 found that an empty validation-check list can still produce a passed validation state, so configuration preconditions must be traced to the trusted PASS transition.
- Treating JSON/HTML evidence as cryptographic attestation. Task 12 verified inspectable evidence but not signatures/hashes binding each drill report to the exact backup artifact and config.

## Useful terminology / signatures
- `xtrf="GFI"` — GSA FAR Global Fill-in marker for clause/provision input fields.
- `FM MARKER` / `FM AREA` — documented FAR/FAC/FAR Council production change comments keyed by case number.
- DITA `concept` / `conbody` / `section` / `lines` structure in the FAR source corpus.
- `load_submission`, `published_award_financial`, `update_c_to_d_linkages` — Task 10 signatures for the live DATA Act submission-to-USAspending ETL boundary.
- `vw_transaction_normalized`, `AwardSearch`, `TransactionSearch` — Task 10 signatures for derived award/search state rather than raw endpoint proxying.
- `recipient_uei`, `recipient_hash`, `parent_uei`, `generated_unique_award_id`, `distinct_award_key` — identity/provenance fields worth following in Task 11.
- `SAMRecipient`, `SAM_ENTITY_MAPPINGS`, `ultimate_parent_uei`, `parent_award_id`, `referenced_idv_agency_iden`, `unique_award_key` — Task 11 signatures for authoritative recipient hierarchy plus referenced-award semantics.
- `c11_cross_file` — Task 11 cross-file rule requiring File C PIID or PIID/ParentAwardId combinations to exist in File D1 under the rule's stated conditions.
- `ValidationPassed`, `CheckResult.Expected`, `CheckResult.Actual`, `CleanupSkipped`, `TargetID`, `TargetHost`, `TargetPorts` — Task 12 signatures for the restore-evidence trusted-state boundary and independently inspectable retained targets.
- `RESTORE_DRILL_INTEGRATION=1` plus real Docker fixture generation — Task 12 signature for distinguishing operational recovery tests from mocked provider adapters.

## Candidate search skills
- **Production-source triangulation for official systems**: start from a first-party publication/API surface, follow it to the source repository, inspect operational markup or transformation code, pin exact revision/history, verify internal schemas/tests, and compare adjacent first-party pipeline stages. Validated independently on Task 09 (FAR production corpus) and Task 10 (USAspending backend/ETL). This now meets the two-task evidence threshold for possible SEARCH_SKILLS.md promotion, but was not promoted during this run.
- **Identity graph invariant triad**: for entity-resolution/award-lineage systems, require (1) authoritative source-system identifier/hierarchy ingestion, (2) deterministic compound identity/reference keys, and (3) negative tests that reject ambiguous identities or broken references. Task 11 validates this once; do not promote until it succeeds on another distinct benchmark task or Hunt 15 approves it.
- **Restore-verification invariant quartet**: require (1) a real scratch restore, (2) post-restore semantic assertions, (3) evidence preserving expected/actual/error state, and (4) negative lifecycle/integration tests; then trace the exact PASS transition back through configuration and require a minimum-check invariant. Task 12 validates this once. Do not promote to SEARCH_SKILLS until it succeeds on another distinct benchmark task or Hunt 15 approves it.
