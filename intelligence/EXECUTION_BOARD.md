# HUNT EXECUTION BOARD

V11 derives execution state from append-only per-slot events. Missing event logs mean AVAILABLE.

| Slot | Role | Assignment | State | Worker | Claim | Telemetry |
|---|---|---|---|---|---|---|
| SLOT-01 | experiment | ASSIGN:e4a38e4e610c:slot-01 | **RELEASED_AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-02 | experiment | ASSIGN:e4a38e4e610c:slot-02 | **RELEASED_AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-03 | experiment | ASSIGN:e4a38e4e610c:slot-03 | **AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-04 | experiment | ASSIGN:e4a38e4e610c:slot-04 | **EXPIRED_AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-05 | experiment | ASSIGN:e4a38e4e610c:slot-05 | **RELEASED_AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-06 | experiment | ASSIGN:e4a38e4e610c:slot-06 | **AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-07 | coverage | ASSIGN:e4a38e4e610c:slot-07 | **EXPIRED_AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-08 | coverage | ASSIGN:e4a38e4e610c:slot-08 | **AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-09 | coverage | ASSIGN:e4a38e4e610c:slot-09 | **AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-10 | adjacency | ASSIGN:e4a38e4e610c:slot-10 | **AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-11 | measurement | ASSIGN:e4a38e4e610c:slot-11 | **AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-12 | measurement | ASSIGN:e4a38e4e610c:slot-12 | **RELEASED_AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-13 | verification | ASSIGN:e4a38e4e610c:slot-13 | **AVAILABLE** | — | — | NOT_APPLICABLE |
| SLOT-14 | wildcard | ASSIGN:e4a38e4e610c:slot-14 | **AVAILABLE** | — | — | NOT_APPLICABLE |

## Claim protocol

1. Claim by appending a CLAIM event to the slot's JSONL file using optimistic file-SHA concurrency.
2. Heartbeat before lease expiry for long work.
3. Write the V11 search-run telemetry before appending COMPLETE.
4. COMPLETE only after the search run exists with exact claim and assignment provenance.
5. Retryable FAIL or RELEASE returns the slot to the claimable pool; non-retryable FAIL blocks the same assignment.
