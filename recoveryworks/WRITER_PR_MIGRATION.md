# RETALLY automated writer PR migration — first release stage

**Status:** code policy only. Existing scheduled writers remain unchanged.

Four workflows still push data directly to `main`: Scout,
`catalog-append.yml`, `integrator-sync.yml`, and
`technology-intelligence.yml`. They cannot be switched to a mandatory-PR
branch ruleset without a validated replacement for GitHub Actions-token
pull-request creation and exact SHA-tested automatic integration.

`tools/retally_writer_proposal_policy.py` defines independent,
fail-closed path allowlists for the four lanes. It is **pure validation**:
no network access, credentials, GitHub mutations, VM access, cloud
subscriptions, customer data or release decisions. Eight adversarial tests
cover unsafe paths, traversal, secrets/code extensions, scope crossing, wrong
parents/SHAs, duplicate files, deletes and unsafe TI-generated manifests.

## Required activation sequence

1. Complete owner-only synthetic PR creation, explicit
   `workflow_dispatch`, five real release-gate jobs and exact-head canary
   merge. This is tracked in PR #530. Do not assume that GitHub's
   `GITHUB_TOKEN`-created PR triggers normal `pull_request` CI events.
2. For each writer, stage its changed paths only, create a deterministic
   run-id-scoped `automation/retally-<lane>-<run_id>-<attempt>` branch,
   push without force, validate `main` parent/target and exact file allowlist.
3. Create only a same-repository bot-authored PR. Dispatch genuine release
   tests on that proposed branch and require exact-run/commit evidence; a
   failed or absent check leaves the proposal as a hold.
4. Merge via normal GitHub PR only after refreshed source/main hashes,
   actual passing CI and repository rules. New main activity or an
   unexpected filename is not grounds for a force push or auto waiver.
5. Keep a durable retry/reconciliation path for PR creation disallowed by
   repository Actions settings and for real concurrent main-branch changes.
   Do not treat opening an unattended PR as successful main publication.
6. **Only after all four lanes actually work unattended**, update the
   `.github/retally-main-ruleset.json` from `disabled` to `active`,
   apply it through GitHub admin controls, and test that direct pushes are
   rejected while no-review automated PRs pass.

This policy is deliberately not wired into the four scheduled jobs yet,
so it cannot interrupt existing ongoing Scout and technology-intelligence
work while the synthetic integration test is pending.

**Production release status: HOLD.** This is code publishing control, not
customer audit review, bank verification, external claim sending, cloud
spending, private host installation or data-retention acceptance.

## Staged opt-in writer changes

The four workflows now offer a PR publishing path behind the disabled repository variable the independent lane switches RETALLY_SCOUT_PR_ENABLED, RETALLY_CATALOG_PR_ENABLED, RETALLY_INTEGRATOR_PR_ENABLED and RETALLY_TECHNOLOGY_PR_ENABLED. Without that variable they retain their existing scheduled behavior. With the variable explicitly set to true after successful canary acceptance, the source job pushes only its isolated, run-specific evidence branch and a separate minimally scoped job proposes the PR. This source change alone neither activates new behavior nor enables main protection. Production release remains HOLD.

### Verified Python entry-point preflight

The production runner executes both proposed GitHub automation commands with `python -m tools.retally_automated_pr_proposal` and `python -m tools.retally_automated_pr_merge`, from the repository root. Direct file invocation fails with `ModuleNotFoundError` because Python starts with `tools/` rather than the repository root on its import search path. A real Windows exact-SHA test exposed this; the fixed module launch is required for successful unattended proposals. Automated tests assert the entry points import successfully but refuse an untrusted/missing Actions identity before any provider request.

## October 21 — increment-only payload safety

The existing Catalog and Integrator trigger files contain historical operations.
A disposable, exact-source replay of the old Integrator payload reproduced a
dangerous unintended result: it would append the September 20 Integrator queue
advice to the current `SEARCH_QUEUE.md` while adding a new synthetic pilot.
This is **not** accepted as a new business recommendation or evidence.

Both helpers now compare the **frozen triggering Git SHA** against its
`github.event.before` parent revision before running any target update:

- Integrator only accepts an exact **append-only extension** to its original
  UTF-8 payload and processes only the newly appended complete operation
  sections. Existing 25-KB historical sections can never be replayed merely
  because their old marker disappeared from today's target.
- Catalog accepts only **new keys** in its JSON `append` mapping. Existing
  target paths and values must be byte-equivalent and present; otherwise the
  run fails closed instead of silently regenerating unrelated catalog history.
- Frozen input bytes must match `git show <github.sha>:<payload path>`.
  Source SHAs must be exact; no arbitrary branch, unknown Unicode, duplicate
  JSON keys, executable-path target, symlink or stale changed payload is
  accepted. The operation delta is written only to an exclusive owner-only
  temporary file.
- A full replacement, deletion, changed historical operation or ambiguous
  push is a HOLD. Future new instructions must use a newly appended section
  (Integrator) or a new append-map key (Catalog).

This change does **not** activate `RETALLY_CATALOG_PR_ENABLED` or
`RETALLY_INTEGRATOR_PR_ENABLED`; both remain separate owner-controlled
switches. It also does not process the old September 20 queue advice.
Customer production and financial-source authorization remain HOLD.


## Owner-authorized PR-only enforcement after four live writer acceptances

All four writer lanes have now been exercised through real GitHub PR
creation and independently dispatched exact-head release-gate CI:

- Scout PR #544: **automatic merge success**.
- Integrator PR #548: **automatic merge success**.
- Catalog PR #550: proposal and all CI passed, but unrelated main
  movement correctly stopped automatic merging. The owner later merged
  the same source. This is evidence of an outstanding source-race
  recovery gap, **not** proof of unattended reconciliation.
- Technology Intelligence PR #558: **automatic merge success**, with
  30 source-scoped generated files and no direct-main write.

The PR-only source migration removes all four direct-main fallback
branches. If a lane flag is missing or not exactly true, the writer
fails visibly without publishing anything. Technology Intelligence's
CLI likewise requires an explicit isolated PR branch and refuses to
push to main from the normal production path.

The declared GitHub main ruleset remains DISABLED until repository
administration applies it and checks the live ruleset effect. This
source change does not create/remove any rules or amend customer,
Oracle or commercial release permissions. Customer production HOLD.
