# Parallel Portfolio Prework Progress

Working branch: `portfolio-parallel-prep`

| Step | Workstream | Status |
|---:|---|---|
| 1 | Portfolio inventory | **COMPLETE** |
| 2 | Stable project IDs | **COMPLETE** |
| 3 | Repository snapshot generator | **COMPLETE** |
| 4 | SHA-based change detector | **COMPLETE** |
| 5 | Durable build-state schema | **COMPLETE** |
| 6 | Autonomy matrix | **COMPLETE** |
| 7 | GitHub workflow inventory | **COMPLETE** |
| 8 | Test-suite inventory | PENDING |
| 9 | Dependency inventory | PENDING |
| 10 | Architecture evidence bundle | PENDING |

## Step 1 result

Created:
- `portfolio_prework/portfolio_inventory.json`
- `portfolio_prework/PORTFOLIO_INVENTORY.md`

Captured the seven currently connected repositories at exact snapshot SHAs and inventoried the major businesses, products, research systems, formal experiments, and shared infrastructure already identified.

## Step 2 result

Created:
- `portfolio_prework/PROJECT_ID_REGISTRY.json`
- `portfolio_prework/PROJECT_ID_REGISTRY.md`

Established immutable top-level project IDs, aliases, parent relationships, repository scope, categories, and hard boundaries. Validation confirms 12 project identities, 12 unique IDs, zero duplicate IDs, and zero alias collisions.

## Step 3 result

Created:
- `portfolio_prework/snapshot_repos.json`
- `portfolio_prework/build_portfolio_snapshot.py`
- `portfolio_prework/test_build_portfolio_snapshot.py`
- `portfolio_prework/repository_snapshot.json`
- `portfolio_prework/REPOSITORY_SNAPSHOT.md`
- `.github/workflows/portfolio-prework-ci.yml`

The snapshot generator uses the GitHub API and Python standard library to capture exact HEAD SHAs, recursive tree structure, workflow paths, test paths, dependency manifests, README locations, file counts and top-level structure without modifying downstream repositories. The generated baseline captured all 7 configured repositories with 0 failures and 0 truncated trees. Focused GitHub Actions CI passed after correcting the test import and regex escaping.


## Step 4 result

Created:
- `portfolio_prework/detect_repository_changes.py`
- `portfolio_prework/test_detect_repository_changes.py`
- `portfolio_prework/repository_delta.json`
- `portfolio_prework/REPOSITORY_DELTA.md`

The detector performs the cheapest possible first check: current default-branch HEAD versus the cached snapshot SHA. Unchanged repositories stop there and are explicitly marked as not requiring deep inspection. Changed repositories alone receive a compare request and changed-file list. The current baseline found 6 unchanged repositories and 1 changed repository (`abvmschoolstarworld`), with 6 changed files across 13 commits. Focused CI now discovers all prework tests and is green.

## Step 5 result

Created:
- `portfolio_prework/PORTFOLIO_BUILD_STATE.schema.json`
- `portfolio_prework/PORTFOLIO_BUILD_STATE.json`
- `portfolio_prework/validate_build_state.py`
- `portfolio_prework/test_validate_build_state.py`

The durable state now records architecture/build version, current and completed steps, per-repository inspection SHAs/status, accepted architectural decisions, artifacts, test evidence, blockers and the exact next action. Standard-library validation enforces resumability invariants, including unique completed steps, valid SHAs, valid status enums, unique decision/artifact identities and exact alignment between `current_step` and `next_action.step`. Focused CI passed with the new build-state tests included.

## Step 6 result

Created:
- `portfolio_prework/AUTONOMY_ACTION_TAXONOMY.json`
- `portfolio_prework/test_autonomy_action_taxonomy.py`
- `portfolio_prework/AUTONOMY_MATRIX.json`
- `portfolio_prework/AUTONOMY_MATRIX.md`
- `portfolio_prework/test_autonomy_matrix.py`

Step 6 now defines the global autonomy classes and applies them to all 12 canonical projects. OBSERVE is autonomous, EXPERIMENT is bounded to non-consequential work, MODIFY is limited to isolated candidate changes with testing/verification gates, and ACT is never generally autonomous. Recovery/customer/financial/production actions remain human-gated, child-facing consequential changes remain human-gated, and live trading/broker execution is explicitly prohibited. Matrix coverage matches the project registry exactly, and focused CI is green.

## Step 7 result

Created:
- `portfolio_prework/WORKFLOW_INVENTORY.json`
- `portfolio_prework/WORKFLOW_INVENTORY.md`
- `portfolio_prework/test_workflow_inventory.py`

Inventoried all 47 workflow paths present in the pinned Step 3 repository snapshot across all seven repositories. The inventory records triggers, declared permissions, jobs, and risk markers such as schedules, secrets, write permissions, and Pages/deployment behavior. Exact coverage verification found zero missing and zero extra workflows, and no `pull_request_target` use at the pinned SHAs. Existing write/deploy credentials are explicitly treated as workflow capabilities rather than inherited Portfolio Brain authority.

## Rule

Only one step is completed per user authorization. After each step, stop and wait for `CONTINUE`.
