# Data / OCR / Entity Resolution

## Hunter instructions
Before searching, read this file plus ../MASTER.md, ../REJECTED.md, and ../COMBINATIONS.md.

Search public GitHub repositories for unusually valuable functioning software, data pipelines, algorithms, workflows, datasets, integrations, or product infrastructure relevant to this lane. Include obscure, abandoned, low-star, and no-license repositories in discovery. Respect license/copyright for reuse.

Do not collect, reproduce, preserve, or exploit exposed credentials, personal data, authentication material, or accidentally published confidential information. Skip/quarantine those items and continue searching for legitimate technical or commercial value.

## Finding template
### Repository name
- Repository:
- Commit / revision:
- Date discovered:
- What it contains:
- Why it matters:
- Commercial possibilities:
- Build-time savings:
- Evidence inspected:
- License / rights:
- Reuse classification:
- Scores:
  - Technical value:
  - Commercial value:
  - Rarity:
  - Completeness:
  - Build-time saved:
  - Data advantage:
  - High-ticket potential:
- Next action:

## Findings
### dedupeio/dedupe
- Repository: https://github.com/dedupeio/dedupe
- Commit / revision: 3f61e79102910bd355e920a2df7e44c14c9cb247
- Date discovered: 2026-09-19
- What it contains: Mature Python fuzzy matching, record deduplication, record linkage, blocking, clustering, learned classifiers, confidence scoring, and entity-resolution APIs.
- Why it matters: Entity resolution is a reusable hidden requirement across PermitPlate, CaptureBrief, freight audit, supplier/AP analysis, and public-data products where names/addresses/organizations do not share stable IDs.
- Commercial possibilities: Shared matching layer for contractors/properties/vendors/agencies/carriers across fragmented datasets, improving enrichment, deduplication, and longitudinal histories.
- Build-time savings: Very high versus designing blocking, pair scoring, clustering, training, confidence, and scaling logic from scratch.
- Evidence inspected: README.md; dedupe/api.py implementing matching, blocking/fingerprinting, scoring, clustering, training-oriented APIs, multiprocessing, and confidence outputs.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT terms.
- Scores:
  - Technical value: Very High
  - Commercial value: High as infrastructure
  - Rarity: Medium
  - Completeness: Very High
  - Build-time saved: Very High
  - Data advantage: High when applied to fragmented proprietary/public datasets
  - High-ticket potential: High indirectly
- Next action: Prototype one shared entity graph for PermitPlate + CaptureBrief using business/person/address normalization and confidence-scored linkage.
  
### getomni-ai/zerox
- Repository: https://github.com/getomni-ai/zerox
- Commit / revision: 91bbb20c50de86067670aa13833afa1b8a73c22e
- Date discovered: 2026-09-19
- What it contains: Node and Python document-to-markdown/document-extraction pipeline that converts PDFs/docs/images to page images and uses vision models for OCR/layout interpretation; supports multiple model providers, concurrency, page selection, formatting preservation, and structured extraction options.
- Why it matters: It can dramatically shorten the path from messy business documents to machine-readable evidence for invoice audit, contracts, government notices, permits, scopes, and change-order analysis.
- Commercial possibilities: Shared document-ingestion layer across freight audit, ScopeSignal, CaptureBrief, and AP/recovery products.
- Build-time savings: High for multi-format conversion, vision-model orchestration, concurrency, provider support, and document extraction plumbing.
- Evidence inspected: README.md; repository structure includes node-zerox/src, node-zerox/tests, Python package, packaging files; node-zerox/src/index.ts is a substantive implementation file (~18.5 KB) with supporting models/types/utils.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT terms.
- Scores:
  - Technical value: High
  - Commercial value: High as a shared ingestion component
  - Rarity: Medium
  - Completeness: High
  - Build-time saved: High
  - Data advantage: Medium
  - High-ticket potential: High indirectly
- Next action: Benchmark it on representative invoices/contracts/permit PDFs and compare structured-output reliability against DocuRule-style deterministic provenance workflows.

### rasinmuhammed/entify
- Repository: https://github.com/rasinmuhammed/entify
- Commit / revision: ae9be28452d8fee61aa18d0862732f1e1826be52
- Date discovered: 2026-09-19
- What it contains: A functioning local-first entity-resolution workspace built on Splink 4 + DuckDB with automatic column-role inference, blocking-rule generation, probabilistic matching/training, clustering, per-field survivorship, traceable source IDs, explainable waterfall charts, CSV/TSV/Parquet/JSON/Excel ingestion, PDF audit reports, a Next.js UI, optional semantic blocking, and Docker deployment. The exact revision includes a 47 KB resolution engine, 24 KB FastAPI layer, 15 KB autoconfiguration module, 17 KB Splink service, audit/reporting code, frontend, and a substantive test suite.
- Why it matters: This is materially more product-ready than a raw matching library. It turns entity resolution into an explainable data-steward workflow that can clean messy carrier/vendor/customer/property/company records before invoice, permit, contract, or public-data analysis. The repo includes external FEBRL tests that auto-configure on unseen data and assert high precision/recall, including harder variants with the strong identifier removed and meaningless headers.
- Commercial possibilities: (1) A lightweight customer/vendor-master cleanup audit sold as a fixed-fee data-quality engagement; (2) shared entity-resolution infrastructure for freight audit so carrier/vendor aliases across OCR, ERP exports, rate cards, invoices, and payment ledgers resolve to one entity; (3) entity graph / longitudinal record layer for PermitPlate and CaptureBrief; (4) private/on-prem deduplication for buyers unwilling to upload customer data to SaaS MDM tools.
- Build-time savings: Very High — likely 2-4 months versus building auto-profiling, blocking, probabilistic training, explainable matching, review UI, merge survivorship, benchmark harnesses, and audit reporting from scratch.
- Evidence inspected: Actual MIT LICENSE.md; exact latest commit and recursive tree; README architecture/limitations; backend/tests/test_external_benchmark.py. Tests assert >=0.99 precision / >=0.98 recall on the external FEBRL benchmark in the normal case and >=0.98 precision / >=0.95 recall without the strong SSN-like identifier; anonymized-header and sparse/junk-column robustness are also tested. README documents measured scaling and current limitations rather than hiding them.
- License / rights: MIT; actual license file inspected at the exact revision. Splink and other dependencies still require normal dependency-license review before redistribution.
- Reuse classification: Directly reusable subject to MIT terms and dependency-license compliance.
- Scores:
  - Technical value: Very High
  - Commercial value: Very High as shared infrastructure and a narrow data-quality service
  - Rarity: High relative to its 0-star / 0-fork visibility
  - Completeness: Very High
  - Build-time saved: Very High
  - Data advantage: Very High when combined with fragmented customer/public/vendor datasets
  - High-ticket potential: High
- Next action: Benchmark Entify against one realistic freight/vendor-master dataset and one PermitPlate/CaptureBrief entity set; if precision holds, use it as the common entity-resolution layer instead of building a second matcher around dedupeio/dedupe.

### oronts/invoice-audit-skill
- Repository: https://github.com/oronts/invoice-audit-skill
- Commit / revision: 1be6b451457d76c02ecc2e1674aa4227db6f0f2e
- Date discovered: 2026-09-19
- What it contains: A surprisingly complete TypeScript/Bun invoice-audit pipeline that converts PDF/image supplier invoices into strict structured data, reconciles them against open orders, runs roughly 20 deterministic rules, routes exceptions through a human-review path, optionally invokes an LLM anomaly reviewer, persists state, produces JSON/Markdown/CSV reports, and maintains SHA-256 hash-chained decision/audit records. The tree includes a large config surface, PII/tokenization/retention helpers, supplier identity logic, PO-consumption state, duplicate detection, line reconciliation, VAT/IBAN/recipient/supplier rules, evaluation/calibration code, Docker packaging, E2E tests, and dozens of adversarial/regression tests.
- Why it matters: This is unusually close to the control plane needed for the freight-invoice audit/recovery product: document extraction -> deterministic evidence checks -> cross-invoice reconciliation -> fail-closed decision -> human override -> tamper-evident audit trail. It can provide the workflow/evidence shell while freight-specific math and carrier/rate-contract logic stay separate. It is also a stronger tested foundation for AP/document validation than many README-only invoice projects.
- Commercial possibilities: (1) Accelerate the freight-recovery stack by replacing its PO-centric rules with carrier invoice + rate agreement + shipment evidence rules while retaining HITL, state, audit chain, configuration, and reporting; (2) a narrow AP exception-review service for mid-market finance teams; (3) shared document-decision infrastructure for vendor onboarding/COI/compliance packets after swapping schemas/rules.
- Build-time savings: Very High — likely 2-4 months for a production-minded evidence/rules/HITL/audit framework, and potentially enough to compress a freight-audit demo into days once domain rules are supplied.
- Evidence inspected: Actual MIT LICENSE; exact commit/tree; README; BENCHMARK.md; src/domain/hash-chain.ts; test/e2e/pipeline.e2e.test.ts. The repository contains 352 tests / 697 assertions per its checked benchmark report, E2E approve/review flows, audit-chain tamper tests, duplicate/entity-bypass/adversarial regressions, config-safety tests, HITL override tests, and state/reconciliation tests. The live extraction benchmark is author-reported and model-dependent, so it should not be treated as independent OCR accuracy proof.
- License / rights: MIT; actual license inspected, granting commercial use/modification/distribution subject to preserving the notice. Anthropic/Claude, Mastra, Bun, and other dependencies/services require their own terms/licensing review.
- Reuse classification: Directly reusable subject to MIT terms and dependency/provider terms.
- Scores:
  - Technical value: Very High
  - Commercial value: Very High, especially combined with the freight-audit/recovery stack
  - Rarity: Very High relative to 0 stars / 0 forks
  - Completeness: Very High for a single-commit repository, with important deployment gaps disclosed
  - Build-time saved: Very High
  - Data advantage: High once paired with customer invoice/order/rate/evidence history
  - High-ticket potential: Very High
- Next action: Run a clean-room spike that maps freight entities and evidence into this pipeline: carrier/vendor identity, invoice number, PRO/BOL, service date, billed line, expected line, rate-source hash, discrepancy rule, reviewer decision, and recovery-state output. Keep its documented gaps in place for the first pilot: no ERP payment write-back, no reviewer authentication, and no cross-tenant deployment until separately hardened.

### opensanctions/yente
- Repository: https://github.com/opensanctions/yente
- Commit / revision: 3bc1b14ea884aba9f0728d67b76a461f5339dc59
- Date discovered: 2026-09-19
- What it contains: Production-grade asynchronous FastAPI entity search/matching infrastructure used as the open-source core of the OpenSanctions API. It supports people, companies, vessels, custom watchlists, company-registry/KYB data, FollowTheMoney schemas, configurable scoring, Elasticsearch/OpenSearch candidate retrieval, on-prem deployment, OpenTelemetry instrumentation, benchmark fixtures, validation tooling, Docker packaging, and a substantial pytest suite.
- Why it matters: Unlike general-purpose deduplication libraries, yente is already shaped for operational KYC/KYB/watchlist-style matching where noisy names, company records, identifiers, sanctions entities, and custom datasets need low-latency candidate generation plus explainable scoring. It can provide a hardened entity-search service around vendor/carrier/company matching without sending customer queries outside the customer's infrastructure.
- Commercial possibilities: (1) Private vendor/KYB matching layer for onboarding and contractor qualification; (2) entity screening/enrichment infrastructure for PermitPlate/CaptureBrief/freight customer records; (3) on-prem matching service for buyers with confidentiality restrictions; (4) custom internal watchlist matching when customer-supplied data is used instead of licensed OpenSanctions data.
- Build-time savings: Very High — likely 2-4 months for API, search-provider abstraction, entity schemas, matching/scoring plumbing, observability, indexing, benchmarking, and self-host deployment.
- Evidence inspected: Exact latest commit; README; actual MIT LICENSE; recursive source tree; yente/scoring.py; tests/test_match.py search results; candidate-generation benchmark and validation-report directories; Dockerfile and CI/security workflows. The tree includes multi-megabyte positive/negative benchmark fixtures and active tests around matching behavior and candidate search. README explicitly separates the MIT code license from commercial licensing of OpenSanctions datasets.
- License / rights: Code is MIT. OpenSanctions datasets have separate licensing and may require a commercial data license; do not assume the code license grants rights to the data. Customer-owned/custom datasets can avoid that dependency if lawful.
- Reuse classification: Directly reusable for the software under MIT terms; dataset reuse requires separate rights review.
- Scores:
  - Technical value: Very High
  - Commercial value: Very High as regulated-B2B matching infrastructure
  - Rarity: Medium (established project, but unusually complete for this lane)
  - Completeness: Very High
  - Build-time saved: Very High
  - Data advantage: Very High when paired with licensed/custom corporate datasets
  - High-ticket potential: Very High
- Next action: Benchmark yente versus Entify on carrier/vendor/company-name resolution and determine whether yente should become the low-latency screening/search service while Entify remains the batch cleanup/stewardship layer.

### zentity-io/zentity
- Repository: https://github.com/zentity-io/zentity
- Commit / revision: ecddfab82b68379d223beac108714a92831a4dba
- Date discovered: 2026-09-19
- What it contains: An Apache-2.0 Elasticsearch plugin for deterministic entity resolution directly over existing indices. It defines entity models, attributes, matchers, resolvers, multi-index mappings, recursive/transitive resolution, and REST endpoints, with large core Job/Query implementations, integration tests, Maven packaging, and CI that tests against many Elasticsearch versions.
- Why it matters: zentity solves a different operational problem than Dedupe/Entify: real-time, transitive resolution across already-indexed heterogeneous data without forcing a separate batch dedupe/reindex workflow. That is valuable when PermitPlate, CaptureBrief, freight, or customer systems already sit in Elasticsearch and need to resolve aliases across multiple sources on demand.
- Commercial possibilities: (1) Real-time company/vendor/property identity graph over Elasticsearch-backed products; (2) cross-index carrier/customer/company resolution in data-heavy SaaS; (3) investigative/entity-search feature where multi-hop identities matter; (4) low-friction add-on for customers already standardized on Elasticsearch.
- Build-time savings: High — likely 1-3 months for model DSL, transitive query planning, multi-index resolution, plugin/API packaging, and cross-version compatibility work.
- Evidence inspected: Exact latest commit; README; actual Apache-2.0 LICENSE and NOTICE; recursive source tree; CI matrix; source includes ~58 KB resolution/Job.java and ~46 KB resolution/Query.java plus model classes; tests include JobTest and Elasticsearch ResolutionActionIT integration coverage.
- License / rights: Apache License 2.0 with NOTICE/attribution and modified-file obligations; Elasticsearch itself and any distribution/plugins used in deployment require separate compatibility/terms review.
- Reuse classification: Reusable with Apache-2.0 license conditions.
- Scores:
  - Technical value: High
  - Commercial value: High when an Elasticsearch-native path exists
  - Rarity: High
  - Completeness: Very High
  - Build-time saved: High
  - Data advantage: High when federating multiple customer indices
  - High-ticket potential: High indirectly
- Next action: Prototype a carrier/vendor entity model across invoice, rate-card, shipment, and ERP indices; compare latency and explainability against the Entify/Splink batch path before choosing an architecture.

### conjuncts/gmft
- Repository: https://github.com/conjuncts/gmft
- Commit / revision: ac7ef5e73e3977bfe60b6ffd80356b7be32f4532
- Date discovered: 2026-09-19
- What it contains: Focused PDF table-detection and structure-extraction library built on Microsoft's Table Transformer plus PyPDFium2. It detects tables, reconstructs implicit structure, handles multi-column headers, spanning cells and rotated tables, exports to pandas/CSV/JSON/HTML/Markdown/LaTeX, and can expose crops/bounding boxes for a downstream OCR/vision step. The repository includes CI, extensive reference outputs, sample PDFs, comparison data, tests against expected bounding boxes/dataframes, notebooks, and current Python packaging.
- Why it matters: Zerox is a broad vision/document ingestion layer, but freight invoices, rate sheets, tariffs, bid tabs, policy schedules, and government notices often fail specifically at dense tabular structure. gmft can serve as a deterministic/high-throughput table-first extractor before invoking a more expensive vision model, while preserving row/column semantics needed for audit evidence.
- Commercial possibilities: (1) Freight rate-card/invoice table extraction feeding deterministic recovery rules; (2) contract schedule and pricing-table extraction for ScopeSignal/compliance workflows; (3) bulk financial/document-table normalization service; (4) hybrid ingestion pipeline that routes born-digital tables through gmft and scanned/image tables through OCR/vision.
- Build-time savings: High — likely 1-2 months for table detection, structural reconstruction, dataframe export, geometry handling, and regression fixtures.
- Evidence inspected: Exact latest commit; README; actual MIT LICENSE; recursive tree; current pyproject/CI; data/test/references contains large expected table/CSV/position fixtures; test/formatters/tatr/test_full.py asserts table bounding boxes and dataframe output. README discloses limitations including no OCR, false positives/negatives, and merged-cell issues rather than treating benchmarks as universal accuracy guarantees.
- License / rights: MIT for gmft. Its default dependency stack includes PyPDFium2/Transformers/PyTorch; dependency/model/data licenses require normal review. The separate optional PyMuPDF support repository is AGPL-3.0 and should not be silently substituted into a proprietary product without accepting those obligations.
- Reuse classification: Directly reusable subject to MIT and dependency/model-license terms; avoid the separate AGPL PyMuPDF integration unless deliberately chosen.
- Scores:
  - Technical value: High
  - Commercial value: Very High as a document-table component
  - Rarity: Medium
  - Completeness: Very High
  - Build-time saved: High
  - Data advantage: High once table rows are linked to source-page geometry/evidence
  - High-ticket potential: High indirectly
- Next action: Add gmft to the freight-document benchmark: run born-digital carrier invoices/rate sheets through gmft first, fall back to Zerox/vision only when confidence/structure checks fail, and measure line-item accuracy plus processing cost.
