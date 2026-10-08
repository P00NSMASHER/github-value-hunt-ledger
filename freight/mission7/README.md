# Mission 7: Financial integrity staging candidate (NOT deployed)

Snapshot source: production Floot project `c719b60c-9b3b-4193-a543-0be9d3ceaef2` (virtual source version `1791462078397`), GitHub main `3f9c9e46ac8f9422fbc6e83d22f8dd9416427787`.

## Confirmed original defects
- `endpoints/recovery/payment_prepare_POST.ts:31-49` sums positive confirmed findings but has no cross-instruction conservation or currency verification.
- `payment_prepare_POST.ts:21-29` accepts conflicting idempotency reuse.
- `analytics_ask_POST.ts:50-79,147-168` mixes currency values; `29-31` renders all money as USD.
- `payment_event_POST.ts:9-78` records a provider-reported SETTLED event without independent cash reconciliation.

## Implemented isolated PostgreSQL candidate
See `staging_schema.sql`. This is generated from the new dedicated QA database, **not** the customer's production data plane.
`m7_prepare_instruction` serializes competing allocations via finding-row locks, checks currently committed sums per tenant/economic key/currency, bounds them to independently eligible net-new finding amounts, validates currency, and binds idempotency to exact JSONB payload content. Rows are append-only. Provider assertions and buyer reconciliation are separate concepts.

No automatic allocation release is available: this intentionally fails closed until independently verified reversal/adjustment authorization is designed.

## Independent executed evidence
The source-equivalent legacy arithmetic reproduced 2 x $1,000 allocations against a single $1,000 entitlement and accepted a EUR request for USD evidence.
In a distinct unpublished Floot QA project (ID `7257eaf3-a4d7-43db-9136-fe81e5df35bf`), the SQL candidate:
1. Accepted initial eligible USD allocation.
2. Accepted exact idempotent replay.
3. Rejected a second full allocation against the same entitlement.
4. Rejected mixed currency.
5. Rejected conflicting idempotency.
6. Rejected incumbent-known value.
7. Rejected a blocked finding.
8. Rejected cross-tenant reference.
9. Accepted separate EUR entitlement.
10. In two concurrent QA database calls for the same remaining $1,000 entitlement, exactly one committed and the other failed; $1,000 total allocated.

No original production rows were read as customer payloads. No production DB writes or Floot publishing occurred.

## Explicit limitations and deployment blockers
This is a tested **staging financial kernel**, not a patch automatically wired into the live Floot application. Before rollout: port the guarded function and tables into a reviewed migration using production `recovery_*` records; update payment preparation to call it transactionally; partition ALL analytics by currency; add verifier-backed realized-cash and fee-eligibility paths; run a full staging clone and adversarial concurrent HTTP tests; review historical instruction migration; independent tenant/RLS/security testing; document rollback. Do not deploy the isolated `m7_` schema as if it were a production migration.

## Proposed acceptance gate
`staging_acceptance.sql` runs synthetic DB-boundary tests under a transaction and rolls them back. A separate multi-session concurrency test is required: the single-transaction SQL cannot establish cross-connection isolation. Production acceptance remains **NO-GO**.

## Additional defense-in-depth verified in isolated staging
- A BEFORE INSERT conservation trigger rejects raw allocation inserts even if they bypass the controlled preparation function.
- Finding entitlements cannot be updated or deleted after creation. Adjustments require an independently designed append-only revision protocol.
- The recovered-cash reporting view is intentionally empty: a free-text verifier name or untrusted provider event is **not** independent proof of funds.
- Clean-bootstrap CI ran successfully on PostgreSQL 16 for revision `a4a9ebd086fed4e89403474055f624a480c5be3c`.
- A separate two-connection concurrent transaction race is now in CI and must be accepted independently; this is distinct from the sequential transaction fixtures.

### Current security limit
The staging project has an isolated database containing only artificial records. The current function is NOT ready to accept live customer records. A service-role grant boundary, verified source/authority enrollment, historical entitlement backfill, reviewer/buyer sign-off, evidence-backed reversals and full HTTP authentication tests are required for production.
