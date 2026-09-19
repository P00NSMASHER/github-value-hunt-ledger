# Permits / PermitPlate

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

### civic-data-adapters
- Repository: https://github.com/mpointer/civic-data-adapters
- Commit / revision: `1d6f3dd1811e320effef43b8e88c957a8a1a4934`
- Date discovered: 2026-09-19
- What it contains: A compact TypeScript civic-ingestion library extracted from a production local-news pipeline. The important PermitPlate component is a deterministic Socrata catalog discovery engine that searches a portal's real catalog, scores datasets for permits/zoning/violations/inspections/contracts, maps source columns into a ready-to-run adapter configuration, and hands normalized records to a sink with stable dedupe keys. The Socrata adapter paginates recent records, enforces a page cap, normalizes dates, maps permit numbers/titles/summaries, and supports generic permit/violation/inspection/contract record types. Discovery is explicitly human-approved rather than auto-provisioned.
- Why it matters: PermitPlate's largest scaling bottleneck is adding jurisdictions without hand-building every Socrata integration. This repository already solves the discover -> classify -> map -> ingest loop for Socrata-backed municipal datasets, and it does so with real catalog metadata rather than an LLM guess. That makes it a strong base for generalized multi-city permit and code-enforcement source discovery.
- Commercial possibilities: Add a jurisdiction-onboarding service to PermitPlate that automatically inventories a city's Socrata portal, proposes permit/violation/zoning datasets, verifies schemas, and creates normalized feed configs. This can turn PermitPlate from an NYC-specific feed into a repeatable municipal opportunity engine for contractors, material distributors, lenders, insurers, property operators, and economic-development intelligence buyers.
- Build-time savings: Estimated 1-3 months for Socrata source discovery, schema mapping, pagination, normalization, idempotent ingestion, and source-verification plumbing; more if expanded across many portals.
- Evidence inspected: `README.md`; `src/discovery/socrata-catalog.ts`; `src/discovery/socrata-catalog.test.ts`; `src/adapters/blotter-socrata.ts`; repository tree and latest commit metadata. The inspected discovery code includes permit/zoning and violation patterns, column mapping, scoring, domain-scoped Socrata catalog paging, dedupe, and evidence strings. Tests cover domain scoping, mapping, dedupe, and failure handling. The latest commit message reports 26/26 tests and TypeScript clean at v0.2.0.
- License / rights: Apache-2.0 confirmed in root `LICENSE` and README. Code is permissively reusable subject to Apache-2.0 notice/terms. Municipal datasets discovered through it have separate source-specific data rights/terms and must be evaluated independently.
- Reuse classification: Directly reusable.
- Scores:
  - Technical value: 9
  - Commercial value: 9
  - Rarity: 9
  - Completeness: 8
  - Build-time saved: 9
  - Data advantage: 9
  - High-ticket potential: 8
- Next action: Prototype a PermitPlate `discover-jurisdiction` command around `searchSocrataCatalog`, extending its permit pattern with valuation, contractor, parcel/address, status, work-type, and geospatial field candidates, then test it against 5-10 Socrata cities and measure how many feeds can be onboarded without handwritten configs.

### PermitBuild / construction-intel
- Repository: https://github.com/adamleap02/PermitBuild
- Commit / revision: `ff795137e0c66e62a87e62956fa351926886255d`
- Date discovered: 2026-09-19
- What it contains: A surprisingly large construction-permit/property-intelligence codebase with FastAPI/Postgres scaffolding, alerts/billing migrations, Socrata/ArcGIS/CKAN/HTML connectors, normalization/enrichment modules, tests, and deployment infrastructure. The inspected Socrata connector is roughly 73 KB and contains live-verified field mappings for multiple cities/counties. It normalizes contractor/builder/architect/engineer, address, parcel, valuation, square footage, units, status, dates, coordinates, and permit URL where available; handles duplicate permit identifiers, 50k-row Socrata pages with backoff, and city-specific data-quality traps. Tests exercise real-shaped records from SF, Chicago, Austin, Mesa, Cambridge, Howard County, Norfolk, Kansas City, Somerville, and other feeds.
- Why it matters: This is almost a clean-room blueprint for the generalized PermitPlate data model and jurisdiction connector library. The unusually valuable part is not the product shell but the accumulated source-specific schema knowledge: fee-vs-project-valuation corrections, contractor-role extraction, zero-safe valuation handling, address construction, source-level uniqueness quirks, missing-field truth, and proven field mappings across many permit portals.
- Commercial possibilities: Use it as an inspect-only reference to accelerate a proprietary PermitPlate connector registry and canonical permit schema. The product wedge is a normalized cross-jurisdiction feed of high-intent construction events with contractor/owner/project-value context and saved searches/alerts, rather than a generic permit dashboard.
- Build-time savings: Estimated 2-5 months of schema archaeology and connector edge-case discovery if the mappings and test cases are reimplemented clean-room; potentially more as a roadmap for ArcGIS/CKAN/HTML coverage.
- Evidence inspected: Root `README.md`; repository tree showing backend migrations, billing/alerts, Socrata/ArcGIS/CKAN/HTML connectors, enrichment and infra; `backend/app/connectors/socrata.py`; `backend/tests/test_connector_socrata.py`; latest commit metadata. The source documents and tests show live-verified fixes for non-unique permit numbers, fee-vs-valuation confusion, contractor/architect role extraction, zero-value handling, absent-schema fields, and multiple real municipal permit datasets.
- License / rights: No root `LICENSE` found at the inspected revision, and no SPDX license declaration was found in repository code search. Treat repository-owned code/documentation as copyrighted inspect-only material unless the author supplies a reuse license. Public municipal source endpoints/data may have separate public/open-data terms that can be used independently after checking each source.
- Reuse classification: Inspect / learn / clean-room implementation only.
- Scores:
  - Technical value: 9
  - Commercial value: 9
  - Rarity: 10
  - Completeness: 8
  - Build-time saved: 9
  - Data advantage: 10
  - High-ticket potential: 9
- Next action: Extract only factual source metadata and independently verify the municipal APIs, then recreate a licensed PermitPlate connector registry from scratch using the existing Apache-2.0 civic-data-adapters engine as the legal implementation base. Prioritize the city mappings whose feeds contain contractor + valuation + address/parcel fields.
