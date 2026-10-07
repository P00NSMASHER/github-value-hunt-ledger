# RecoveryOS Product Hardening — 2026-10-07

Status: **DEPLOYED / INTERNAL ENGINEERING EVIDENCE ONLY**

Production application: https://freight-recoveryos.floot.app

## Product changes deployed

### Governed source-document intake

RecoveryOS now accepts private PDF, PNG, JPEG and WebP freight evidence through
a server-created immutable upload intent. The upload intent binds tenant,
document ID, original filename, MIME type, expected byte size, storage path and
expiry before file transfer.

The browser uploads directly to private object storage. The backend then reads
the stored object, verifies the exact stored byte count and computes SHA-256
from the stored bytes before the evidence document is admitted.

Tenant-scoped SHA-256 deduplication prevents the same source bytes from quietly
becoming multiple independent evidence objects.

### Append-only document evidence plane

Three separate append-only layers are retained:

1. source evidence document;
2. machine extraction claim;
3. human review/correction/rejection.

Database mutation guards prevent update/delete of those evidence rows and the
existing tenant audit chain records each insert. A corrected extraction creates
a separate review artifact instead of rewriting the model output.

### Document extraction boundary

The production extraction path uses native PDF/image input and returns only
observable document facts. Unknown values remain null. It records:

- document kind;
- invoice/shipment/carrier identifiers when visible;
- money as integer cents;
- line-item facts;
- per-field confidence;
- overall confidence;
- source page/region locators;
- extraction warnings.

Deterministic post-extraction checks currently include unknown document type,
missing invoice total, missing source locators, low extraction confidence,
low-confidence line items and line-item/total mismatch.

No extraction, confidence score or AI response may itself create a freight
finding, establish contract authority, authorize carrier action, or become
reported recovered value.

### Failure recovery

A source document that has already been admitted remains retryable after the
short upload-intent window expires. This lets an operator retry extraction after
a transient model/credit/provider failure without asking the customer to upload
the same source evidence again.

### Identity

RecoveryOS now offers:

- password sessions;
- Google federated sign-in;
- Microsoft federated sign-in.

This is not represented as SAML enterprise SSO, MFA, SCIM or buyer-managed
identity federation. Those remain product gaps.

### Reviewer integrity

The human-review path now fails closed when a deterministic extraction issue is
marked BLOCK. The backend enforces that rule even if a client bypasses the UI.

Reviewers can open the original retained document through a tenant-scoped,
short-lived signed URL before approving or correcting the extraction.

Re-extraction creates or selects an immutable extraction claim. Reviews are
bound to the exact extraction ID rather than being applied generically to the
document, preventing an older approval/rejection from silently governing a
newer extraction attempt.

### Security & API operations

Owners now have an in-product Security & API workspace showing:

- audit-chain event count, invalid hashes and broken links;
- implemented control status;
- session ceiling;
- active/revoked scoped API keys;
- one-time plaintext display for newly created API keys;
- separate ingest and payment-event scopes;
- one-way audited key revocation.

The UI explicitly distinguishes implemented controls from external assurance.

### Mobile operability

The control room now retains workspace navigation on phone-sized layouts rather
than hiding the desktop sidebar and its navigation together.

## Verification

The post-change Floot typecheck passed.

The complete current helper test suite passed with **5 files passing / 0
failing**, including the new RecoveryOS evidence invariants and the provisioned
OAuth-provider tests.

The production publish completed successfully on 2026-10-07.

## What this does not prove

This deployment does **not** prove:

- extraction accuracy on a customer's real document distribution;
- real-customer false-positive/false-negative rates;
- named ERP/TMS/accounting connector maturity;
- MFA/SAML/SCIM enterprise identity;
- direct bank/payment-rail execution;
- SOC 2, ISO 27001 or independent penetration-test assurance;
- realized customer recovery or willingness to pay.

Those remain evidence/product gaps rather than being backfilled with synthetic
claims.
