# GovCon / CaptureBrief

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
### MindPetal/sam-search
- Repository: https://github.com/MindPetal/sam-search
- Commit / revision: 019b31dca0f980e79117a7c559777cb357a2a385
- Date discovered: 2026-09-19
- What it contains: Small but functioning Python SAM.gov opportunity search client with NAICS filtering, date handling, formatting, GitHub Actions execution, Teams posting, generated API client code, configuration, and tests.
- Why it matters: It proves and packages the core SAM.gov opportunity-ingestion loop needed by CaptureBrief, including daily scheduled retrieval and normalization/formatting logic.
- Commercial possibilities: Reuse the ingestion layer inside CaptureBrief while replacing Teams delivery with qualification, evidence linking, scoring, and customer-specific opportunity workflows.
- Build-time savings: Medium-High for reliable SAM.gov ingestion and scheduled search plumbing.
- Evidence inspected: README.md; search.py with SAM API calls, formatting, date/set-aside handling; test_search.py with pytest coverage for API search and formatting behavior.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT terms.
- Scores:
  - Technical value: Medium
  - Commercial value: High as a CaptureBrief component
  - Rarity: Medium
  - Completeness: Medium-High for its narrow purpose
  - Build-time saved: Medium-High
  - Data advantage: Medium
  - High-ticket potential: Medium-High when embedded in a decision product
- Next action: Map its returned SAM fields to CaptureBrief's evidence model and design around the documented non-federal API request limit rather than copying its Teams-oriented output layer.
