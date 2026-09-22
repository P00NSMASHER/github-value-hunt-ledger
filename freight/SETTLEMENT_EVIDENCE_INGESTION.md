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


## Ambiguous counter/reversal review

If a return or reversal cannot be auto-applied because it is ambiguous across multiple live allocation edges, the Counter/Reversal Review Workflow must be used.

The workflow snapshots current live allocation capacity, requires a reviewer decision bound to the exact case, rejects stale state before writing, and applies the reversal through the reviewed-reversal transaction primitive. Split reviewed reversals remain unsupported.


## Lifecycle orchestration

For operational processing, settlement and counter CSVs can be passed through the Settlement Evidence Lifecycle Workflow. It parses every supplied file before persistent writes, preflights cross-file references, runs safe automatic allocation/reversal, and returns proof-bound settlement/counter review cases for anything ambiguous.


## Returned-payment capacity

A counter/return event reduces the original settlement event's allocatable capacity as soon as the return evidence is ingested. The store computes available event capacity from **net settlement funds**:

`original settlement - observed returns - live allocations`

where live allocations are gross allocations less applied reversals.

Consequences:

- a fully returned payment has zero capacity for later claim allocation, even if no allocation existed when the return arrived;
- unused gross payment remainder cannot be allocated after that portion of the payment was returned;
- an applied partial return can free only the amount that still exists in net settlement funds;
- cumulative counter events cannot exceed the original settlement amount;
- additive SQLite triggers enforce the same rules for direct SQL and for databases created under an older schema revision;
- reopening a database fails closed if historical counter rows already exceed their original settlement event.

The persistent report's unresolved-counter check remains a downstream defense. This store rule prevents the invalid recovery state from being created in the first place rather than relying on reporting to catch it later.
