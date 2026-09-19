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
