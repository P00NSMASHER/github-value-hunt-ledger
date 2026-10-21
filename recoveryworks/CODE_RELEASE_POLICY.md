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

The proposed GitHub ruleset in [`.github/retally-main-ruleset.json`](../.github/retally-main-ruleset.json) applies to **only the default branch** and requires pull requests, zero human approvals, GitHub Actions `release-gate`, no bypass actors, no deletions or force pushes, and tests against the latest base branch. It is currently **disabled in the checked-in manifest** because scheduled direct-main writers have not been migrated. It is a declarative configuration candidate, not proof that GitHub has installed or enforced it.

**Do not change `enforcement` to `active` until the automated writers in `catalog-append.yml`, `integrator-sync.yml`, `public-repo-hunter.yml`, and `technology-intelligence.yml` no longer push directly to `main`; otherwise the owner-approved Scout/Integrator pipelines would be stranded.** The offline manifest test fails an active configuration while those known writer paths remain. Route each writer through an isolated branch and actual PR with exact-head CI; verify the event/credentials model rather than assuming GitHub's `GITHUB_TOKEN`-created PR triggers CI. 

After all writers migrate, the repository-owner administrator must apply the active manifest through GitHub's Settings → Rules → Rulesets interface (or an appropriately authenticated `gh api --method POST repos/P00NSMASHER/github-value-hunt-ledger/rulesets --input .github/retally-main-ruleset.json`). Do not paste credentials, relax repository protections or use an unverified token. Read back `GET /repos/P00NSMASHER/github-value-hunt-ledger/rulesets` and `GET /repos/P00NSMASHER/github-value-hunt-ledger/rules/branches/main` to confirm enforcement, then verify a small disposable PR merges with exact-head CI success and **no human review**. A failed or unavailable admin operation does not count as protection.

**Only `release-gate` is globally required**: `Repository Release Gate` runs for every pull request and its final job fails unless all four independent CI lanes pass. `main-only-policy` and the specialized `RecoveryWorks` jobs are path-filtered and must *not* be required globally, or unrelated PRs can become permanently unmergeable. Never disable these specialized checks when relevant.

## Separate operational and customer boundaries — NOT waived

- A code merge is **not** an approval to create billed infrastructure, turn on a VM service, publish Cloudflare DNS/tunnels, create Access Allow policies, or process customer data.
- Keep `production_release=HOLD` and simulation-only runtime restrictions until distinct live host, authentication, privacy, encrypted-backup custody/retention, and customer authorization evidence is verified.
- Case source reviews, customer audit consent, rate/contract truth, independent external bank/carrier settlement validation, customer claim authorization, and domain-specific reviewer identities remain unchanged. They are financial/operational proof, **not code review**.
- Preserve the historical OCI synthetic orphan, the immutable quarantine/attempt/acceptance receipts, and no new spending.

This owner authorization removes the **reviewer prerequisite**, not automated code validation or external evidence requirements. The owner may revise this policy in a subsequent audited source change.
