# Counter/Reversal Review Workflow

The Counter/Reversal Review Workflow is the controlled human-decision boundary for return/reversal evidence that cannot be unambiguously auto-applied to live settlement allocation edges.

## Automatic path first

Counter-events continue to use the settlement store's fail-closed automatic reversal logic.

Manual review is rejected when the counter can already be applied automatically, including:

- a full return of the original settlement event;
- a return equal to all currently live allocation value; or
- a partial return when only one live allocation edge exists and can absorb it.

## Review case

When a partial return is ambiguous across multiple live allocation edges, the workflow builds a deterministic case from:

- the counter-event proof;
- original settlement event;
- current live allocation edges;
- existing reversal history;
- claim identity/reference proof behind each allocation;
- each allocation's remaining live cents and fee-eligible cents.

V1 exposes only allocation edges that can absorb the **entire remaining counter amount**.

If no single edge can absorb that amount, the case can be inspected but cannot be applied through this workflow. Split reviewed reversals are intentionally unsupported.

## Human decision

The reviewer supplies:

- exact counter-review case hash;
- selected eligible allocation ID;
- reviewer role;
- timezone-aware review timestamp;
- non-empty rationale.

The amount is derived from the counter residual. It is not caller-entered.

The review timestamp cannot predate the observed counter-event timestamp.

## Stale-state protection

Before writing a reversal, the workflow rebuilds the case from the current settlement store.

If another return/reversal or other relevant state change altered live allocation capacity, the old case is rejected and must be regenerated.

Exact replay of the same proof-bound decision is recognized through a deterministic review/reversal ID and does not create a duplicate edge.

## Receipt

A successful reviewed reversal produces a deterministic receipt binding:

- case hash;
- counter and allocation IDs;
- exact reversed cents;
- reviewer role/timestamp/rationale;
- review hash;
- reversal edge ID/status;
- settlement-store snapshot hashes before and after the state transition.

This workflow changes attribution of already-observed settlement evidence. It does not move money, create a bank return, or independently prove realized savings.
