# RETALLY Mission 15 | Real Cloudflare D1 retention acceptance

**Reviewed October 8, 2026. Review-only, synthetic data, no production deployment.**

## Source and isolation

- Source branch: `mission14/inquiry-retention-lifecycle-20261008`, stacked PR #321 on PR #307.
- Migration under test: `freight/site/migrations/0002_inquiry_case_retention.sql`, Git blob `55c71b5ddecbad22d8cf1ebd3d822f36bda5d402` at the start of the test.
- Isolated, newly created US-jurisdiction Cloudflare D1: `retally-m15-disposable-qa-20261008` (UUID `7da9a8bf-e2b1-4d38-bf7e-d1d5b6c5cefd`).
- Existing production database: `retally-inquiries` (UUID `8a2628d8-9649-49c5-84a5-a2cde37283e2`). Different resource IDs. No production SQL changes.
- All rows were synthetic; names and email fields used QA placeholders only. No customer data, claim, billing document, email send, credential rotation, or website release.
- Executed via the actual Cloudflare D1 query API, not SQLite emulation.

## Original migration compatibility defect and repair

The first attempt to apply the entire previous migration through Cloudflare D1's query API returned `7500 incomplete input: SQLITE_ERROR`. The first five DDL operations succeeded when submitted individually, but the original `inquiry_require_review_before_delete` trigger with two SQL statements and an internal CASE expression failed. This was a real migration-delivery blocker.

Replaced the trigger in PR #321 with a **single-statement** `INSERT INTO inquiry_purge_audit ... SELECT COALESCE((SELECT approved_at ...), RAISE(ABORT, ...))`. The one statement makes the eligible purge receipt and deletion guard inseparable: if the qualified approval is absent, the trigger aborts; otherwise, an audit receipt is inserted in the same database transaction.

Cloudflare D1 accepted the new trigger. It also accepted the entire updated six-statement migration file as one API request, including an idempotent reapplication. To ensure the exact checked-in migration was actually installed rather than silently ignored due to IF NOT EXISTS, the test removed **only the QA guard trigger**, reapplied the entire file, confirmed all three registered triggers and re-executed the old-pending deletion refusal.

## Real Cloudflare D1 test matrix

- Nine kinds of forbidden deletion were tested with aged synthetic records: `pending`, `provider_accepted`, `delivery_verified` without case disposition; acknowledged-but-not-closed; closed without purge approval; legal hold; active retention deadline; younger than 90 days; and future-dated approval.
- Every forbidden deletion either was refused directly by the trigger or was rejected at schema admission, and the corresponding record remained. No unauthorized audit receipt was created.
- One 91-day-old closed record, approved by a **different** operator with no hold and an elapsed retention deadline, was deleted successfully and generated one audit receipt.
- Attempts to `UPDATE` or `DELETE` the audit receipt were rejected. The receipt remained.
- The initial synthetic future-approval case had a malformed SQL expression and failed during fixture creation. The fixture was corrected and rerun on real D1; the future-dated approval was then admitted to the synthetic disposition table but deletion was **correctly blocked**. The final corrected acceptance set therefore satisfies all intended cases. Do not disguise the original harness error.
- A final read-only D1 census verified three installed triggers, one authorized audit receipt and preserved aged pending records.
- The production D1 data was not read for personal details or changed.

**Evidence:** Tool-based Cloudflare D1 read/query execution on the isolated QA database within this Mission 15 conversation. These are observed D1 responses, not a claim that production migration or privileged access control was certified.

## Remaining critical gaps

1. **D1 API acceptance does not certify deployment tooling.** Confirm the exact schema is applied through the intended reviewed production migration mechanism, with staging rollback, prior version compatibility and audited release.
2. **Database actor authority is not enforced by SQL field labels alone.** A privileged writer could falsely assert `case_state`, `operator_id`, `purge_approved_by` or clear a hold. Separate restricted identities, recorded source evidence and real two-person authority must be implemented and independently tested.
3. **Legal deletion exceptions:** The normal 90-day minimum gate is not by itself a lawful response workflow for an authorized earlier data-erasure obligation. Obtain jurisdiction-specific counsel/privacy approval.
4. **Human follow-up is not provider delivery.** Neither a D1 receipt nor Cloudflare `delivered`/`queued` establishes actual Zoho inbox arrival and operator acknowledgment.
5. **Live online intake remains disabled.** Keep both production release flags at 0 until real company email inbound and sender permissions, controlled full-path confirmation, device/browser QA and documented staffing pass.
6. **Audit retention:** The receipt contains a pseudonymous inquiry reference and needs a legal retention/data-minimization decision; removing personal data must not silently invalidate audit controls.

## Release verdict

- D1 migration compatibility after repair: **PASS on isolated disposable D1**.
- Retention guard under the tested synthetic cases: **PASS on isolated disposable D1**.
- Production configuration, operator authorization and actual mailbox delivery: **NOT VERIFIED / NO-GO**.
- Do not merge stacked PR #321 ahead of PR #307, or treat D1 QA as permission to activate external inquiries.
