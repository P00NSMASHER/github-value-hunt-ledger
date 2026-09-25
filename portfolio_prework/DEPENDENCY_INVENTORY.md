# Dependency Inventory

Inspected **14 dependency manifests** across the seven repositories at their pinned snapshot SHAs. No dependencies were installed during this step.

## Repository summary

| Repository | Manifests | Ecosystems | Lockfile discovered | Key reproducibility note |
|---|---:|---|---|---|
| `P00NSMASHER/github-value-hunt-ledger` | 6 | Python/pip | No | Production sets mostly use compatible ranges; CI deps exact-pinned |
| `P00NSMASHER/StarBlox` | 3 | npm + Cargo | No | Rust direct pins exact; npm caret ranges; no discovered npm/Cargo lock |
| `P00NSMASHER/abvmschoolstarworld` | 1 | npm | No | All three dependencies use `latest` |
| `P00NSMASHER/trading-platform` | 4 | Python/pip | Yes | Runtime/dev/optional lock files exact-pin environments |
| `P00NSMASHER/permitplate-nyc` | 0 | none discovered | No | No manifest discovered |
| `P00NSMASHER/permitplate-state` | 0 | none discovered | No | No manifest discovered |
| `P00NSMASHER/capturebrief` | 0 | none discovered | No | No manifest discovered |

## Architecture observations

- **DEP-OBS-001 [REVIEW]** ABVM uses floating `latest` npm dependencies and has no discovered npm lockfile at the pinned snapshot.
- **DEP-OBS-002 [REVIEW]** StarBlox exact-pins its direct Rust dependencies but has no discovered Cargo.lock; its npm dependencies use caret ranges and no npm lockfile was discovered.
- **DEP-OBS-003 [REVIEW]** Primary portfolio production Python requirements mainly use version ranges; only the shared CI requirements file is exact-pinned.
- **DEP-OBS-004 [INFO]** The market-surveillance research repository has exact runtime, dev, and optional safer-model lock files, giving it the strongest explicit dependency reproducibility of the inspected repositories.
- **DEP-OBS-005 [INFO]** PermitPlate NYC, permitplate-state, and CaptureBrief have no dependency manifests discovered by the pinned snapshot; the inventory deliberately does not equate that with dependency-free software.

## Portfolio Brain implication

Dependency state should become part of each repository snapshot and promotion evidence. Candidate changes that alter a manifest or lockfile should automatically trigger dependency-specific validation and provenance capture. Reproducibility should be measured from committed dependency evidence, not inferred from a successful install on one runner.

Machine-readable source: `DEPENDENCY_INVENTORY.json`.
