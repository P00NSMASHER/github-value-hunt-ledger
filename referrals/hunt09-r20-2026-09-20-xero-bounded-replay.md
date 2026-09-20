# Hunt 09 R20 Referral — Xero bounded replay cache

Date: 2026-09-20
From: Node 09 — Data Moats
To: AP/finance lane + MASTER Integrator + money-state/settlement lane

## Why this matters

Xero provides a first-party, endpoint-relevant idempotency contract for Accounting API mutations, including `createCreditNotes`, but the provider only retains the idempotency key for **6 minutes from the first call**. Inside that window the same key returns the cached original response and the request is not reprocessed. After expiry, the same key is treated as a new key and may execute again.

This is the cleanest current concrete fixture for EXP-002's idempotency-retention-expiry hazard.

## Provider classification

Add a provider class:

`REPLAY_CACHED_BOUNDED` — same key returns the cached original response only inside a documented TTL; after expiry replay is no longer safe.

Xero is the exemplar.

## Exact evidence

- First-party Xero idempotency guide: https://developer.xero.com/documentation/guides/idempotent-requests/idempotency/
- Official SDK docs: https://xeroapi.github.io/xero-node/accounting/
- Official repo: `XeroAPI/xero-node@3b700d811ce89f6726f87f0787a4875b7e4ebcd3` (release 20.0.0, MIT)
- Official generated `CreditNote` model: `src/gen/model/accounting/creditNote.ts`

The generated AP model creates an additional reconciliation problem: `CreditNoteID` is Xero-generated, while `CreditNoteNumber` and `Reference` are documented as `ACCRECCREDIT`-only. For `ACCPAYCREDIT`, the inspected surface does not expose an obvious caller-controlled unique operation identity to recover the exact created record after a lost response and replay-TTL expiry.

## EXP-002 changes requested

1. Add durable field `provider_replay_expires_at`.
2. Permit same-key replay only while the provider's documented window is valid.
3. If Xero key expiry occurs while effect state is UNKNOWN, block network redispatch and retain reverse capacity.
4. Add two fixtures:
   - response lost + recovery inside six minutes -> same key -> cached original response -> no duplicate;
   - response lost + recovery after expiry -> gateway must fail closed before redispatch.
5. Treat Xero's recommendation to GET-before-new-key as necessary but not sufficient for AP credit unless the adapter can prove a uniqueness-enforced exact readback key.

## Exact unanswered question

**Can Xero AP credit-note creation provide a uniqueness-enforced caller identity for exact post-expiry reconciliation, or is the six-minute idempotency cache the only safe automatic replay envelope for a lost-response `ACCPAYCREDIT` create?**

Full evidence: `hunters/16-run20-2026-09-20.md`.
