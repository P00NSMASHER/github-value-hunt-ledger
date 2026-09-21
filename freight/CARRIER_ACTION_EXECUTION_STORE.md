# Carrier Action Execution Store

The Carrier Action Execution Store is the durable idempotency boundary immediately before and after an external carrier action.

It does not send anything itself.

## Why it exists

The in-memory execution proofs already make duplicate successful submissions detectable. A real sender also needs duplicate prevention across:

- process restarts;
- concurrent workers;
- retried jobs;
- crashes between preparation and receipt recording.

The SQLite store provides that boundary.

## Durable send slot

Before an external sender acts, it must reserve the execution key with `reserve_send_attempt(...)`.

The store atomically persists the proof-bound execution intent and an immutable attempt row, then acquires one transient send-slot row whose primary key is:

`buyer_id + business_unit + execution_key`.

Only one attempt can own that slot.

Exact replay of the same active attempt is idempotent. A different worker receives `IN_FLIGHT`.

## Fail-closed crash behavior

If a worker crashes or its external outcome is uncertain, the send slot remains occupied. The system does **not** automatically release it.

This intentionally prefers at-most-once external submission over automatic retry.

A slot is released only when a proof-bound terminal execution receipt is persisted:

- **FAILED** releases the slot and permits a new attempt ID;
- **SUBMITTED** or **DELIVERED** releases the transient slot but permanently blocks any later send attempt for the execution key.

The database also has a partial unique index allowing at most one successful submitted/delivered receipt per tenant-scoped execution key, even if application code is bypassed.

## Evidence tables

The following rows are append-only/immutable:

- execution intents;
- send attempts;
- execution receipts;
- asynchronous delivery receipts.

The operational send-slot table is transient and may be deleted only as part of a terminal receipt transaction.

SQL triggers enforce attempt/execution-key and receipt/attempt identity. Delivery rows require an existing submitted-but-not-already-delivered execution receipt.

## Tenant scope

Every row is scoped by buyer and business unit. Execution keys themselves are also buyer/business-unit-bound.

A store instantiated for another tenant cannot persist or read the first tenant's execution proof.

## States

The derived durable state is one of:

- `NOT_FOUND`
- `PREPARED`
- `IN_FLIGHT`
- `FAILED_ONLY`
- `SUBMITTED`
- `DELIVERED`

A deterministic snapshot hash covers evidence rows and the current operational send slot.

## Boundary

The store proves durable reservation and persistence state. It does not itself prove:

- that a sender actually performed a network call;
- delivery unless delivery evidence is recorded;
- settlement;
- credit issuance;
- cash recovery;
- realized savings.
