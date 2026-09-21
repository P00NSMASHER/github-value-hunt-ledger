# HUNTER-04 R25 — EXP-009 typed source-observation receipt acceptance contract

- **Observed at:** 2026-09-21T13:32:00Z
- **Worker:** HUNTER-04
- **Execution mode:** unallocated/manual live-worker path.
- **Lifecycle note:** Pair 2 benchmark tasks 09–15 were already COMPLETE. The generated HUNTER-04 SLOT-06 dispatch for `WORK:seed:f4717ef30b92` had hard-expired at 2026-09-21T08:59:58Z. A fresh READY write was attempted but blocked by the connector safety layer; no activation, claim, lease, generated assignment, completion event, or commercial outcome is asserted.
- **Capability / experiment:** CAP-012 / EXP-009
- **Bounded action:** execute the missing source-observation receipt classifier against the failure classes already established by R23. No new repository discovery was performed.
- **Prior frozen evidence reused:** `referrals/hunt04-r23-2026-09-21-exp009-three-jurisdiction-permit-benchmark.md`. R23's San Francisco/Tempe/San Antonio counts and hashes are treated as prior frozen observations, **not refreshed current-source claims in this run**.

## Hypothesis

PermitPlate can safely distinguish a complete/empty permit source from source movement, outage, sampling, truncation, and unproven emptiness only when the observation receipt binds source/config identity, schema evidence, page/cursor closure, count evidence, raw-page hashes, scope intent, and freshness metadata.

## Receipt contract exercised

Minimum receipt fields used by the fixture:

- `source_id`
- `connector_config_hash`
- `observed_at`
- transport/HTTP state
- redirect target when present
- `intended_full_scope`
- `publisher_count` when available
- `fetched_count`
- `cursor_closed`
- `schema_fingerprint`
- `raw_page_hashes`
- freshness deadline / currentness metadata

Terminal interpretation states:

- `VERIFIED_EMPTY`
- `COMPLETE_NONEMPTY`
- `PARTIAL`
- `SOURCE_UNAVAILABLE`
- `SOURCE_MOVED`
- `UNKNOWN`

## Decision rules

1. Transport error or HTTP failure -> `SOURCE_UNAVAILABLE`.
2. Redirect/moved canonical endpoint -> `SOURCE_MOVED`; do not reinterpret as empty.
3. A sample/non-full-scope observation cannot become complete; nonempty sample -> `PARTIAL`, empty sample -> `UNKNOWN`.
4. Full-scope zero rows without schema/source evidence and pagination/cursor closure -> `UNKNOWN`.
5. Full-scope observation with source/config/schema/raw-page evidence and closed pagination:
   - count mismatch -> `PARTIAL`;
   - exact count 0 -> `VERIFIED_EMPTY`;
   - exact positive count -> `COMPLETE_NONEMPTY`.
6. An unresolved/partial observation cannot delete, close, retire, or suppress an existing permit opportunity.

## Executed synthetic acceptance matrix

The classifier was executed locally against seven planted cases:

| Case | Expected | Observed |
|---|---|---|
| stale SF host redirects | SOURCE_MOVED | SOURCE_MOVED |
| transport timeout/outage | SOURCE_UNAVAILABLE | SOURCE_UNAVAILABLE |
| zero rows, no closure proof | UNKNOWN | UNKNOWN |
| zero rows, exact count + closure + schema/source hashes | VERIFIED_EMPTY | VERIFIED_EMPTY |
| publisher count != fetched count | PARTIAL | PARTIAL |
| exact positive count + closure + evidence | COMPLETE_NONEMPTY | COMPLETE_NONEMPTY |
| intentional non-full sample | PARTIAL | PARTIAL |

**Result: 7/7 expected classifications.**

Deterministic matrix digest:

`sha256:ec98661714c12c89b0d8efac7b2abd4426c277fd78f6817577462f5a6424e7fe`

## Claims tested

- **Zero normalized rows are sufficient for "no permits":** FALSIFIED.
- **Transport failure can safely become zero:** FALSIFIED.
- **A moved source can safely be interpreted as empty:** FALSIFIED.
- **Sampling can establish whole-source completeness:** FALSIFIED.
- **Count mismatch can still be complete:** FALSIFIED.
- **Verified emptiness is representable when exact source/schema/count/closure evidence exists:** PASSED in the synthetic contract.
- **Complete nonempty is representable when counts and closure reconcile:** PASSED in the synthetic contract.

## Red-team / verifier verdict

**ACCEPT as an EXP-009 acceptance-contract refinement; NOT a live-source completion proof.**

The fixture proves classification semantics only. It does not prove that PermitBuild/PermitPlate currently emits all required receipt fields, follows source moves safely, or obtains authoritative publisher totals for every jurisdiction. Current live endpoint probing was attempted through the available web surface, but those direct API URLs were inaccessible through that retrieval tool in this run; that retrieval limitation was not converted into source unavailability.

## Capability delta

CAP-012 should be split into two independently testable outputs:

1. **Permit event truth:** normalized immutable permit identity/version and field semantics.
2. **Source observation truth:** a typed receipt proving what source window was actually observed and whether absence/completeness claims are justified.

A permit row without a receipt may still be a useful positive observation. A negative/absence claim without a sufficient receipt remains UNKNOWN.

## EXP-009 fixtures added

1. `FULL_SCOPE_ZERO__NO_CURSOR_CLOSURE__UNKNOWN`
2. `FULL_SCOPE_ZERO__COUNT_ZERO__CLOSED__VERIFIED_EMPTY`
3. `FULL_SCOPE_POSITIVE__COUNT_MATCH__CLOSED__COMPLETE_NONEMPTY`
4. `FULL_SCOPE_POSITIVE__COUNT_MISMATCH__PARTIAL`
5. `SAMPLE_NONEMPTY__PARTIAL_NOT_COMPLETE`
6. `SOURCE_REDIRECT__SOURCE_MOVED_NOT_EMPTY`
7. `TRANSPORT_ERROR__SOURCE_UNAVAILABLE_NOT_EMPTY`

## Commercial implication

PermitPlate can make a stronger product claim by distinguishing:

- **"No qualifying permit observed in a verified-complete source window"**
from
- **"No permit returned by this request."**

The former is decision-grade evidence. The latter may be an outage, moved host, partial page, sample, schema change, or unproven empty response. This distinction directly reduces false "no opportunity" conclusions and silent lead suppression.

## Negative knowledge

- HTTP success is not completeness.
- Zero rows are not negative authority.
- Source movement is not source emptiness.
- A publisher count without pagination closure is insufficient.
- Pagination closure without source/config/schema identity is insufficient.
- A positive sample proves presence, not whole-source completeness.
- Retrieval-tool inability to access a public endpoint is retrieval debt, not source outage.

## Next falsifiable action

Implement this receipt contract around one real PermitPlate ingestion path and require the ingest/lead-state reducer to reject any deletion/closure/suppression action when the receipt state is `UNKNOWN`, `PARTIAL`, `SOURCE_MOVED`, or `SOURCE_UNAVAILABLE`.
