# Pair 2 — CONTROL results

Frozen benchmark result log. Append one task result block per scheduled run. Do not rewrite prior completed blocks.

TASK: 09
CONDITION: CONTROL
STARTING HYPOTHESIS: The official Acquisition.gov/GSA publication pipeline likely exposes FAR as structured DITA/XML with clause/provision metadata, fill-in markers, and FAC-level change provenance suitable for machine ingestion.
DISCOVERY METHODS: Official-domain web search for Acquisition.gov developer/FAR machine-readable sources; public GitHub discovery around the GSA acquisition repositories; direct repository/commit/file inspection of the candidate’s default branch and DITA artifacts.
CANDIDATE: GSA/GSA-Acquisition-FAR
CANONICAL URL: https://github.com/GSA/GSA-Acquisition-FAR
EXACT REVISION: da52ccbbe114e1f031a7f4c59195c508dbfa485f
VERDICT: STRONG
A-F SCORE: A5 B5 C5 D5 E5 F4 = 29/30
EVIDENCE INSPECTED: Official Acquisition.gov developer material; GitHub repository metadata showing the GSA organization and default branch; protected master HEAD at da52ccbbe114e1f031a7f4c59195c508dbfa485f; dita/52.203-14.dita; dita/LSATable.dita; FAC 2026-01 merge/update commits including 80b7c82579bc69ddc187f05c862e66400c3277bf.
CLAIMS VERIFIED: The source is first-party GSA/Acquisition.gov; FAR is published as DITA/XML rather than flattened prose; clause 52.203-14 preserves structural IDs, prescription cross-references, clause text, and machine-readable government fill-ins using xtrc/xtrf plus outputclass; LSATable.dita identifies FAC 2026-01, effective March 13 2026, enumerates affected sections, describes exact amendments, and links each change to a FAR case/Federal Register amendment; the default-branch history contains explicit FAC 2026-01 update commits, providing revision provenance beyond static text.
CLAIMS NOT VERIFIED: Exhaustive correctness/completeness of every FAR clause/provision; formal schema-validation guarantees for all DITA files; long-term API/backward-compatibility guarantees; a repository-level public software/content license (GitHub reports license=null).
STRONGEST OBJECTION: It is an authoritative publication source, not a complete contract-writing engine; downstream users still must implement clause applicability/prescription logic and validation, and the repository lacks an explicit root license despite being an official federal source.
COMMERCIAL WEDGE: Evidence-grade FAR clause/provision ingestion for GovCon tooling: clause-change monitoring, FAC impact alerts, solicitation/award clause assembly, fill-in workflow, and provenance-backed compliance diffs for contractors or contract-writing systems.
SEARCH EFFORT: 8 materially distinct searches and 5 deep inspections
FALSE-PROMOTION RISK: LOW — first-party provenance and the requested structure/change semantics were directly observed in source files and commit history; remaining risk is primarily downstream interpretation/completeness, not whether the source exists.
LESSON: N/A
COMPLETED_AT: 2026-09-20T01:33:21-04:00

TASK: 10
CONDITION: CONTROL
STARTING HYPOTHESIS: The U.S. Treasury’s USAspending production backend should contain first-party DATA Act ingestion, canonical award/transaction schemas, and transformation logic that can be verified directly in code rather than inferred from the public REST API.
DISCOVERY METHODS: Official USAspending/API web discovery; direct inspection of the fedspendingtransparency GitHub repository and exact production-branch revision; code-level inspection of Broker submission loading, normalized transaction/award schemas, Spark/Delta ETL transformations, and ETL tests.
CANDIDATE: fedspendingtransparency/usaspending-api
CANONICAL URL: https://github.com/fedspendingtransparency/usaspending-api
EXACT REVISION: 1692d484b38c66361c54faa221548527cae29964
VERDICT: STRONG
A-F SCORE: A3 B5 C5 D5 E5 F5 = 28/30
EVIDENCE INSPECTED: Official USAspending API site identifying Treasury’s open-source DATA Act stack; repository metadata and signed master HEAD 1692d484b38c66361c54faa221548527cae29964; usaspending_api/etl/management/commands/load_submission.py; usaspending_api/awards/models/transaction_normalized.py; usaspending_api/awards/models/award.py; usaspending_api/etl/management/commands/load_transactions_in_delta.py; usaspending_api/etl/tests/unit/test_load_transactions_in_delta.py; loading_data.md and data_reformatting.md for source/loader cross-checks.
CLAIMS VERIFIED: The repository is the production-shaped backend used by USAspending.gov, not an API wrapper: load_submission.py connects to the Data Broker and transactionally loads certified submission File A, File B and File C data with validation and rollback behavior; the normalized transaction model defines monetary, agency, award-key, certification and action-date fields and maps them to a reporting view; the Award model explicitly constructs high-level award holders from incoming D1/D2/legacy transactions and carries PIID/FAIN/parent-award/obligation and aggregate semantics; the Spark/Delta loader implements bronze-to-silver ETL levels for award/transaction lookup, FPDS, FABS, normalized transactions and awards, including deletes, merge/upsert behavior, date parsing, string canonicalization, category derivation, earliest/latest transaction selection and monetary aggregation; a unit test exercises fail-closed behavior when required Delta tables are absent. Official USAspending documentation independently states that the U.S. Department of the Treasury builds the open-source tools and that the API serves comprehensive government spending data.
CLAIMS NOT VERIFIED: Full end-to-end reproducibility against the live Treasury production databases; exhaustive correctness of every transformation or historical edge case; whether all production orchestration/infrastructure is contained in this single repository; live Broker credentials/data access; independent numerical reconciliation of a production snapshot.
STRONGEST OBJECTION: This is a large evolving government production stack rather than a drop-in library. Reusing the ETL directly requires substantial Postgres/Spark/Delta/Data Broker context, and production truth still depends on upstream agency/Broker submissions and reference data.
COMMERCIAL WEDGE: Evidence-grade federal-award intelligence infrastructure: reuse the authoritative schema and transformation semantics to normalize award histories, obligations, modifications and agency/recipient records for GovCon opportunity intelligence, spend-change monitoring, award lineage/reconciliation and provenance-backed analytics without reverse-engineering USAspending’s public endpoint behavior.
SEARCH EFFORT: 3 materially distinct discovery methods and 6 deep inspections
FALSE-PROMOTION RISK: LOW — first-party Treasury provenance is independently corroborated, and the requested schemas plus ETL transformations were observed directly in source and tests at a fixed commit; residual risk concerns deployment complexity and upstream data quality, not whether the backend/ETL exists.
LESSON: N/A
COMPLETED_AT: 2026-09-20T01:59:05-04:00
