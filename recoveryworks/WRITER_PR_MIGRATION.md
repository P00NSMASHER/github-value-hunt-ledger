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
