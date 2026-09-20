# Pair 2 — EXPERIMENT persistent state

## Task completion
- 09 — COMPLETE (2026-09-20): official FAR machine-source/provenance benchmark completed with GSA/GSA-Acquisition-FAR at `da52ccbbe114e1f031a7f4c59195c508dbfa485f` as the accepted strong candidate.
- 10 — COMPLETE (2026-09-20): official federal spending backend/ETL benchmark completed with fedspendingtransparency/usaspending-api at `1692d484b38c66361c54faa221548527cae29964` as the accepted strong candidate.
- 11 — UNFINISHED
- 12 — UNFINISHED
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

## Failed search patterns
- Treating eCFR alone as the complete answer for acquisition automation: authoritative machine-readable regulation, but Task 09 did not verify solicitation-specific fill-in semantics there.
- Treating Federal Register alone as the complete corpus: strong amendment provenance, but not the consolidated current clause/provision source needed for fill-in extraction.
- Inferring current regulatory version from README date strings without checking commit history and the official publication surface.
- Treating a repository ending in `-api` as an endpoint wrapper without source inspection. Task 10 showed that `usaspending-api` also owns substantial ETL, normalization, derived award state and test-backed schema logic.
- Treating the upstream DATA Act Broker as interchangeable with the public USAspending data plane. They are connected but implement different authority/normalization stages.
- Using the obsolete historic-loader section of `loading_data.md` as current production evidence; current evidence came from the Broker-backed loader, models, integration tests and exact history.

## Useful terminology / signatures
- `xtrf="GFI"` — GSA FAR Global Fill-in marker for clause/provision input fields.
- `FM MARKER` / `FM AREA` — documented FAR/FAC/FAR Council production change comments keyed by case number.
- DITA `concept` / `conbody` / `section` / `lines` structure in the FAR source corpus.
- `load_submission`, `published_award_financial`, `update_c_to_d_linkages` — Task 10 signatures for the live DATA Act submission-to-USAspending ETL boundary.
- `vw_transaction_normalized`, `AwardSearch`, `TransactionSearch` — Task 10 signatures for derived award/search state rather than raw endpoint proxying.
- `recipient_uei`, `recipient_hash`, `parent_uei`, `generated_unique_award_id`, `distinct_award_key` — identity/provenance fields worth following in Task 11.

## Candidate search skills
- **Production-source triangulation for official systems**: start from a first-party publication/API surface, follow it to the source repository, inspect operational markup or transformation code, pin exact revision/history, verify internal schemas/tests, and compare adjacent first-party pipeline stages. Validated independently on Task 09 (FAR production corpus) and Task 10 (USAspending backend/ETL). This now meets the two-task evidence threshold for possible SEARCH_SKILLS.md promotion, but was not promoted during this run.
