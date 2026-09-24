# Value-weighted memory

Upgrade 4 gives AI Business OS an auditable retrieval prior based on:

`relevance × observed value × confidence × recency`

## Why

Ordinary memory answers "what is related?" This layer also asks whether recalling
that memory has historically been useful. It is deliberately advisory: memory
ranking never grants tool permissions, authorizes consequential actions, or
bypasses the independent auditor.

## Evidence model

- Memories are stored under an explicit scope.
- Outcome observations are append-only.
- Every observation requires an `outcome_ref` that points to external evidence.
- Usefulness is bounded to `[0, 1]`.
- Confidence grows from weighted observations, not from an agent asserting that a
  lesson is important.
- Recency decays with a configurable half-life.
- Retrieval returns every scoring factor so the ranking can be inspected.

## Failure behavior

Invalid usefulness values, missing evidence references, invalid scope/query, and
unknown memories fail closed. Cross-scope retrieval is not allowed.
