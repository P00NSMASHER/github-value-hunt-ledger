# RETALLY OS Phase 2 — private Cloudflare owner desk

Status (2026-11-08): the source route is deployed on production retally-web and all retally_os_* D1 objects were independently observed in the live database. The exact Cloudflare Access application currently reports a 30-day (`720h`) session duration, and protected-main source accepts signed owner JWT lifetimes up to that same bound. Authenticated owner-browser acceptance and preview-host denial are not independently verified in this session. On 2026-11-08, independent anonymous browser checks of the canonical route and `?view=data` both redirected to Cloudflare Access login without rendering dashboard HTML or customer JSON. **The pilot's GopherCRM, Postmill and Prime Agent are not live production services.** Do not describe this as a deployed GopherCRM/Postmill integration, verified customer, paid revenue, social publication or customer deliverable.

Source/deployment receipt (2026-11-08): [PR #1100](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/1100) merged a navigation-only link from the private social workspace to the existing Metricool planner at main commit `3eadc813867bda240ae9804821238f9eef51e5ad`, and the exact-commit [Cloudflare Pages: retally-web check](https://github.com/P00NSMASHER/github-value-hunt-ledger/runs/128879195445) completed successfully. This proves source inclusion and a successful provider deployment check only; authenticated owner-browser visibility, provider-side planner access or scheduled-post state, and any Metricool API integration remain unverified.

Owner-session receipt (2026-11-08): [PR #1105](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/1105) merged the bounded 30-day JWT lifetime at protected-main commit `7f4d47565a140f4c23ff6184720a29abde384231`; its exact-head release gate passed and the [Cloudflare Pages deployment check](https://github.com/P00NSMASHER/github-value-hunt-ledger/runs/128919061133) reports that exact commit deployed successfully. A separate read-only Cloudflare Access application readback returned the matching app name, canonical domain, pinned audience, and `session_duration: 720h`. This establishes current source, deployment, and provider configuration state only. It does not prove a 30-day authenticated iPhone session has completed; the provider mutation actor is not established by the readback, and the GitHub merge actor was `P00NSMASHER`, not this integrator.

## Production URL and protection
- Owner URL: https://retallyrecovery.com/api/internal/retally-os (never use a Pages preview URL).
- Cloudflare Access: self-hosted application "RETALLY OS — private owner dashboard" for exactly retallyrecovery.com/api/internal/retally-os; identity rule allows only the owner email, with a read-back 30-day (`720h`) application session.
- The Pages Function independently verifies the signed Cloudflare Access JWT, exact team issuer, application audience, expiry, and the SHA-256 hash of the owner email. It does not trust spoofed email headers.
- The route refuses all other hostnames, including Pages preview domains, and does not render customer information in its initial HTML. Private JSON data is fetched only after signed authentication. No unauthenticated public API exists.
- Logs, source control and static deployment artifacts must never contain customer records, Access JWTs or any secrets.

## Data boundaries
- The existing retally-web Pages project uses the production D1 binding INQUIRY_DB (database retally-inquiries).
- The authoritative `inquiries` and `inquiry_qa_registry` tables are READ ONLY for this desk. Existing intake, Turnstile, idempotency, notification, retention, customer-consent and case governance flows are untouched.
- Migration `freight/site/migrations/20261108_retally_os_phase2.sql` creates ONLY private case-task, case-event, editorial-draft and draft-event tables and indexes/triggers. Inspect exact DDL before applying. No source rows are imported or altered.
- Unauthenticated access must be blocked by Cloudflare Access and separately by the Function. Only the owner can write private case follow-ups and internal draft/review state.
- No external mail, publish, scheduling, customer outreach, contract acceptance, cash receipt, invoice issuance or payment endpoint is present.
- Inquiries tagged by `inquiry_qa_registry` remain labeled synthetic and excluded from the dashboard's non-test counts. All displayed source records are limited to the latest 100. Missing cash evidence displays **unknown**, not zero real earnings.

## Preflight and migration
1. Check Cloudflare Pages retally-web production source, its binding name INQUIRY_DB and existing intake availability; do not remove or switch the binding.
2. Verify the Access application path, exact owner allow rule, and JWT audience. Confirm the selected team issuer matches the pinned `retally_os_auth.mjs` issuer.
3. From a separate staging D1, apply the migration and run `node --experimental-default-type=module --experimental-sqlite --test freight/site/test_retally_os.mjs`. Confirm the suite passes before applying production DDL.
4. The migration was already applied to production on 2026-11-08. For any new environment or rerun, first read-only query `sqlite_master` to reject name collisions and verify no `retally_os_*` table exists unexpectedly. Apply the migration to a new environment only after source backups and an explicit schema check. Live production uses record_tag in the case-event schema. Requery `sqlite_master` to confirm all expected objects. No customer rows need to be copied.
5. Deploy through a protected GitHub PR with exact-head CI, then verify the resolved production deployment commit.

## Acceptance
- Without Access credentials, GET /api/internal/retally-os and GET ?view=data must not return HTML or JSON customer records; an Access redirect or denied response is expected.
- A Pages preview hostname must never reveal data even if its route is loaded directly.
- An authenticated owner must be able to open the dashboard on an iPhone, see existing inquiries, and distinguish QA-tagged records. A new real inquiry should appear on refresh with its original reference once independently submitted through existing approved intake; **do not create a fake real inquiry to pass this test**.
- A private case note and due date may be added to an existing authorized reference without modifying that inquiry. Check concurrent version conflict returns HTTP 409. Verify event log and persistence after fresh login/restart.
- A social draft can be saved and marked reviewed, but no social channel is connected and no post is published. Editing a reviewed draft resets its review flag.
- Financial collections and verified paying customers remain unknown until independent evidence exists.
- Audit D1 `rows_read` and `rows_written`; respect account daily quotas. No batch scans or recurring polling outside the owner's explicit refresh.

## Rollback
- If a deployment fails, roll back ONLY the Pages release. Keep production D1 bindings, live intake and original inquiry rows unchanged.
- Access app can remain enabled to deny access to the route. Do not remove historical private case notes without separate approval and retention review.
- Disable the new UI by reverting the single Function in a protected PR. Do not delete `retally_os_*` tables as part of automatic rollback.

## Upstream exclusions
- GopherCRM and Postmill passed isolated synthetic pilots but have outstanding upstream dependency advisories, require durable private hosting and credentials, and lack production authorization. Do not expose either service to the internet before a separate patch/retest and operator-only Access gate.
- Prime Agent's completed local CPU experiment does not grant it production credentials or autonomous mutation rights.
- This limited owner workbench supplies an immediate zero-new-host-cost bridge to real D1 inquiries, case tasks and editorial drafts. It is **not** full production GopherCRM or Postmill.

## Canonical hostname redirect repair (2026-11-08)

The zone originally redirected **all** apex-host requests to www, including the exact protected RETALLY OS path. That returned an unrelated 301 instead of the protected dashboard and made the existing owner-only route unusable. A dry-run followed by an applied Cloudflare Rulesets PATCH modified ONLY the existing redirect expression to:

```text
http.host eq "retallyrecovery.com" and http.request.uri.path ne "/api/internal/retally-os"
```

The original rule remains enabled for all other apex paths. Its 301 destination (`concat("https://www.retallyrecovery.com", http.request.uri.path)`) and query-string preservation are unchanged. No www-based owner dashboard was activated; access remains restricted to the Access application on the apex path. The original expression for rollback is `http.host eq "retallyrecovery.com"`. Rolling back this exception would break the owner dashboard, so test Access denial and owner sign-in first.

The new read-only CI smoke check `freight/site/verify_retally_os_access.py` must reject anonymous production data access and any preview-host exposure. It deliberately makes GET requests only and does not submit a login or access customer records.

## Cloudflare Access passkey callback route repair (2026-11-09)

The owner reported **Invalid nonce** immediately after Face ID passkey authentication. The first-party Cloudflare Access audit recorded an allowed passkey login on 2026-11-09 at 17:05:41 UTC, so successful identity verification did not establish a completed browser callback.

Cloudflare's request simulator proved that the previous apex-to-www rule (version 2) returned HTTP 301 for both `/cdn-cgi/access/callback` and `/cdn-cgi/access/login`. The rule had exempted only the dashboard path, not the Access callback paths, and it preserved query strings while moving the host to `www`. This hostname change can invalidate an in-flight Access nonce. **It was an actual routing defect.**

A preview-validated, narrowly scoped Cloudflare Rulesets PATCH changed that existing Single Redirect rule to version 3. The full current expression is:

```text
http.host eq "retallyrecovery.com" and http.request.uri.path ne "/api/internal/retally-os" and not starts_with(http.request.uri.path, "/cdn-cgi/access/")
```

The rule is still enabled for normal apex-host pages and still issues a 301 to `https://www.retallyrecovery.com` while preserving query strings. The owner dashboard path and Cloudflare-managed `/cdn-cgi/access/*` paths keep their original hostname. No new unauthenticated application route, identity-provider change, token bypass, or D1 mutation was introduced.

**Independent post-change Cloudflare Trace results:**

- Apex `/` and `/contact` → HTTP 301 (canonical www redirect retained).
- `/api/internal/retally-os` and its `?view=data` query → HTTP 302 Access login; no www redirect.
- `/cdn-cgi/access/callback?state=synthetic` → HTTP 400 for the deliberately invalid callback; **no www redirect**.
- `/cdn-cgi/access/login` → HTTP 404 for a bare probe, `/cdn-cgi/access/certs` and `/cdn-cgi/access/logout` → HTTP 200; none redirected to www.
- Unrelated `/cdn-cgi/accessory` still redirects to www, confirming the exception is prefix-specific rather than all of `/cdn-cgi`.

The live deployment of RETALLY OS, its Cloudflare Access passkey-only identity provider, 720-hour application session, and owner-email-only Allow policy were read back unchanged. This establishes corrected routing and intact protection, **not** a completed authenticated Face ID session on the owner's iPhone.

The bounded anonymous CI check `python -m freight.site.verify_retally_os_access` now checks that Cloudflare callback and certificate paths cannot be redirected to `www`. The deterministic unit tests in `freight/site/test_verify_retally_os_access.py` reject the old behavior without initiating a real login. Do not replay stale callback URLs; begin a new login from the application URL in the same persistent Safari context.

Rollback of just this callback exemption would recreate the known authentication defect. If routing needs further adjustment, preserve both the dashboard path and the Cloudflare-managed Access callback prefix.

