# Construction / ScopeSignal

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
### Fajendagba/Construction-Change-Order-Engine
- Repository: https://github.com/Fajendagba/Construction-Change-Order-Engine
- Commit / revision: 60f5ab99bfb97647039e6cec280c246a10f8a856
- Date discovered: 2026-09-19
- What it contains: Laravel/PostgreSQL construction change-order API organized around domain-driven design, explicit change-order state transitions, project budget line items, audit metadata, events, queues, realtime updates, and strict static-analysis/testing conventions.
- Why it matters: The source includes concrete construction-specific workflow logic instead of generic CRUD. ChangeOrderService implements creation and state transitions; BudgetRecalculationService applies approved changes to cost-code and project totals.
- Commercial possibilities: Architecture reference for ScopeSignal/change-order detection: detected scope changes can flow into a defensible proposed-change state machine, review process, cost-code impact, audit trail, and budget update.
- Build-time savings: High as a clean-room architecture reference for domain states, approval flow, events, and budget propagation.
- Evidence inspected: README.md; app/Domain/ChangeOrder/Services/ChangeOrderService.php; app/Domain/ProjectBudget/Services/BudgetRecalculationService.php.
- License / rights: No repository license detected.
- Reuse classification: Inspect / learn / clean-room implementation only unless permission is established.
- Scores:
  - Technical value: High
  - Commercial value: High as ScopeSignal reference architecture
  - Rarity: Medium-High
  - Completeness: Medium-High
  - Build-time saved: High for architecture/design
  - Data advantage: Low
  - High-ticket potential: High if paired with document/change detection
- Next action: Clean-room the state model and budget-impact concepts, then search for permissively licensed RFI/submittal/document-diff components that supply the upstream detection signal.
