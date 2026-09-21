# Freight Recovery — Controlled Pilot Environment Policy Snapshot

Effective date: 2026-09-21
Environment: single-tenant, manual-review Google Drive workspace
Status: VERIFIED FOR CONTROLLED MANUAL PILOT — EMPTY UNTIL BUYER AUTHORIZATION

- One pilot at a time.
- Owner-only until a specific buyer engagement is approved.
- No public or link-wide sharing.
- Customer source files treated as immutable evidence; SHA-256 recorded before review.
- Derived analysis stored separately; no writeback to buyer source systems.
- Manual/no-parser route only. No production PDF/XML/EDI/CSV parser runtime or customer-data API.
- Default retention: 30 days after final report delivery unless a signed engagement requires less.
- Deletion must be provider-confirmed before represented as complete.
- No confidential buyer data may be uploaded to or processed by the current Netlify freightleak-audit shell.
- No carrier contact, disputes, payments, account changes, or money movement without separate buyer approval.
- Material control changes require reverification.
