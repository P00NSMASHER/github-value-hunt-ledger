# RETALLY guarded GitHub auto-merge — synthetic canary

This workflow is a **permission/CI integration probe**, not a customer or
production release. It is deliberately inert and only runs when the repository
owner creates an exact `automation/retally-guard-canary-YYYYMMDD-xxxxxxxx`
branch with one bounded Markdown file under `automation/canary/`.

The GitHub Actions run verifies that one file is the **only change** and the
commit parent equals the currently observed `main`. It uses a scoped
`GITHUB_TOKEN` to create a pull request, explicitly dispatches the existing
`Repository Release Gate` workflow on the exact canary branch, and waits for
the **five** release-check jobs (four test lanes plus final `release-gate`)
to pass. It rechecks current `main`, the PR's head and base SHAs, then asks
GitHub to merge the synthetic PR by **normal PR merge**, pinned to the exact
canary head. It never force-pushes, suppresses a check, spoofs a review, or
modifies GitHub protection settings.

**Critical prerequisite:** GitHub's repository Actions setting *Allow GitHub
Actions to create and approve pull requests* must permit PR creation by a
workflow token. If disabled, the canary fails with a clear status and **leaves
the one inert candidate branch unmerged**. Do not replace its token with a
personal access token or share a credential in chat to force a merge.

**Token-triggered PR rule:** A PR created by the automatic `GITHUB_TOKEN` does
not automatically trigger ordinary PR CI. Explicit
`workflow_dispatch` is essential; the workflow waits for a new dispatch run
bound to the branch, exact SHA, and dispatch timestamp. This tests the
authentication and actual CI path before any scheduled data writer is
migrated. A run status of `skipped`, `neutral` or `pending` is **not** proof.

**After successful canary:** Migrate the four existing direct-main writers
separately, ensuring each carries a precise path allowlist, one isolated
proposal branch, a current-base check and actual release-gate CI. Do not enable
the currently disabled `.github/retally-main-ruleset.json` until every
scheduled/direct writer has been migrated and a repeatable no-review canary
proves protected-main merge behavior under the active rule. The initial
unprotected canary by itself is insufficient.

No credentials, customer data, invoices, bank payments, public hosts,
billed services or OCI operations are authorized or exercised. RETALLY
customer production remains **HOLD**.
