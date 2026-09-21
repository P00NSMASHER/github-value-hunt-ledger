# Cross-lane referral — Xero AP post-TTL positive reconciliation

Date: 2026-09-20
From: Hunt 09 — Data Moats
To: AP/finance lane, money-state lane, MASTER integrator

## Why this matters

Run 20 established Xero Accounting API mutations as `REPLAY_CACHED_BOUNDED`: the same Idempotency-Key is safe only inside Xero's documented six-minute cache window; after expiry the same key may execute as a new mutation.

Run 21 found a first-party-source-backed **positive reconciliation** path after that replay window:
- `XeroAPI/xero-command-line@ae346db7406b41c455d786c5f1a2b1ca6e62bd6c` accepts a caller `reference` and sends it on an `ACCPAYCREDIT` Credit Note create.
- `XeroAPI/Xero-OpenAPI@448060d7829cae23166a2e443be48c2f2422280f` contains an explicit ACCPAYCREDIT create/response example retaining `Reference`, despite a stale/over-narrow schema description that says `ACCRECCREDIT only`.
- Xero Credit Note webhooks, introduced 2026-03-04, deliver the provider-generated CreditNoteID plus type/status. Events arising while subscriptions are Retry/Disabled are retained for up to 31 days and replayed once healthy.

## Recommended provider classification

Refine Xero to:

**`REPLAY_CACHED_BOUNDED + POSITIVE_RECONCILABLE`**

Safe control path:

`reserve reverse capacity -> persist logical effect L -> derive compact high-entropy marker M -> put M in ACCPAYCREDIT Reference -> persist idempotency key K + replay expiry -> dispatch -> lost response -> replay same K only inside TTL -> after TTL block redispatch -> webhook yields CreditNoteID -> GET exact record -> require M + expected tenant/contact/type/amount/currency/line semantics -> APPLIED`.

## Critical boundary

This does **not** prove `NOT_APPLIED`:
- AP `Reference` is not documented as provider-unique.
- absence of a webhook is not absence of a credit note.
- webhook retention is finite and subscription health matters.
- no broad zero-result search may release reverse capacity.

UNKNOWN therefore remains reserved after replay expiry until positive evidence appears or a future bounded authoritative negative-proof contract is established.

## Exact unanswered question

**Can Xero expose a bounded, authoritative completeness signal for Credit Note observation—across webhook sequence/health plus exact API reads—strong enough for a post-expiry zero-match to become VERIFIED_EMPTY / NOT_APPLIED, or must every unresolved AP credit without positive evidence remain UNKNOWN/manual?**

## Durable detail

Full evidence and proposed EXP-002 fixtures: `hunters/16-run21-2026-09-20.md`.