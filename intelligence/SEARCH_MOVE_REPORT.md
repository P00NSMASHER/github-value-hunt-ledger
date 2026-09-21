# SEARCH MOVE LEARNING REPORT

Observe-first learning at retrieval-move granularity. A move is a concrete search action such as code-signature search, lineage tracing or adjacent-domain invariant search. These observations do **not** currently change allocation automatically.

- Discovery runs: **22**
- Runs with move-level telemetry: **0**
- Recorded search moves: **0**
- Move types observed: **0**

## Move-type evidence

| Move type | Uses | Qualifying hit | Productive hit | Retrieval-limited | Deep | Retained | Evidence |
|---|---:|---:|---:|---:|---:|---:|---|
| — | 0 | — | — | — | 0 | 0 | insufficient |

## Learning rules

- No historical run was retroactively assigned move-level results.
- Do not infer absence from a no-hit when the move was retrieval-limited or blocked.
- Prefer objective-specific evidence over global averages when enough examples exist.
- A productive move can still be expensive; whole-run outcome and effort telemetry remain authoritative for portfolio decisions.
- Do not suppress low-frequency exploration because one move type has high early hit rate.
- Search-move evidence becomes a scheduling prior only after minimum-sample gates and recall audits are satisfied.
