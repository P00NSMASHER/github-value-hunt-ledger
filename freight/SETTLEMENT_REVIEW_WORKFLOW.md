# Settlement Allocation Review Workflow

The settlement allocation review workflow is the controlled human-decision boundary for settlement events that **cannot** be auto-allocated to one exact recovery claim.

It exists to eliminate direct, unproven manual calls to `SettlementStore.review_allocate(...)`.

## When it is used

The workflow is used only when exact auto-allocation cannot select one unique claim. It builds a deterministic review case from:

- the immutable settlement event;
- the event's full remaining amount;
- live recovery-claim residual capacity;
- payer/payee/currency identity;
- claim issuance time;
- invoice/reference match state;
- prior manual-review lock state.

If exactly one non-review-locked claim with the same reference has residual equal to the event residual, the event is auto-allocatable and manual review is rejected.

## Candidate boundary

V1 supports one settlement event being assigned in full to one claim.

Eligible manual-review candidates must:

- match payer, payee, and currency;
- have been issued on or before the settlement booking time;
- have enough live residual capacity to absorb the entire remaining settlement event.

Reference mismatch is allowed only as an explicit human-reviewed candidate path, which supports documented batch-credit situations.

Split allocations across multiple claims are **not** supported by this workflow.

## Human decision proof

A decision must bind:

- exact settlement review case hash;
- selected eligible claim;
- reviewer role;
- timezone-aware review timestamp;
- non-empty rationale.

The review timestamp cannot predate the settlement booking.

The workflow derives the full allocation amount from the current event residual. Reviewers do not type the allocation amount.

## Stale-state protection

Before writing an allocation, the workflow rebuilds the review case from the current settlement store.

If claim capacity, event state, review-lock state, or other relevant evidence changed, the case no longer matches and the allocation is rejected. The operator must regenerate the case.

Exact replay of the same proof-bound review is recognized through its deterministic review/allocation ID.

## Output

A successful reviewed allocation produces a receipt containing:

- case hash;
- event and claim IDs;
- exact allocated cents;
- reviewer role/timestamp/rationale;
- stable review hash;
- deterministic allocation ID;
- store snapshot hashes before and after the state transition;
- deterministic receipt hash.

The workflow attributes observed settlement evidence. It does not move money, create a credit, accept a settlement, or by itself prove realized savings.
