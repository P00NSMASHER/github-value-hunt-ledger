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

TASK: 11
CONDITION: CONTROL
STARTING HYPOTHESIS: Treasury’s USAspending normalization backend likely contains deterministic recipient identity construction from SAM/award data plus explicit parent/referenced-award identifiers and ambiguity-safe linkage rules that are more useful for evidence-grade entity resolution than the public API surface alone.
DISCOVERY METHODS: Official Treasury/USAspending web discovery for DATA Act recipient and award identifiers; public GitHub discovery across fedspendingtransparency repositories; code-level search for recipient_hash/UEI/parent identity semantics and referenced-IDV/parent-award fields; direct inspection of normalization SQL/models plus integration tests for recipient and award-linkage behavior.
CANDIDATE: fedspendingtransparency/usaspending-api
CANONICAL URL: https://github.com/fedspendingtransparency/usaspending-api
EXACT REVISION: 1692d484b38c66361c54faa221548527cae29964
VERDICT: STRONG
A-F SCORE: A4 B5 C5 D5 E5 F5 = 29/30
EVIDENCE INSPECTED: Official USAspending API material identifying Treasury’s open-source DATA Act stack; Treasury Financial Experience guidance defining UEI/legal-entity/ultimate-parent and PIID/Parent Award ID/FAIN/URI semantics; repository metadata and signed master HEAD 1692d484b38c66361c54faa221548527cae29964; usaspending_api/recipient/models.py; usaspending_api/recipient/delta_models/recipient_lookup.py; usaspending_api/recipient/delta_models/recipient_profile.py; usaspending_api/awards/models/transaction_fpds.py; usaspending_api/etl/management/sql/c_file_linkage/C_to_D_Linkage.md; usaspending_api/recipient/tests/integration/test_recipient.py; usaspending_api/etl/tests/integration/test_update_file_c_linkages_in_delta.py.
CLAIMS VERIFIED: The first-party backend implements recipient identity rather than merely exposing strings: recipient_lookup stores deterministic recipient_hash plus UEI, DUNS, legal name, parent UEI/DUNS/name, source, update_date and alternate names; the Delta normalization builds hashes with UEI preferred, DUNS second and normalized legal name as fallback, constructs the same hierarchy for ultimate parents, and merges SAM-derived identity records with FPDS/FABS transaction evidence. RecipientProfile explicitly distinguishes parent/child/root-recipient levels and affiliations, with uniqueness on recipient_hash plus recipient_level. Procurement transaction schema preserves parent_award_id, referenced_idv_agency_iden and referenced-IDV type semantics. The File-C-to-D linkage logic links procurement and assistance records only when exactly one award matches the applicable PIID+parent-PIID, PIID, FAIN or URI rule; zero-match or multi-match ambiguity remains unlinked. Integration tests exercise parent-PIID matches/mismatches, duplicate-match no-link behavior, deleted-award unlinking, FAIN/URI fallback cases, and recipient parent/child identity fixtures.
CLAIMS NOT VERIFIED: Full live-production reconciliation of recipient_lookup against current SAM/FPDS/FABS snapshots; exhaustive temporal lineage for every recipient identity change or merger; globally unique legal-entity resolution beyond federal identifier semantics; collision/false-merge behavior when the name fallback is used; independent proof that every upstream source correction propagates without lag.
STRONGEST OBJECTION: This is deterministic federal-award identity normalization, not a general probabilistic entity-resolution system. Its strongest keys are UEI/DUNS and federal award identifiers, while the legal-name fallback can be ambiguous and the latest-record merge can discard some historical nuance; downstream evidence-grade products should preserve source snapshots and refuse to overstate identity when only weak fallback evidence exists.
COMMERCIAL WEDGE: A provenance-backed GovCon entity/award graph that resolves contractors, subsidiaries/parents and task-order/IDV relationships, then drives award-history reconstruction, incumbent mapping, spend consolidation, modification monitoring and evidence-backed opportunity intelligence without inventing joins from names alone.
SEARCH EFFORT: 7 materially distinct searches and 7 deep inspections
FALSE-PROMOTION RISK: LOW — first-party Treasury provenance, identity-construction code, parent/referenced-award fields, ambiguity-safe linkage rules and integration tests were all inspected at a fixed signed production revision; residual risk is mostly around historical completeness and weak-key fallback semantics.
LESSON: N/A
COMPLETED_AT: 2026-09-20T03:06:28-04:00

TASK: 12
CONDITION: CONTROL
STARTING HYPOTHESIS: A credible restore-verification platform should treat backup creation/status as insufficient, provision disposable targets, execute engine-specific recovery paths across multiple data systems, run semantic checks against the recovered state, and persist/export check-level evidence that distinguishes restore/validation failure from mere backup completion.
DISCOVERY METHODS: Direct public-web search for automated restore drills and disaster-recovery verification; GitHub repository discovery around restore-verification terms; comparative code inspection of Redrill, Databasus, and restore-drill; deep inspection of restore-drill’s engine lifecycle, PostgreSQL/MySQL/Redis providers, evidence reporter, integration fixtures, CI workflow, and exact-SHA Actions results.
CANDIDATE: RamazanKara/restore-drill
CANONICAL URL: https://github.com/RamazanKara/restore-drill
EXACT REVISION: dea374da3b340f53b798112eee82bd7ed1224572
VERDICT: STRONG
A-F SCORE: A4 B5 C5 D5 E5 F5 = 29/30
EVIDENCE INSPECTED: Public GitHub discovery; repository tree at exact revision; internal/engine/engine.go; internal/providers/postgres/postgres.go; internal/providers/mysql/mysql.go; internal/providers/redis/redis.go; internal/reporter/evidence.go; test/integration/integration_test.go; .github/workflows/ci.yml; exact-revision GitHub Actions run 28367632132 and jobs; LICENSE.
CLAIMS VERIFIED: The engine provisions a disposable runtime target, performs provider preflight, calls a real restore operation, then validates the recovered system and evaluates expected-vs-actual checks; a pass is derived from restored-state checks, not a backup-success flag. PostgreSQL recovery paths support pg_dump/pg_restore, pgBackRest and WAL-G and then run SQL/schema/freshness/extensions checks; MySQL/MariaDB paths support mysqldump, XtraBackup and MariaBackup including physical prepare/copy-back/restart flows and SQL validation; Redis restores RDB/AOF into a fresh server and validates key counts, key existence and query values. The Docker integration suite constructs real backup fixtures for PostgreSQL, MySQL/MariaDB and Redis, executes restore drills and requires each validation result to pass. CI at the exact revision successfully ran the docker-integration job plus Kubernetes smoke and unit verification. Evidence reporting preserves run timestamps/provider/duration, aggregate RTO/success metrics, and failure-level check details including expected, actual and error, with JSON and HTML output. Apache-2.0 licensing is explicit.
CLAIMS NOT VERIFIED: Independent production usage at scale; long-running reliability across diverse real-world backup repositories/object stores; Kubernetes end-to-end provider parity beyond the inspected smoke test; tamper-evident/cryptographically signed evidence; complete support for every database/version/backup-tool edge case; customer adoption or paid deployments.
STRONGEST OBJECTION: The project is small and production adoption is not established, and its evidence is generated by the verifier itself rather than an external attestation or append-only signed ledger. Heterogeneous provider coverage is real but finite, so version/tool-specific recovery edge cases remain operational risk.
COMMERCIAL WEDGE: A self-hosted “restore proof” control for SRE/platform teams, MSPs and regulated operators that continuously proves PostgreSQL/MySQL/MariaDB/Redis backups can actually recover, produces RTO/RPO and expected-vs-actual audit evidence, and alerts on silent backup rot without replacing the existing backup product.
SEARCH EFFORT: 6 materially distinct searches/comparative passes and 10 deep inspections
FALSE-PROMOTION RISK: LOW — restore execution, semantic validation, heterogeneous provider implementations, evidence structures, real integration fixtures, CI wiring, and a successful exact-SHA integration run were all verified beyond README; remaining risk is deployment maturity/adoption, not whether the core capability exists.
LESSON: N/A
COMPLETED_AT: 2026-09-20T04:11:44-04:00
