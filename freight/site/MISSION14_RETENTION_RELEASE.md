# RETALLY Mission 14: Inquiry retention repair and human case lifecycle

**Status: draft engineering candidate only. No live D1 migration, inquiry feature activation, data deletion, email send or customer operation authorized.**

## Exact source of repair

This branch is stacked on **PR #307** (original base head `3c1964bc617f90e0349a6766b241e6368af8b8ba`), not independently rebased onto main. That preserves PR #307's validated provider-acknowledgment logic and existing website work. Avoid merging this branch before its base is accepted. Coordinate with PR #313's read-only inquiry-aging monitor.

## Independently reproduced defect

The original public inquiry handler ran `DELETE FROM inquiries WHERE accepted_at < ?` during a subsequent form submission. A synthetic case already 91 days old with state `pending` was silently erased under the old schema and a simplified direct-delete model. Neither `provider_accepted` nor `delivery_verified` proves a human handled the inquiry.

## Implemented correction

1. **Actual request handler:** stops deleting from `inquiries` altogether. Continues limited cleanup of expired hashed rate-limit buckets. No public ability to delete or mark a lead handled is introduced.
2. **Additive migration `0002_inquiry_case_retention.sql`:** proposes `inquiry_case_dispositions` and an append-only retention audit. Existing rows are not modified. An inquiry cannot be deleted at the database layer without CLOSED status, a documented acknowledgment, a separate named purge approver, explicit approved timing, no legal hold, and passing the 90-day policy boundary. A successful deletion writes a pseudonymous receipt atomically. The original `inquiries` table schema remains unchanged.
3. **Regression:** existing inquiry tests plus isolated, real SQLite negative-case tests for old pending and provider-only entries, missing closure, holds, early purges, same-person approval, future approval, and actual approved deletion with a durable receipt.
4. **Existing CI reused:** adds the SQLite regressions to the existing `RETALLY Inquiry CI`; no new cron, dashboard, CRM or deployment system.

**Technical honesty:** SQLite unit tests exercise the SQL transaction semantics, not deployed Cloudflare D1 migration acceptance. A case disposition row is still an operator assertion until its identity, underlying evidence, access permissions and independent acceptance are verified. An audit receipt records approval metadata, not actual legally valid authorization.

## Operator control and privacy release gates

- **P0:** Business owner must name one inquiry case reviewer and an independent retention approver with actual authorized credentials. Prevent unreviewed operators from directly writing dispositions.
- **P0:** Define independently reviewable evidence references for customer contact, reply/closure, legal hold, and erasure approvals. A provider notification status must not count as human completion.
- **P0:** Legal/privacy reviewer must approve maximum/minimum retention, lawful-basis/erasure exception handling, processor terms and data inventory. The current SQL guard enforces a minimum 90-day retention for normal purges and is **not** yet a complete response mechanism for legally required earlier erasure.
- **P0:** Prove safe migration and rollback in a truly isolated production-representative Cloudflare D1 clone; verify indexes, constraints, trigger safety, authorization, and normal old-schema data behavior. Do not apply migration to live D1 based only on GitHub CI.
- **P0:** Provide an access-controlled case-disposition procedure with actor-authenticated write path, two-person approval and durable audit evidence. PR #14 does not implement an operator console or permit blind manual edits in the production console.
- **P0:** Match two permitted non-sensitive end-to-end inquiry submissions, D1 reference IDs, actual Zoho inbox receipt and operator acknowledgments, without real customer freight data.
- **P1:** Integrate PR #313's independent read-only monitor with real disposition flags; avoid false "zero lost leads" because a notification field is "delivered".
- **P1:** Test iOS Safari/keyboard/Turnstile fallback and live response accuracy.

The safe approval flow is:

1. Customer request is durably received under a unique reference, with no claim of inbox delivery.
2. Approved operator investigates notification, confirms Zoho receipt where applicable and acts on inquiry.
3. Operator records evidence-supported acknowledgment and final case resolution in a restricted system.
4. Any applicable hold blocks purge.
5. Independent approved operator authorizes an eligible purge.
6. Retention deadline and legal-review requirements are satisfied.
7. Controlled administrative deletion occurs; the trigger enforces case gates and writes only a pseudonymous receipt.

**No automated purge has been installed; this is intentional until an actual, approved operator process is established.** This does not excuse leaving personal data indefinitely. Aging reports must flag overdue records, require disposition work and a counsel-reviewed alternative for exceptional erasure obligations.

## Regression commands

```sh
node --experimental-default-type=module --test freight/site/test_inquiry.mjs
python freight/site/test_inquiry_retention.py
```

The current direct online inquiry production flags remain disabled. Preserve the public email-draft fallback. Do not merge a green test report into a claim that mailbox delivery, actual customer service, or production retention compliance is certified.

**Acceptance:** Code-level premature deletion repaired and isolation-tested; **production activation remains NO-GO** until all P0 controls are independently verified.
