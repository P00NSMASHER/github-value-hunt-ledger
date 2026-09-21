# Settlement Evidence Lifecycle Workflow

The Settlement Evidence Lifecycle Workflow is the operational boundary above settlement CSV ingestion, safe automatic attribution, and proof-bound review-case generation.

It accepts one or both of:

- settlement/remittance CSV evidence;
- counter/return/reversal CSV evidence.

The workflow is bound to an existing buyer/business-unit `SettlementStore`.

## Processing order

1. Parse **all supplied CSV files** before any persistent write.
2. Preflight immutable replay conflicts, source-hash reuse, counter/original-event references, currency, event chronology, and processing-time chronology.
3. Ingest settlement events.
4. Run safe exact auto-allocation for each settlement event.
5. Generate Settlement Allocation Review cases for any event that remains ambiguous.
6. Ingest counter-events.
7. Run safe auto-reversal for each counter-event.
8. Generate Counter/Reversal Review cases for any ambiguous return.

The workflow never auto-resolves a human-review case.

## Preflight-before-write rule

A malformed counter file, unknown counter reference, counter currency mismatch, impossible evidence chronology, a processing timestamp earlier than supplied evidence, or immutable replay conflict is rejected before the valid settlement file in the same package writes anything.

## Economic event-time integrity

All persisted settlement timestamps are canonical UTC. Allocation edges cannot be created before their settlement event was booked. Reversal edges cannot be created before the counter/return was observed or before the allocation being reversed existed.

These rules are enforced twice:

- in the Python `SettlementStore` boundary, including timezone-aware parsing and UTC normalization;
- in SQLite triggers, so direct SQL cannot bypass timestamp validity or economic chronology.

Equivalent timezone-offset inputs normalize to the same UTC timestamp for replay/idempotency checks.

This does not claim a global multi-row database transaction across the entire lifecycle. Each underlying store write remains independently transactional. The preflight boundary is designed to eliminate predictable package-level partial writes before processing begins.

## Review state

The workflow returns:

- **COMPLETE** — every supplied event reached an automatic terminal attribution state;
- **REVIEW_REQUIRED** — one or more proof-bound Settlement Allocation Review or Counter/Reversal Review cases require human resolution.

Review cases are returned as full typed proof objects, not only IDs.

## Replay semantics

Raw first-run statuses can differ from replay statuses:

- `ALLOCATED` vs `ALREADY_ALLOCATED`;
- `REVERSED` vs `ALREADY_REVERSED`;
- `INGESTED` vs `ALREADY_PRESENT`.

The workflow therefore exposes two hashes:

- **state_hash** — binds normalized evidence adapters, effective terminal states, review-case hashes, and the final store snapshot. Identical final state produces the same hash across exact replay.
- **execution_hash** — additionally binds execution time, before/after snapshots, and raw execution statuses. A later replay can have a different execution hash while preserving the same state hash.

## Safety boundary

The lifecycle orchestrator:

- does not make buyer review decisions;
- does not choose a claim for ambiguous settlement allocation;
- does not choose an allocation for an ambiguous return;
- does not contact a carrier;
- does not move money;
- does not itself convert discrepancy dollars into realized savings.

Human settlement/counter decisions remain separate proof-bound workflows.


## Package atomicity

Settlement and counter evidence supplied in one lifecycle call are now persisted inside one `BEGIN IMMEDIATE` transaction. Event ingestion, safe auto-allocation, counter ingestion, safe auto-reversal, and final automatic re-evaluation either commit together or roll back together.

The transaction captures both the actual pre-write and post-write store snapshots. Lifecycle provenance uses those transaction snapshots rather than an earlier advisory read.

Review cases are generated only after the atomic package has reached its final state. This prevents the workflow from returning a review-case hash based on claim/allocation capacity that a later row in the same package already changed.

A final automatic pass is intentional:

1. counters can restore claim capacity, making a settlement that initially required review safely auto-allocatable;
2. that newly created allocation can make a counter safely auto-reversible.

After those passes, remaining review cases are derived from the transaction's final snapshot. Any later concurrent store change is still caught by the existing proof-bound review workflows when a human tries to apply the decision.
