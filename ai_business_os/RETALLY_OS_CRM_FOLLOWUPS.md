# RETALLY OS native CRM follow-ups

This is a private Cloudflare-native task workflow linked to the authoritative RETALLY D1 inquiry receipts. It **does not** deploy upstream GopherCRM, send mail, schedule or publish posts, issue invoices, or attest to recovered customer money. Keep the existing intake and Cloudflare Access owner-only gate unchanged.

## Purpose and behavior

- New private **Follow-ups** tab in `freight/site/retally_os_ui.mjs` shows up to 200 owner tasks, linked by the immutable accepted `RA-...` inquiry reference.
- The owner may create, assign, reschedule and resolve tasks without contacting a customer. Each task has title, owner, optional due date, status, private note, numeric version, and an event trail.
- Completing or cancelling a task requires a written note; it **does not** change financial or customer-engagement outcome fields.
- Save operations use an opaque client-generated UUID and optimistic version matching; conflicting idempotent retries or stale writes return 409. A task cannot be reassigned to another inquiry reference.
- The dashboard's open/overdue counts exclude records tagged synthetic in `inquiry_qa_registry`. They only describe the returned 200 tasks; they are not enterprise-wide metrics when more than 200 exist. The latest-inquiries window remains 100.
- No task permits outbound communication, publishing, contracting, claims, money movement, or customer identity creation.

## Deployment: schema first, feature second

1. From the live Cloudflare account, **read-only** inspect `retally-inquiries` D1 schema and existing inquiry, case and QA counts. Preserve binding `INQUIRY_DB` on `retally-web`.
2. Run a local SQLite rehearsal with both `20261108_retally_os_phase2.sql` and `20261108_retally_os_crm_followups.sql` and enable foreign-key enforcement. Run `node --experimental-default-type=module --experimental-sqlite --test freight/site/test_retally_os.mjs`; require all tests to pass.
3. Stage only `freight/site/migrations/20261108_retally_os_crm_followups.sql` against D1. It must create two tables, three indexes and two triggers, with **zero changes to any inquiry row**. Confirm constraints and the expected new tables before enabling the new API. For a new environment, back up first and inspect namespace collisions. Production D1 migrations are forward-compatible and retained on code rollback.
4. Submit source changes by PR, require exact-head release and intake CI. Do not merge if tests fail or the production D1 schema check fails. Existing public pages must continue to build unchanged.
5. Verify Cloudflare's canonical production deployment SHA and exact owner Access policy, then independently test that anonymous production and Pages preview requests cannot retrieve private tasks, case notes, customer contacts or draft contents.
6. An authenticated owner must test a case/task roundtrip from the actual private URL on a mobile device and verify 409 for a stale version. This remains **unverified** unless performed with a genuine owner-authorized session; synthetic browser fixtures do not count.

## Retention and recovery

New `retally_os_tasks.reference` is a foreign key to authoritative `inquiries.reference` with `ON DELETE CASCADE`. The task-event table cascades from the task. This ensures tasks and their event trails follow a verified deletion of their original intake records when foreign keys are enabled. The existing `retally_os_cases` table is not altered here; its independent retention reconciliation remains a separate concern.

Do not automatically delete task history, clear records, or change existing intake retention. The SQL migration contains only new objects and has no data modification statements. As part of a rollback, redeploy the previous Pages Function/UI but preserve the task tables and their data pending explicit retention review.

## Verification limits

Local tests use fixture inquiries and a simulated owner identity, plus browser DOM workflow checks at 393px and 1365px. They do not prove a live customer or an authenticated iPhone login. A green Cloudflare deployment alone is also insufficient: verify the exact production SHA, Access policy and anonymous denial after release. Full GopherCRM/Postmill runtime rollout remains separate pending patched dependencies, persistent secure hosting and owner authorization.
