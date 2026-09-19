# Finance / AP / Recovery

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
### pengyulong/InvoiceAuditAgent
- Repository: https://github.com/pengyulong/InvoiceAuditAgent
- Commit / revision: b53902513902fab91ddd7143585d898cf0ce869b
- Date discovered: 2026-09-19
- What it contains: Contract/invoice audit project with Vue/FastAPI-oriented architecture, OCR/LLM design documents, frontend/backend/deploy folders, tests, and deployment documentation.
- Why it matters: The concept and repository structure overlap directly with contract-to-invoice cross-checking, but the README itself says core functionality is still incomplete, so this is more useful as a design reference than a ready engine.
- Commercial possibilities: Architecture/reference material for AP audit and contract/invoice matching; not currently a strong direct-reuse candidate.
- Build-time savings: Low-Medium until deeper code inspection proves the backend is more complete than the README status suggests.
- Evidence inspected: README.md marks core functionality, AI integration, tests, and deployment as pending; root contains backend/frontend/tests/docs/deployment material.
- License / rights: No repository license detected.
- Reuse classification: Inspect / learn / clean-room implementation only unless permission is established.
- Scores:
  - Technical value: Medium
  - Commercial value: Medium-High conceptually
  - Rarity: Low-Medium
  - Completeness: Low-Medium
  - Build-time saved: Low-Medium
  - Data advantage: Low
  - High-ticket potential: Medium
- Next action: Deprioritize unless backend inspection reveals functioning audit logic not reflected in the README; favor mature permissive components instead.
