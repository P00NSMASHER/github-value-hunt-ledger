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
