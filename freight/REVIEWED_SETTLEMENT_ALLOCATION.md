# Reviewed Settlement Allocation

Ambiguous, batched, or partial settlement evidence can require a human to decide how much of an external event belongs to a specific recovery claim. This workflow turns that decision into a deterministic proof artifact instead of a raw database call.

## Decision proof

A reviewed allocation is bound to:

- the verified recovery-claim batch;
- exact claim ID, finding ID, finding proof and claim-record proof;
- exact settlement event ID and source proof;
- currency and reviewed allocation cents;
- reviewer role;
- timezone-aware review timestamp;
- human review reason;
- the exact pre-allocation settlement snapshot hash.

The allocation ID is derived from the decision hash.

## Safety

The decision builder fails closed when:

- the claim is not part of the verified claim batch;
- the persisted claim differs from that batch;
- settlement payer, payee or currency differs from the claim;
- the settlement predates claim issuance;
- the human review timestamp predates the settlement event;
- the requested amount exceeds claim or event residual capacity.

A batch/remittance reference may differ from the invoice reference, but only under explicit human review with matching counterparty/currency and residual capacity.

## Stale-decision protection

Before persistence, the current settlement snapshot must equal the decision's pre-snapshot hash. If any unrelated claim/event/allocation/counter evidence changes after the human decision, the decision is rejected and must be rebuilt.

Exact replay of an already-applied decision is idempotent.

This workflow records attribution of existing external settlement evidence. It does not create money movement, contact a carrier, accept a settlement offer, or by itself establish realized recovery.
