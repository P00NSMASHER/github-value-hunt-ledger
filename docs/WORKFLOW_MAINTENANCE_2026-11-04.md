# Portfolio workflow maintenance review — 2026-11-04

## Grounded scope and release boundary

An owner-authorized, read-only GitHub inventory inspected **14 repositories** and **239** `.github/workflows/*.yml|*.yaml` files. The prior 237-file estimate is superseded by this exact listing. **No historical workflow or research source was deleted.** There are **6 protected** and **8 unprotected** default `main` branches at this snapshot. Four unprotected repositories are public; four are private and deliberately not identified in this public document.

The 239 current workflow files by repository are: `github-value-hunt-ledger` 71; `permitplate-nyc` 60; `capturebrief` 33; `abvmschoolstarworld` 22; `StarBlox` 16; `x402-product-factory` 13; `portfolio-brain` 11; `trading-platform` 6; `PipsQuestWorld` 3; `resonance-qloo` 2; one private project repository 2; three other private/state repositories 0. Names and internal artifacts of private projects remain outside this public document. These are tracked workflow-file counts, **not** proof of all schedules executing or unique work being delivered.

### Main findings

- **Preserve distinct evidence gates.** Similar-looking workflows cover separately source-bound checks, payment constraints, protected releases, mobile rendering, read-only provider investigations and data integrity. Workflow count alone cannot justify deletion or disabling. No scheduled task was paused or replaced in this maintenance change.
- **Largest maintenance exposure:** the ledger has 71 workflows, including four scheduled workflow files. One existing scout workflow intentionally contains 15 distinct scheduled expressions; the existing tests must continue to verify that cadence. A second high-frequency RETALLY research workflow is deliberately preserved pending measurement rather than silently weakened.
- **New required guard:** `automation/WORKFLOW_MAINTENANCE_BASELINE.json`, `tools/workflow_maintenance_guard.py`, and `tests/test_workflow_maintenance.py` fail closed on unexpected ledger workflow additions/deletions, schedule modifications, token write-scope expansion, unreviewed privileged PR triggers, broad permissions and remote-shell pipes. The protected required `release-gate` now runs this guard on every PR; its adversarial tests prove the rejection paths. This is scoped to the ledger, not a replacement for any other repository's branch protections.
- **Retirement verified:** the active 14-worker `automation/hunter_schedule.json` targets trading, verified revenue, RETALLY social, novel discovery, engineering acceleration, ABVM, PermitPlate, CaptureBrief and Portfolio Brain. StarBlox and dedicated Genesis research are absent from the active allowlist. `.github/workflows/active-scout-scope-ci.yml` enforces this. The retired StarBlox repository retains historical workflows, none scheduled; it is **not** reactivated.
- **GitHub protection blocker:** public default branches still missing enforced rulesets require the owner's administrative ruleset operation. This GitHub connector exposes read/PR/commit but not the ruleset-write endpoint. The private-repository ruleset read returned HTTP 403: `Upgrade to GitHub Pro or make this repository public to enable this feature`. Preserve private repositories; never treat a workflow test as equivalent to an enforced branch ruleset. No bypass or invisible protection change was made.

## Source-bound PR chain reconciliation

The initial read observed 28 open PRs, 20 of them drafts. Eight overlapping or obsolete proposals were closed **unmerged** with an individual explanation, preserving their original branches and review history:

- Ledger generated runtime snapshots: #998, #992, #988, #983 and #979. Exact candidate activation clocks precede the current protected `main` state; these diffs were generated `intelligence/` snapshots, not accepted customer results.
- PipsQuestWorld duplicate ancestors: #338 was a strict ancestor of draft #355 (641 commits ahead, 0 behind); #339 of #343 (135 ahead, 0 behind); #351 of #355 (72 ahead, 0 behind). Each older PR was closed **without merging** after exact ancestry validation. Their newer successors remain unreleased drafts.

No other stale draft was automatically merged or discarded: multiple PipsQuestWorld and x402-product-factory draft heads are deeply diverged from `main`, with several hundred or thousand additional commits and overlapping workflow trees. Their future work must first be separated into bounded current-main PRs, with real browser/deployment and branch-rule acceptance, rather than merging a whole historic branch. Current source files and synthetic/test records are preserved.

The only remaining open ledger PR from the inspected batch, #995, carries distinct exact-source Scout evidence and was **kept** rather than discarded with the runtime snapshots.

## Explicit unresolved dependencies

1. Apply enforceable protected-main rulesets to the appropriate **active** unprotected repositories through supported GitHub administrative controls; only verified required checks should be pinned. Do not fake this through a repository document or CI status. Public projects and private-repo plan limitations require separate handling.
2. Reconstruct deeply divergent draft features in bounded independently testable protected PRs. Preserve branches and original evidence; do not force merge, blindly close, or infer that draft QA passed.
3. Independently verify delivered outcomes for commercial and engineering acceptance. Green CI and a smaller PR count alone are not proof of operational success.

**Verification boundary:** A successful protected merge of this document and the maintenance guard demonstrates release of a *preventive ledger CI gate*. It does not demonstrate that branch protections in other repositories were installed or that every historical draft was delivered.
