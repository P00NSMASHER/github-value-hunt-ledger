# RETALLY OS Phase 2 — private Cloudflare owner desk

Status (2026-11-08): the source route is deployed on production retally-web and all retally_os_* D1 objects were independently observed in the live database. Authenticated owner-browser acceptance is not independently verified in this session; unauthenticated negative testing remains required. **The pilot's GopherCRM, Postmill and Prime Agent are not live production services.** Do not describe this as a deployed GopherCRM/Postmill integration, verified customer, paid revenue, social publication or customer deliverable.

## Production URL and protection
- Owner URL: https://retallyrecovery.com/api/internal/retally-os (never use a Pages preview URL).
- Cloudflare Access: self-hosted application "RETALLY OS — private owner dashboard" for exactly retallyrecovery.com/api/internal/retally-os; identity rule allows only the owner email, with 1-hour sessions.
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
