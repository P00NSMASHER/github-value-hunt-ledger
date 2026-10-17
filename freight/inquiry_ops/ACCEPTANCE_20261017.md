# RETALLY inquiry response and retention — acceptance evidence (2026-10-17)

## Environment separation
- Source candidate: PR #467, branch `hardening/retally-lead-response-retention-20261017`.
- Original production D1: `retally-inquiries` — no schema writes during this QA.
- Disposable US D1 test database: `retally_inquiry_ops_qa_20261017`.
- No real clients, customer files, permissions, messages or financial actions were used.
- Public `FREIGHT_INQUIRY_ENABLED=0` and `FREIGHT_INQUIRY_MAILBOX_VERIFIED=0` remain off. Cloudflare Access operator credentials and production approval flags were not configured.

## Verified execution
- Original secured Resend inquiry + signed staff JWT, response-state, and aggregate safety: **65 Node tests passed**.
- Independent SQLite retention guard regressions: **19 Python tests passed**.
- Disposable actual Cloudflare D1 accepted additive 0001–0004 migration objects, including the final direct-SQL guard triggers.
- Exactly **14** real D1 state-changing/denied operations behaved as specified:
  synthetic 91-day-old inquiry inserted; unhandled purge blocked; reviewer acknowledgement recorded; closure without reply evidence blocked; fabricated one-shot VERIFIED insertion blocked; response REPORTED; closure still blocked; response VERIFIED; closure succeeded; legal hold blocked purge; hold released; purge approved by distinct synthetic actor; authorized purge emitted an audit receipt.
- Disposable result: **zero remaining inquiry records**, **one purge receipt**, **two response audit receipts**. These records and roles were fictional; no real customer data was read or modified.
- Source app CI must pass again on the exact final commit before production merge or migration.

## What this does and does not certify
This verifies SQL/SQLite/Cloudflare-D1 invariants, validation code, synthetic JWT verification and negative cases. It **does not** certify real human responses, actual MFA/IdP enrollment, true independent recipient or actor identity, Zoho sent-message review, external evidence provenance, browser-origin signed Access operations, applicable lawful retention periods, legal consultation, or customer service SLA staffing.

Only a properly scoped live system with independently authenticated staff may mark a real lead ACKNOWLEDGED, VERIFIED, WAIVED, CLOSED or deletion-approved. Until then, production write APIs must stay disabled and public direct intake must not be reopened.
