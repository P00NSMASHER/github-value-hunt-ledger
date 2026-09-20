# Freight Recovery — Pilot Audit and Data Lifecycle

Updated: 2026-09-20

This layer applies three research-derived patterns to buyer data operations:

1. **CENSUS / SCOPE / PROOF** — know what evidence objects exist, what retention/deletion policy applies, and what proof establishes a lifecycle transition.
2. **PRESENT / VERIFIED_EMPTY / UNAVAILABLE** — a failed source/query is not an empty result.
3. **UNKNOWN is not success** — an ambiguous deletion attempt stays unknown and must not be silently retried or called deleted.

## Audit chain

`freight/audit_ledger.py` provides a buyer/BU-scoped append-only hash chain for important pilot events such as source observations, truth freeze, incumbent open, report issue and data-deletion state.

The hash chain detects mutation/reordering inside the supplied record set. It is **not** external timestamp attestation.

## Data lifecycle

`freight/data_lifecycle.py` creates lifecycle entries from the machine-checkable data-room manifest.

- Data-room manifest = CENSUS.
- `retention_days` / delete-after = SCOPE.
- Explicit external deletion confirmation = PROOF.

Allowed states:
- PRESENT
- DELETE_REQUESTED
- DELETE_UNKNOWN
- DELETE_CONFIRMED

**Absence/disappearance is never deletion proof.**

A deletion call whose outcome cannot be confirmed must move to DELETE_UNKNOWN. It can only become DELETE_CONFIRMED with explicit confirmation evidence.

## Source observation receipts

Source reads can be recorded as:
- PRESENT
- VERIFIED_EMPTY
- UNAVAILABLE

VERIFIED_EMPTY requires completeness evidence. A timeout, auth failure, partial page or unavailable feed must remain UNAVAILABLE.

This is directly relevant to later settlement/readback feeds: "we saw no credit" is not a defensible outcome unless the source/window was actually observed completely.
