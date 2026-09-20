# Pair 2 — EXPERIMENT results

Frozen benchmark result log. Append one task result block per scheduled run. Do not rewrite prior completed blocks.

## TASK 09 — Acquisition rule provenance
DATE: 2026-09-20
STATUS: COMPLETE

HYPOTHESIS:
An official first-party FAR production source exists in machine-readable form that preserves more procurement semantics than rendered regulation text alone—specifically clause/provision structure, solicitation fill-ins, and identifiable change/revision provenance. Falsification condition: no first-party source could be verified beyond rendered HTML, or machine-readable sources lacked either fill-in semantics or auditable revision/change provenance.

DISCOVERY MODES USED:
1. Direct domain/authority search across GSA/Acquisition.gov, eCFR and Federal Register first-party sources.
2. Code/file/markup inspection of the candidate source corpus, including exact DITA clause XML and acquisition-specific markup conventions.
3. Commit/history archaeology at an exact Git revision, including recent Federal Management/FAR production-fix commits and source-sync history.
4. Independent authority cross-check against Acquisition.gov, eCFR and Federal Register rather than relying on repository claims alone.

CANDIDATES CONSIDERED:
- GSA/GSA-Acquisition-FAR — official GSA source DITA XML used to create the FAR at Acquisition.gov; strongest match.
- eCFR API / Title 48 machine-readable regulatory text — authoritative structure/date source, but no verified FAR solicitation fill-in semantics or equivalent case-local production markers.
- Federal Register API/documents — authoritative amendment/rulemaking provenance, but not a consolidated current clause/provision corpus with structured fill-ins.
- Acquisition.gov rendered FAR pages — authoritative reading surface, but less useful as the machine-source substrate than the GSA DITA corpus.

BEST CANDIDATE:
GSA/GSA-Acquisition-FAR
Canonical URL: https://github.com/GSA/GSA-Acquisition-FAR

EXACT REVISION / VERSION:
da52ccbbe114e1f031a7f4c59195c508dbfa485f (master observed 2026-09-20); tree b17931d0739d432eb448a39f6cb99b300ae7ed49; parent 298318be7a6fd4dc1546b7a12b08a1072502b3f6.

VERIFIED EVIDENCE:
- Repository metadata identifies the project as GSA's "Source DITA XML for the Federal Acquisition Regulation."
- README at the exact revision states the DITA XML is used to create the FAR at Acquisition.gov and describes machine conversion into DITA with special handling for Multi-Line Text Fields and prescription references.
- README documents acquisition-specific Global Fill-in semantics: `xtrf="GFI"` marks clause/provision fields requiring solicitation/contract input.
- Real source file `dita/52.203-14.dita` was inspected at the exact revision. It is structured DITA (`concept`, `conbody`, `section`, ordered-list/list-item/paragraph elements) and contains multiple `<lines ... xtrf="GFI">` fill-in regions, including blank underscore lines. The clause title itself preserves its regulatory revision label: `52.203-14 Display of Hotline Poster(s). (NOV 2021)`.
- README documents production change markers `FM MARKER` and `FM AREA` keyed by case number for FAR/FAC/FAR Council text changes.
- Git history independently verifies active revision provenance. Recent commits include `7d81e616dee28495d3d3d066fd4bea7edf46fbee` (`Resolve 2026-01 FM and Technical errors`) and `fc9b64f57d28fb519be9a23102ab67452c35796e` (`sync with gsa-far-api`).
- Exact Git commit/tree/parent identity was verified, so downstream parsers/diff engines can pin a reproducible corpus state rather than relying on a mutable website.
- Standard DITA DOCTYPE/schema family is present in the inspected clause source. No repository-local acquisition-specific XSD was verified in this run; attempts to locate one did not substantiate that claim.
- Official Acquisition.gov/eCFR/Federal Register surfaces were used as authority cross-checks. Federal Register case-based rulemaking corroborates that FAR case identifiers are real regulatory provenance, but the strongest machine-production substrate verified here is the GSA DITA repository.

SPECIALIST PASSES:
- SOURCE/AUTHORITY VALIDATOR: verified first-party GSA ownership and the README's explicit Acquisition.gov production role; compared eCFR/Federal Register/Acquisition.gov alternatives.
- CODE/MARKUP INSPECTOR: inspected a real clause file at the pinned commit and verified structural DITA markup plus `xtrf="GFI"` fill-ins; explicitly failed to verify a custom repo-local XSD.
- HISTORY/PROVENANCE ANALYST: pinned commit/tree/parent and checked recent commit history for FM corrections and API synchronization.
- COMMERCIAL ANALYST: identified buyers as GovCon/acquisition software vendors, solicitation builders, contract-compliance systems and procurement teams. First paid wedge: a revision-aware FAR clause diff + fill-in extractor/exporter for one solicitation/award workflow; adjacent wedge: authoritative rule-update feed and clause matrix automation.

RED-TEAM / VERIFIER:
VERDICT: STRONG / ACCEPT.
Independent objections that survived review:
- README freshness is not sufficient evidence of current regulatory state; its stated FAC snapshot can lag later repository history. Production use must pin exact commits and reconcile against current official acquisition sources.
- The README acknowledges machine conversion required human intervention for irregular/missing tags, so a parser must tolerate source anomalies rather than assume perfect regularity.
- FM comments are useful provenance metadata, not by themselves a complete semantic amendment graph; a defensible revision tracker should combine corpus diffs, Git history and official FAC/Federal Register metadata.
- The inspected clause proves standard DITA structure and GFI fill-ins, but no custom acquisition-specific XSD was verified.
- Public repository license metadata was null in the observed repository metadata. Record provenance exactly; the user's standing separate repository-code authorization applies only to repository-owned material and not automatically to third-party tooling or independently owned assets.
Despite these objections, the first-party machine-readable corpus directly satisfies the benchmark's core requirement: structured FAR source, explicit solicitation fill-ins, and reproducible revision/change provenance.

SCORE:
A 4/5 — straightforward paid wedge for clause-diff/fill-in/solicitation automation.
B 4/5 — meaningful GovCon/procurement value, though the buyer universe is specialized.
C 5/5 — compresses substantial FAR parsing, curation and provenance engineering.
D 5/5 — rare first-party production corpus with procurement-specific fill-in and change conventions.
E 5/5 — repository role, real source markup, exact revision and history independently verified.
F 4/5 — official first-party source and reproducible revision, with public-license metadata/third-party boundary caveats.
TOTAL: 27/30.

COMMERCIAL INTERPRETATION:
The repository is a strong substrate for a procurement-diff engine rather than merely a reference corpus. A product can pin an exact FAR corpus revision, extract clause/provision fill-ins, generate clause matrices or solicitation templates, and diff later corpus revisions while attaching case/history provenance. The immediate money path is reduced manual acquisition/legal reconciliation and lower risk of stale or incorrectly populated clauses.

WHAT FAILED:
- eCFR alone did not verify the acquisition-specific fill-in semantics needed for solicitation automation.
- Federal Register alone provides amendment provenance but not the consolidated current clause/provision corpus.
- Repository-local acquisition-specific XSD/specialization files were not substantiated; do not promote that claim without a new source.
- README dates cannot be treated as the corpus's current regulatory version without commit/source reconciliation.

SEARCH-SKILL LESSON:
For official rule corpora, search the production-source repository rather than only the public reading website. Then triangulate three evidence layers: (1) source markup semantics, (2) exact commit/history provenance, and (3) a separate first-party publication/rulemaking authority. Acquisition-specific operational metadata may hide in markup attributes/comments rather than file names or README headlines.

NEXT QUERY IF REOPENED:
Trace `FM MARKER`/`FM AREA` case identifiers across multiple historical commits and join them to official Federal Register/FAC metadata to test whether a deterministic case→changed-clause provenance graph can be generated without manual interpretation.

SEARCH-SKILLS PROMOTION: NO — this is the first benchmark-task success for the lesson; protocol requires success on at least two distinct benchmark tasks or Hunt 15 approval before promotion.

TASK: 10 — Official federal spending backend/ETL
CONDITION: EXPERIMENT
STARTING HYPOTHESIS: The first-party `fedspendingtransparency/usaspending-api` repository is the production USAspending backend and contains real loaders, normalized schemas, transformations, linkages and tests; it should therefore satisfy the task only if source inspection disproves the superficial interpretation that it merely wraps public API endpoints. Falsification condition: endpoint/view code without authoritative loading/normalization logic, no internal schemas/tests, or evidence that another first-party repository is the actual public-spending data plane.
DISCOVERY METHODS: (1) direct first-party authority search across USAspending/Treasury and the `fedspendingtransparency` organization; (2) code/file/schema-oriented inspection of loaders, transformation helpers and Django search models; (3) tests/fixture inspection of Broker-backed ETL and award derivations; (4) commit/history and ecosystem comparison against the upstream `data-act-broker-backend` to distinguish submission validation from the downstream USAspending normalization/public-serving plane.
CANDIDATE: fedspendingtransparency/usaspending-api
CANONICAL URL: https://github.com/fedspendingtransparency/usaspending-api
EXACT REVISION: `1692d484b38c66361c54faa221548527cae29964` (master observed 2026-09-20; tree `31d234aa09a37d1acbfdca4a18d8b307bcc9e0bf`; production-deploy merge message `Sprint 225 Prod Deploy`).
VERDICT: STRONG
A-F SCORE: A4 B5 C5 D5 E5 F5 = 29/30
EVIDENCE INSPECTED: First-party repository metadata/CC0-1.0 provenance and exact master commit; exact-revision README; `loading_data.md`; `data_reformatting.md`; `usaspending_api/etl/management/commands/load_submission.py`; `usaspending_api/etl/submission_loader_helpers/file_c.py`; `usaspending_api/etl/award_helpers.py`; `usaspending_api/search/models/transaction_search.py`; ETL test tree and `test_load_submission_mgmt_cmd.py`; `test_award_helpers.py`; ETL commit history; official `api.usaspending.gov` documentation; and the same-org upstream `data-act-broker-backend` as a pipeline-stage comparator.
CLAIMS VERIFIED: The README says this API is used by USAspending.gov to obtain federal spending data and provides local PostgreSQL/OpenSearch/database-migration/materialized-view/data-loader setup rather than only endpoint examples. `loading_data.md` documents loading certified Data Broker submissions and the A/B/D2/D1/C/subaward sequence. `load_submission.py` opens the Broker data plane, validates a submission, loads Files A/B/C under an atomic transaction and exposes optional File-C-to-D linkage behavior. `file_c.py` implements real transformations: filtering meaningful File C rows, object-class/program-activity/TAS enrichment, sign reversal of CPE/FYB and `transaction_obligated_amount`, missing-TAS skip accounting, a deterministic distinct-award key, and contract/assistance C-to-D linkage. `data_reformatting.md` independently documents canonicalization, agency enrichment, award-holder construction, federal-account derivation, quarter-from-cumulative derivation and accounting-sign normalization. `award_helpers.py` derives award-level state from earliest/latest transactions and aggregate obligations/funding, including procurement and subaward rollups. `TransactionSearch` exposes a large normalized internal schema spanning award/transaction keys, agencies, recipient identity/UEI/hash/parent fields, locations, TAS/federal accounts and money fields. Integration tests use a Broker test database, call the real loader, exercise FAIN/URI/PIID-parent award linkages and the skip-linkage negative case; award-helper tests verify earliest/latest transaction semantics and obligation/base-option aggregation. Repository history includes a signed master production-deploy merge and active 2026 ETL test/Delta maintenance. The official USAspending API site states Treasury is building the open-source suite to deliver standardized federal spending data and points users to the codebase.
CLAIMS NOT VERIFIED: This repository was not proven to contain every production ETL step; source comments explicitly note some C-to-D linkage also occurs in subsequent Databricks steps. USAspending is not the origin authority for every raw award fact—Data Broker and upstream award systems supply source records—so “authoritative” here means the official production normalization/public-serving schema and transformations, not an assertion that this repository creates the underlying agency facts. The repository had later pushes on non-master refs after the pinned 2026-09-01 master production merge, so those later changes were not assumed deployed. The obsolete historic-loader section in `loading_data.md` was not used as current evidence.
STRONGEST OBJECTION: `usaspending-api` sounds like an API surface, and the DATA Act Broker is a separate first-party backend, so one could mistake this candidate for a thin presentation layer or choose the Broker instead. Source/test inspection defeats the first objection: this repository owns concrete Broker ingestion, normalization, derived award state, schemas/materialized views and integration tests. The second objection remains a scope boundary: `data-act-broker-backend` is upstream submission/validation infrastructure, whereas this task asks for the federal spending/award backend/ETL that turns those submissions and award feeds into the USAspending data model. Independent verifier verdict: ACCEPT STRONG with that boundary preserved.
COMMERCIAL WEDGE: Evidence-grade federal award normalization and change intelligence for GovCon/compliance products: pin an official data-model revision, normalize award/recipient/agency/account identity, reproduce award-history rollups and detect meaningful award/obligation/subaward changes. A first paid wedge is a deterministic award-history/entity-normalization and snapshot-diff QA layer for a GovCon intelligence or audit workflow, reducing bespoke federal-data ETL and reconciliation work.
SEARCH EFFORT: 4 materially distinct search passes; 8 deep inspections of source/schema/test artifacts, plus exact-history and upstream-backend comparison.
FALSE-PROMOTION RISK: LOW-MODERATE. Risk comes from overcalling USAspending as the sole system of record or assuming every production Databricks transform is present. The core benchmark claim is source-verified: this is first-party production-shaped backend/ETL with real schemas and transformations, not an endpoint wrapper.
LESSON: The Task 09 production-source triangulation lesson generalized successfully to a second, structurally different official system: start from the first-party publication surface, follow it to the source repository, then require operational transformation code + internal schema + tests/fixtures + exact deploy/history evidence. Repository names are weak signals (`*-api` can hide the real ETL plane); concrete loader commands, model derivations and integration tests are better discriminators. This is the second benchmark success for the generalized method, making it eligible for later SEARCH_SKILLS promotion.
COMPLETED_AT: 2026-09-20T02:02:26-04:00
