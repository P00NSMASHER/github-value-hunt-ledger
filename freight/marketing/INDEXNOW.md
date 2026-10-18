# RETALLY: zero-spend IndexNow discovery notification

Scope: **only new or edited first-party HTML pages on trusted `main` releases**. No general crawling, mass index requests, search-ranking promises, Google indexing claims, DMs, payments, customer records, login or customer-facing forms.

IndexNow is a public protocol used by Bing and other participating engines. Google does not participate. An HTTP 200/202 from the protocol acknowledges a URL notification; it does **not** establish indexing, crawling, visibility, conversions or customer inquiries.

## Workflow

1. The existing `RETALLY Live Publication Audit` runs read-only after a site-source push to `main`.
2. On a **successful push-triggered** audit only, `.github/workflows/retally-indexnow.yml` checks out that precise verified commit.
3. `indexnow_notify.py` diffs that commit against its first parent and selects only changed `freight/site/*.html` pages with canonical production destinations. Exclude `404.html`, synthetic report and verification pages.
4. GET the public ownership file `https://www.retallyrecovery.com/1a17119c023bc3e3c0abe34188f4eeb4.txt`, the deployed sitemap, and the exact HTML of each changed URL. The key content and each published canonical must agree.
5. Verify readiness in a bounded loop. Submit one bulk notification to `https://api.indexnow.org/indexnow` only after all pages are live. Do not retry an ambiguous POST response; server logs record an acknowledgement, not a ranking outcome.

**Public ownership key:** `1a17119c023bc3e3c0abe34188f4eeb4` (not a private secret; the protocol requires the key file to be publicly retrievable).

No new vendors, subscriptions, saved browser identifiers or third-party analytics code are introduced. The existing daily live audit and all RETALLY content schedules remain unmodified.

## Evidence limits

IndexNow **HTTP 200** reports accepted submission, but does not establish crawling, indexing, visitors, leads or revenue. **HTTP 202** reports only that the URL notification was received and the public ownership-key validation remains pending; it is not yet a verified submission. The job records `key_validation_pending` rather than claiming completion. If a release changes no indexable HTML, the workflow exits as `skipped` without a POST. Do not repeatedly submit the same unchanged URLs.

Official docs: https://www.indexnow.org/documentation and https://www2.bing.com/indexnow/getstarted .
