# Test Suite Inventory

Discovered **367 test paths** across the seven pinned repositories. This step inventories the test surface without running every downstream suite.

## Repository summary

| Repository | Test paths | Frameworks / mechanisms |
|---|---:|---|
| `P00NSMASHER/github-value-hunt-ledger` | 205 | python-unittest, pytest |
| `P00NSMASHER/StarBlox` | 43 | vitest, cargo-test, shell-smoke-checks |
| `P00NSMASHER/abvmschoolstarworld` | 10 | node-test, playwright, static-validation |
| `P00NSMASHER/trading-platform` | 26 | pytest, secret-scan |
| `P00NSMASHER/permitplate-nyc` | 40 | direct-node-regression-scripts |
| `P00NSMASHER/permitplate-state` | 0 | none discovered |
| `P00NSMASHER/capturebrief` | 43 | python-unittest, compileall, cli-contract-checks |

## Primary repository breakdown

| Area | Test paths |
|---|---:|
| `ai_business_os` | 13 |
| `business_os` | 10 |
| `experiments` | 1 |
| `freight` | 60 |
| `production` | 28 |
| `recoveryworks` | 66 |
| `tests` | 27 |

## Notable observations

- **TEST-OBS-001 [INFO]** The seven-repository snapshot contains 367 discovered test paths; six repositories contain tests and permitplate-state contains none.
- **TEST-OBS-002 [INFO]** The primary portfolio repository has the largest discovered test surface, split across AI Business OS, legacy Business OS, Freight, Production, RecoveryWorks, experiments, and technology-intelligence tests.
- **TEST-OBS-003 [REVIEW]** ABVM defines a qa:unit script but the pinned GitHub workflow set does not invoke qa:unit; static and Playwright browser QA are invoked.
- **TEST-OBS-004 [REVIEW]** The legacy business_os subtree has discovered tests but no matching GitHub workflow invocation was found in the pinned workflow set.
- **TEST-OBS-005 [INFO]** Step 8 inventories tests without executing every downstream suite, avoiding unnecessary compute while preserving exact path coverage.

## Architecture implication

Portfolio Brain should route validation to the smallest relevant existing suite instead of blindly running every repository's full test corpus after each candidate change. Test selection can later be driven by changed paths, project identity, capability graph edges, and risk class.

Machine-readable source: `TEST_SUITE_INVENTORY.json`.
