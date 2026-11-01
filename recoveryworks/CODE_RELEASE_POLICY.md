# RETALLY code integration policy — owner authorized

**Effective October 21, 2026. Scope:** `P00NSMASHER/github-value-hunt-ledger` RETALLY internal engineering, including its freight original-document/reconciliation research, RecoveryWorks seven-branch application, synthetic OCI backup transport, and related engineering workflows.

The repository owner authorizes current and future internal RETALLY **source changes, code quality checks, and integration without a required separate human/independent code-review prerequisite**. The automated evidence-based QA process (exact-head tests, source checks, security checks, release-gate CI, reproducible artifacts and protected-branch rules) remains required. Previously documented human code-review prerequisites are superseded **only as code-review prerequisites**. A fabricated reviewer approval or simulated reviewer identity is neither needed nor permitted.

Removing the human code-review requirement does **not** remove the repository's exact-action authorization requirements for merges or production changes, and does not turn internal invoice arithmetic, publisher payment annotations, or synthetic examples into independently proven customer receipts, tariffs or recovered cash. Research work may be approved as research without claiming real freight accuracy or cash settlement.

## Required automated merge conditions

1. Verify the exact proposed commit, its parent/source lineage, and diff. No unrelated changes, credentials or customer originals.
2. All required exact-head GitHub CI, security checks and repository release-policy checks must complete successfully. A pending, failing or cancelled check is not a pass.
3. Respect existing GitHub protected-branch rules and merge permissions. Do **not** force-push, dismiss checks, spoof reviews, disable verification jobs or bypass GitHub protections to achieve a merge.
4. Stage/merge dependent changes in correct order, rechecking the current target SHA. Keep changes reversible and retain test evidence.

## GitHub main branch enforcement

The active GitHub ruleset in [`.github/retally-main-ruleset.json`](../.github/retally-main-ruleset.json) applies to **only the default branch**. It requires pull requests, zero human approvals, GitHub Actions `release-gate` against the latest base branch, no bypass actors, no deletions and no force pushes.

**Live readback verified October 21, 2026 at 22:07 America/New_York:** [repository ruleset 25608380](https://github.com/P00NSMASHER/github-value-hunt-ledger/rules/25608380) is `active`, targets `~DEFAULT_BRANCH`, and reports `current_user_can_bypass=never`. Its sole required check is `release-gate` from GitHub Actions integration `15368`, with strict up-to-date enforcement. The branch metadata reports `protected=true`. The checked-in manifest records this verified state; it is not a substitute for a new provider readback after any later administration change.

**All four automated writers use PRs only.** Scout #579, Integrator #548, Catalog #550 and Technology Intelligence #558 established provider-backed bot PR and exact-head CI acceptance. [PR #582](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/582) removed every legacy direct-main workflow fallback and merged at `6e01088dcbab261a33a035f2c5679eaa28ea516c` after all required checks, including the Windows encrypted-backup job, passed. Bot-created PRs require explicit `workflow_dispatch` CI bound to the exact commit. Missing variables, provider failures or concurrent updates must never reactivate a direct-main path.

The PR recording this verified active policy is the post-activation no-review canary: it must merge through the normal GitHub PR route after fresh exact-head CI against the current base. Opening the PR or passing offline tests does not itself prove its protected merge. Retain the actual PR, check-run and resulting merge commit as the acceptance evidence. Do not test protection by attempting an unauthorized write, disabling a rule, using a bypass actor or fabricating a reviewer.

For future checks, read `GET /repos/P00NSMASHER/github-value-hunt-ledger/rulesets`, then the returned ruleset detail URL and branch metadata. When the client supports it, also inspect `GET /repos/P00NSMASHER/github-value-hunt-ledger/rules/branches/main`; an unsupported client endpoint is not evidence that the provider lacks protection. Do not recreate duplicate rulesets or relax existing controls.

**Only `release-gate` is globally required**: `Repository Release Gate` runs for every pull request and its final job fails unless all four independent CI lanes pass. `main-only-policy` and the specialized `RecoveryWorks` jobs are path-filtered and must *not* be required globally, or unrelated PRs can become permanently unmergeable. Never disable these specialized checks when relevant.

## Separate operational and customer boundaries — NOT waived

- A code merge is **not** an approval to create billed infrastructure, turn on a VM service, publish Cloudflare DNS/tunnels, create Access Allow policies, or process customer data.
- Keep `production_release=HOLD` and simulation-only runtime restrictions until distinct live host, authentication, privacy, encrypted-backup custody/retention, and customer authorization evidence is verified.
- Case source reviews, customer audit consent, rate/contract truth, independent external bank/carrier settlement validation, customer claim authorization, and domain-specific reviewer identities remain unchanged. They are financial/operational proof, **not code review**.
- Preserve the historical OCI synthetic orphan, the immutable quarantine/attempt/acceptance receipts, and no new spending.

This owner authorization removes the **reviewer prerequisite**, not automated code validation or external evidence requirements. The owner may revise this policy in a subsequent audited source change.
