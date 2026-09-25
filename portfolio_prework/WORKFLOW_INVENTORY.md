# GitHub Workflow Inventory

Pinned workflow inventory across **7 repositories** and **47 workflows**.

## Repository counts

| Repository | Workflows |
|---|---:|
| `P00NSMASHER/github-value-hunt-ledger` | 24 |
| `P00NSMASHER/StarBlox` | 1 |
| `P00NSMASHER/abvmschoolstarworld` | 5 |
| `P00NSMASHER/trading-platform` | 2 |
| `P00NSMASHER/permitplate-nyc` | 12 |
| `P00NSMASHER/permitplate-state` | 0 |
| `P00NSMASHER/capturebrief` | 3 |

## Automation characteristics

- Write/deploy-capable workflows: **9**
- Scheduled workflows: **9**
- Workflows referencing secrets: **8**
- `pull_request_target` workflows: **0**

## Risk-relevant workflows

| Repository | Workflow | Triggers | Permissions | Risk markers |
|---|---|---|---|---|
| `P00NSMASHER/github-value-hunt-ledger` | `catalog-append.yml` | push | contents: write | write_permission |
| `P00NSMASHER/github-value-hunt-ledger` | `fmc-tariff-recover-merge.yml` | workflow_run, workflow_dispatch, push | contents: read actions: read | uses_secrets, manual_dispatch |
| `P00NSMASHER/github-value-hunt-ledger` | `freight-site-pages.yml` | pull_request, push, workflow_dispatch | contents: read; job-level Pages deployment write permissions present | write_permission, deployment_or_pages, manual_dispatch |
| `P00NSMASHER/github-value-hunt-ledger` | `integrator-sync.yml` | push | contents: write | write_permission |
| `P00NSMASHER/github-value-hunt-ledger` | `public-repo-hunter.yml` | workflow_dispatch, schedule | contents: write | write_permission, uses_secrets, scheduled, manual_dispatch |
| `P00NSMASHER/github-value-hunt-ledger` | `technology-intelligence.yml` | push, pull_request | contents: read; job-level write path present | write_permission, uses_secrets |
| `P00NSMASHER/github-value-hunt-ledger` | `urdb-ledger.yml` | workflow_dispatch, push | contents: read | uses_secrets, manual_dispatch |
| `P00NSMASHER/abvmschoolstarworld` | `health-dashboard.yml` | workflow_run, schedule, workflow_dispatch | contents: read actions: read | scheduled, manual_dispatch |
| `P00NSMASHER/abvmschoolstarworld` | `pages.yml` | push, workflow_dispatch | contents: read pages: write id-token: write | write_permission, deployment_or_pages, manual_dispatch |
| `P00NSMASHER/abvmschoolstarworld` | `refresh-health.yml` | schedule, workflow_dispatch | contents: read | scheduled, manual_dispatch |
| `P00NSMASHER/abvmschoolstarworld` | `sync-study-pack.yml` | schedule, workflow_dispatch | contents: write pages: write id-token: write | write_permission, deployment_or_pages, scheduled, manual_dispatch |
| `P00NSMASHER/permitplate-nyc` | `current-graph.yml` | workflow_dispatch, schedule, push | contents: read | scheduled, manual_dispatch |
| `P00NSMASHER/permitplate-nyc` | `detection-ledger.yml` | workflow_dispatch, schedule, push | contents: read | uses_secrets, scheduled, manual_dispatch |
| `P00NSMASHER/permitplate-nyc` | `event-recency.yml` | pull_request, push | contents: read | uses_secrets |
| `P00NSMASHER/permitplate-nyc` | `launch-readiness.yml` | workflow_dispatch, push | contents: read | uses_secrets, manual_dispatch |
| `P00NSMASHER/permitplate-nyc` | `material-change.yml` | pull_request, push | contents: read | uses_secrets |
| `P00NSMASHER/permitplate-nyc` | `public-site-build.yml` | workflow_dispatch, push | contents: read pages: write id-token: write | write_permission, deployment_or_pages, manual_dispatch |
| `P00NSMASHER/permitplate-nyc` | `scoring-readiness.yml` | workflow_dispatch, schedule, push | contents: read | scheduled, manual_dispatch |
| `P00NSMASHER/permitplate-nyc` | `source-health.yml` | workflow_dispatch, schedule, push | contents: read | scheduled, manual_dispatch |
| `P00NSMASHER/capturebrief` | `abvm-school-pack.yml` | push, schedule, workflow_dispatch | contents: write | write_permission, scheduled, manual_dispatch |

## Architecture observations

- **WF-OBS-001 [INFO]** Most workflows are CI, validation, ingestion, or read-only probes; write/deploy authority is concentrated in a smaller subset.
- **WF-OBS-002 [REVIEW]** Write-capable workflows exist in the primary intelligence repository, ABVM, PermitPlate, and CaptureBrief. Portfolio Brain must not treat existing GitHub workflow write authority as blanket autonomy.
- **WF-OBS-003 [REVIEW]** CaptureBrief contains a scheduled write-capable workflow named 'Refresh ABVM school pack', which is cross-project behavior and should remain explicitly represented in architecture boundaries.
- **WF-OBS-004 [INFO]** No inspected workflow uses pull_request_target at the pinned snapshot SHAs.
- **WF-OBS-005 [REVIEW]** Pages deployment workflows carry write/id-token authority. Future Portfolio Brain automation should invoke or observe them only through explicit deployment gates rather than inheriting their credentials.
- **WF-OBS-006 [INFO]** permitplate-state has no GitHub Actions workflows in the pinned snapshot.

## Governance implication

Existing workflow credentials and deployment permissions are capabilities of those workflows, not permissions granted to Portfolio Brain. The Step 6 autonomy matrix remains authoritative: production deployment, external customer actions, money movement, and other consequential ACT operations remain human-gated, while live trading/execution remains prohibited.

Machine-readable source: `WORKFLOW_INVENTORY.json`.
