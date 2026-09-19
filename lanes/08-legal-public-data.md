# Legal & Public Data

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

### townlight/sunshine
- Repository: https://github.com/townlight/sunshine
- Commit / revision: `ff99d8c7e692ba1f75e1781f517bb54f5c618b48`
- Date discovered: 2026-09-19
- What it contains: A locally hosted municipal public-records/open-records operations system with a Python backend and TypeScript frontend. Inspected implementation includes a full records-request status model (`received` through `closed`), statutory-deadline and fee fields, request/document linkage, configurable state exemption rules, PII/exemption scanning, duplicate-flag prevention, authenticated/admin-gated exemption APIs, public request submission, and frontend request/exemption workflows. The repository also contains database migrations, Docker/release infrastructure, and a substantial test tree.
- Why it matters: This is unusually production-shaped software for a zero-star repository. It compresses a difficult government workflow that otherwise requires request intake, deadline tracking, document search, exemption/redaction review, user/department controls, auditability, and release management to be built separately. Local hosting is commercially relevant for municipalities that are reluctant to send source records to a third-party SaaS.
- Commercial possibilities: Package as an implementation-supported public-records operations product for cities, counties, school districts, utilities, and public agencies: private-cloud/on-prem deployment, configuration of jurisdiction-specific exemption rules, records-source connectors, staff workflow, redaction/review, and annual support. A narrower initial wedge is a records-office modernization engagement that replaces spreadsheet/email tracking while keeping records under agency control.
- Build-time savings: Approximately 3–6 months versus building the request lifecycle, exemption-review engine, role-aware APIs/UI, migrations, and deployment/release plumbing from scratch.
- Evidence inspected: Actual Apache-2.0 `LICENSE`; latest commit and release/audit changes; `backend/app/models/request.py`; `backend/app/exemptions/engine.py`; `backend/tests/test_exemptions.py`; exemption models/schemas/migration/router/LLM-reviewer paths; public-request router and request/exemption frontend paths; and `docs/QA-REPORT-2026-04-13.md`. The QA report is useful negative evidence as well: it says the core clerk workflow was functional at API level, but at that April checkpoint the deployed database had only one exemption rule seeded even though broader rules existed in code/test data, so jurisdiction coverage must be validated rather than assumed.
- License / rights: Actual repository license file is Apache-2.0. No root `NOTICE` file was present at the inspected revision. Code is commercially reusable subject to Apache-2.0 terms. Jurisdiction-specific exemption logic and legal conclusions still require qualified human review; the software license does not make automated exemption decisions legally authoritative.
- Reuse classification: Directly reusable.
- Scores:
  - Technical value: 9/10
  - Commercial value: 9/10
  - Rarity: 9/10
  - Completeness: 8/10
  - Build-time saved: 9/10
  - Data advantage: 6/10
  - High-ticket potential: 9/10
- Next action: Run the inspected revision with synthetic/public test records and independently validate redaction output, department isolation, audit logs, deadline calculations, and a fully seeded jurisdiction rule set; then scope a small-municipality deployment package rather than a generic FOIA consumer app.

### KnitSecurity/municode-pp-cli
- Repository: https://github.com/KnitSecurity/municode-pp-cli
- Commit / revision: `29f71c33d9ebc4b7ad83e3786951dde612fa958b`
- Date discovered: 2026-09-19
- What it contains: A Go CLI plus MCP server around Municode public endpoints with a persistent local legal-data layer. It can resolve and browse municipalities, clone an entire municipal code into SQLite and an AI-readable Markdown tree, perform local full-text search, detect section-level drift against the live code (`added`, `removed`, `reworded`), identify stale mirrors, compare a topic across cities, extract ordinance history, build inbound/outbound statutory cross-references, resolve defined terms, and optionally ingest Rules/Ordinances PDFs. The clone path stores codification job/version identifiers, timestamps, source URLs, and resumable partial state.
- Why it matters: Municipal-law change intelligence is fragmented and expensive to reproduce across many jurisdictions. This zero-star project already supplies the hard substrate for a multi-jurisdiction "local law radar": acquisition, normalization, local persistence, searchable snapshots, source citations, change detection, and agent access. The actual `diff` implementation avoids a common false-positive failure by refusing to label missing sections as removed when the upstream walk is partial or timed out.
- Commercial possibilities: Build a cited municipal-regulation monitoring service for multi-location operators, real-estate/development teams, zoning/permit consultants, law firms, franchise operators, construction/environmental compliance teams, or insurers. A customer supplies a jurisdiction/topic watchlist; the service snapshots codes, detects and classifies changes, preserves the controlling definition/cross-references/history, and issues source-linked alerts instead of requiring staff to manually revisit hundreds of code libraries.
- Build-time savings: Approximately 2–4 months for the public-code connector, local mirror/store, FTS/search surface, source-linked exports, change-detection logic, and MCP/agent interface.
- Evidence inspected: Actual Apache-2.0 `LICENSE` and repository `NOTICE`; exact latest commit; recursive repository tree showing GoRelease/build plumbing, CLI/MCP binaries, substantial `internal/cli` implementation and tests; `README.md`; `internal/cli/clone.go`; `internal/cli/diff.go`; and `internal/cli/clone_export_test.go`. The source confirms full-code walking/persistence, Rules/Ordinances PDF handling, snapshot manifests, partial/resumable clone behavior, and explicit safeguards around partial diffs.
- License / rights: Apache-2.0 with a `NOTICE` file that must be preserved as required; the NOTICE also credits a separately MIT-licensed CLI Printing Press component. The software license does not itself grant rights in third-party publisher presentation/editorial material. Municipal legal text is generally public law, but a commercial product should still preserve official-source links and separately evaluate publisher/API terms and any non-governmental annotations or formatting it stores or redistributes.
- Reuse classification: Directly reusable.
- Scores:
  - Technical value: 9/10
  - Commercial value: 9/10
  - Rarity: 10/10
  - Completeness: 9/10
  - Build-time saved: 9/10
  - Data advantage: 9/10
  - High-ticket potential: 8/10
- Next action: Run a 25-jurisdiction mirror/change-detection benchmark on public municipal codes, record clone/diff reliability and update latency, and define a normalized alert schema containing jurisdiction, code version, section citation, old/new text hash, change type, source URL, controlling definitions, and cross-references.

### Vaquill-AI/open-us-law
- Repository: https://github.com/Vaquill-AI/open-us-law
- Commit / revision: `2f7aeb85a434a54a351ac44e3c188fec318f78ba`
- Date discovered: 2026-09-19
- What it contains: An active Python ingestion and normalization project for US primary law. The inspected tree contains executable pipelines for federal sources, state statutes, regulations, court rules, and constitutions, plus a machine-readable coverage/provenance manifest. The actual eCFR parser uses streaming XML parsing for large titles, emits normalized JSONL with stable IDs, hierarchy, authority/source fields and official eCFR URLs, and clears processed elements to control memory. `coverage.yml` is a substantive publication gate: a jurisdiction is dump-eligible only after a section-count floor and human `coverage_verified` review, and each jurisdiction records its official source, bulk source, source tier, access quirks, citation scheme, and audit notes. The project's published v2026.08 snapshot reports 2,978,617 sections across 229 files spanning statutes, regulations, court rules, agency guidance, constitutions, and additional federal materials, normalized to a common Parquet schema.
- Why it matters: Building and maintaining a cross-jurisdiction primary-law corpus is normally dominated by source-specific acquisition, normalization, citation identity, provenance, and completeness work. This repository supplies unusually broad source adapters plus an explicit human-verified coverage model. Combined with the existing municipal-code finding, it could supply the federal/state layer of a source-linked regulatory change graph rather than another generic legal-search UI.
- Commercial possibilities: Build a cited federal/state regulatory-change and obligation-monitoring service for multi-state regulated businesses, insurers, compliance consultants, law firms, and corporate legal teams. Customers could maintain jurisdiction/topic watchlists, receive section-level change alerts, trace authority and cross-references, and route changed obligations into compliance workflows. A particularly strong combination is Open US Law for federal/state primary law plus `KnitSecurity/municode-pp-cli` for local municipal codes, producing a unified federal-state-local change radar.
- Build-time savings: Approximately 6–12+ months for source connectors, normalized legal records, stable citation/ID handling, provenance, bulk-source ingestion, and jurisdiction-by-jurisdiction coverage auditing.
- Evidence inspected: Actual Apache-2.0 `LICENSE`; repository metadata and exact latest commit; root tree; `README.md`; `scripts/` directory; substantive federal and state-statute ingester trees; deep inspection of `scripts/federal/parse_ecfr_streaming.py`; and deep inspection of `coverage.yml`. The coverage manifest explicitly warns that raw section counts do not prove completeness and requires human verification before publication. No broad automated test suite was observed in the inspected root/tree and code-search pass, so production QA should not be inferred from corpus breadth alone.
- License / rights: The code repository has an actual Apache-2.0 license and is commercially reusable subject to its terms. The project publisher describes the distributed dataset/compilation as CC BY 4.0 and primary-law text as government-edict/public-law material; those statements do not make the Apache code license a blanket license for every upstream or ancillary source. Preserve official-source provenance and independently evaluate source-specific terms/rights for non-statutory materials, court rules, guidance, publisher formatting, and access-restricted sources before commercial redistribution.
- Reuse classification: Directly reusable for code; dataset reuse should follow the published dataset license and source-specific provenance/rights.
- Scores:
  - Technical value: 9/10
  - Commercial value: 10/10
  - Rarity: 10/10
  - Completeness: 8/10
  - Build-time saved: 10/10
  - Data advantage: 10/10
  - High-ticket potential: 9/10
- Next action: Build a 10-jurisdiction versioned mirror/diff benchmark using official-source-backed corpora, measure section-ID stability, freshness, and coverage, and define a unified federal-state-local change schema with the existing Municode finding.

### cyanheads/courtlistener-mcp-server
- Repository: https://github.com/cyanheads/courtlistener-mcp-server
- Commit / revision: `5dfa7622c80b39433f52af9b1ac7b91a16f20523`
- Date discovered: 2026-09-19
- What it contains: An active TypeScript MCP server that wraps CourtListener/RECAP into 14 typed legal-research tools. The inspected implementation covers full-text opinion search/retrieval, citation lookup and citation-network traversal, federal RECAP docket search and entry retrieval, parties/attorneys, judges/courts, appellate oral arguments/transcripts, and federal judicial financial disclosures. The actual docket-search tool validates inputs before consuming rate-limited upstream calls, supports court/party/date/cursor filtering, returns docket metadata plus parties, attorneys, firms and sample filing metadata/storage URLs, and explicitly surfaces RECAP's partial-coverage limitation. The repository includes a dedicated security test and substantial per-tool tests for dockets, opinions, citations, judges, parties, oral arguments, financial disclosures, court lookup, and related service behavior.
- Why it matters: Court-data integration is deceptively expensive because opinions, citation graphs, docket data, judges, disclosures, pagination, rate limits, and partial-coverage semantics all behave differently. This low-attention repository turns that heterogeneity into a typed, tested interface suitable for agentic legal research or a persistent litigation-intelligence layer. It saves the integration work while preserving important limitations instead of pretending RECAP is complete PACER coverage.
- Commercial possibilities: Build a source-linked litigation/precedent monitoring product for law firms, insurers, litigation-finance teams, corporate legal departments, or diligence teams: saved party/case/court watches, new-docket and filing alerts, citation-network changes, judge background, and judicial financial-disclosure/recusal research. Combined with `Vaquill-AI/open-us-law` and `KnitSecurity/municode-pp-cli`, it can add case law and federal docket intelligence to a federal-state-local primary-law graph.
- Build-time savings: Approximately 2–4 months of CourtListener/RECAP API integration, schema normalization, cursor pagination, citation resolution, judge/disclosure normalization, rate-limit handling, and tool-level testing.
- Evidence inspected: Actual Apache-2.0 `LICENSE`; repository metadata; exact latest commit and release diff; `README.md`; `src/` and MCP tool trees; deep inspection of `src/mcp-server/tools/definitions/search-dockets.tool.ts`; root tests tree; and the substantive `tests/tools/` suite containing dedicated tests for docket, opinion, citation, judge, party, oral-argument, financial-disclosure, and court-search tools. The latest commit moves the release to 0.7.1 with stricter inputs/output schemas and updated deployment/runtime plumbing.
- License / rights: Actual repository license is Apache-2.0, so the code is commercially reusable subject to license terms. Upstream CourtListener/RECAP data, hosted documents/audio, API terms, authentication requirements, and rate limits are separate from this code license. RECAP is crowd-sourced and incomplete by court/date, and the inspected server intentionally does not fetch documents marked unavailable without PACER/RECAP access; a commercial product must preserve those coverage caveats rather than imply complete federal-docket coverage.
- Reuse classification: Directly reusable code; upstream data/content remains subject to CourtListener/RECAP terms and source-specific rights/coverage.
- Scores:
  - Technical value: 9/10
  - Commercial value: 9/10
  - Rarity: 8/10
  - Completeness: 9/10
  - Build-time saved: 8/10
  - Data advantage: 8/10
  - High-ticket potential: 9/10
- Next action: Add a small persistent watch/snapshot layer and benchmark 20 representative public federal cases for docket/opinion/citation/disclosure chaining, source-link integrity, rate-limit behavior, and known RECAP coverage gaps before positioning it as litigation intelligence rather than a PACER replacement.
