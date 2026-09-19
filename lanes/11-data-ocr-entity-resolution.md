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
