# Settlement Evidence CSV Adapters

Freight Recovery now has strict normalized input boundaries for external settlement evidence.

## Settlement/remittance events

The settlement-event CSV accepts exactly:

`event_id, reference, payer_id, payee_id, currency, amount_cents, booked_at, source_kind`

Typical records include carrier credit memos, refunds, or remittance events.

## Counter-events

The counter-event CSV accepts exactly:

`counter_id, original_event_id, currency, amount_cents, observed_at, source_kind`

Typical records include bank returns, reversed credits, or other later evidence that can reduce a previously observed settlement.

## Controls

Both adapters:

- pass through the existing fail-closed CSV input guard;
- receive buyer/business-unit scope from trusted caller context rather than CSV fields;
- require an exact header set;
- require exact positive integer cents;
- require timezone-aware ISO-8601 timestamps and normalize them to UTC;
- normalize ISO currency codes and source-kind labels;
- reject duplicate event identifiers;
- bind each row proof to buyer scope, business-unit scope, source-file SHA-256, physical row number, and normalized row content;
- emit a deterministic adapter hash.

These adapters normalize evidence only. They do not decide that a settlement belongs to a claim, do not move money, and do not assert realized recovery. Settlement attribution remains governed by the persistent settlement store and reporting controls.


## Manual allocation review

If exact auto-allocation cannot identify one unique recovery claim, manual attribution must use the proof-bound Settlement Allocation Review Workflow rather than calling the settlement store's reviewed-allocation primitive directly.

The review workflow binds the event, live candidate claims, reviewer identity, rationale, timestamp, and resulting allocation to deterministic proof hashes and rejects stale cases before writing.
