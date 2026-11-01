# RETALLY live-audit incident alert policy

**State:** Candidate, not active until this change is independently reviewed, merged, and an actual GitHub `workflow_run` completes on `main`. **Dependency:** Merge the bounded HTTP-504 retry in [PR #505](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/505) first. Without that correction, a single transient public HTTP 504 can still make the existing audit fail; the alert workflow does not independently re-run the audit.

## Trigger and meaning

The existing daily and post-release `RETALLY Live Publication Audit` performs public **GET-only** checks of the actual HTTPS origin, sitemap, first-party links, security headers, approved media and inquiry GET status. This new workflow consumes the completed first-party GitHub Actions result on `main`:

- **`failure` or `timed_out`:** open one labeled GitHub Issue, or append the new run URL to the existing incident. Classify it as **live publication audit failure requiring investigation**, never as proven user-facing downtime.
- **`success`:** comment with the run URL and close the matching issue, only when the event is the latest authoritative `main` run. This is a verified passing audit at that point, not a guarantee of continuous availability.
- **Cancelled, skipped, PR-originated, wrong-repo, stale or incomplete events:** no incident mutation. Missing authoritative run metadata fails the alert job rather than inventing a passing audit.
- **Raw Cloudflare `EdgeResponseStatus=504` counts:** no notification. Some are internal `earlyHintsCache` or `edgeWorkerCacheAPI` cache misses and cannot be equated with failed user requests.

This is a **GitHub Issue workflow**, not an external email, paging subscription, or paid observability service. Each confirmed failure issue/comment mentions `@P00NSMASHER` to surface it to the owner through GitHub notifications; actual device/email delivery still depends on the owner's GitHub notification settings. GitHub-hosted Actions minutes remain subject to the repository's existing plan/usage; do not claim unlimited free runner capacity.

## Authorization and security

Uses only the automatically provisioned `GITHUB_TOKEN`, scoped to `issues:write`, `actions:read` and `contents:read` for the incident job. Checkout is from trusted `main`, never from untrusted `workflow_run` head content or artifacts. No external service or paid API is introduced. The handler reads only the workflow event and GitHub's latest-run/Issue metadata. No customer data, inbound documents, user-submitted issue text, external PR data or Cloudflare credentials are consumed.

## Operational response

On incident creation, open the linked Actions run and inspect the exact failed step. Determine whether the trigger was an HTTP failure (persistent 504, 404, SSL, transport), an integrity failure (asset hashes, canonical URL, security headers), an upstream GitHub runner/setup failure, or a stale deployment. Verify independent public responses before classifying end-user impact. Do not disable inquiry safeguards, automatically roll back a good release, or modify WAF/DNS merely because an HTTP status was sampled.

The GitHub issue itself is a durable alert ledger. It does not establish independent human security approval or customer incident notification.
