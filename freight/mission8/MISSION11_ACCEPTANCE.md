# RETALLY M11: Authenticated RecoveryOS handler acceptance

**Candidate scope:** isolated, unpublished Floot M8 source, copied verbatim into an ephemeral GitHub Actions PostgreSQL-16 test harness. **No production deployment, no customer/real carrier data, no payments.** This report must not be construed as hosted Floot acceptance.

## Original defects in actual M8 TypeScript payment preparation

Original M8 source `endpoints/recovery/payment_prepare_POST.ts` interpolated `JSON.stringify(body)` followed by `::jsonb` into Kysely/Postgres.js. Using the actual dependency versions (`kysely 0.26.3`, `kysely-postgres-js 5.0.1`, `postgres 3.4.9`), an authenticated test owner resolved correctly as `handler_t`, but PostgreSQL observed the JSONB parameter as a **string**, not an object. All 100 positive preparation requests failed with `invalid tenant scope`. An isolated read-only parameter probe verified the original JSON string type.

The candidate now interpolates **the original structured object** with `::jsonb`. The frozen probe confirms JSONB type **object** and matching tenant.

After that repair, all 100 positive requests failed with `Financial allocation reconciliation failed`. The database function succeeded but the endpoint read `instruction_hash` and `instruction_id` from Kysely rows, while its configured `CamelCasePlugin` normalizes those fields to `instructionHash` and `instructionId`. A failed HTTP response after commit could invite an unsafe new idempotency key. The candidate now reads the normalized fields.

## Real copied-handler localhost HTTP regression

`freight/mission8/ci_authenticated_handler.mjs` imports the exact M8 staging TypeScript financial handlers, original tenant/session helpers, original Kysely/Postgres.js data access, and validates a **legitimate synthetic JWT** with a valid database session and tenant membership. Test PostgreSQL uses the actual RecoveryOS schema and existing M8 financial function, with new fictional `handler_t` resources.

The test invokes genuine Web `Request`/HTTP `Response` handler paths over ephemeral localhost HTTP:

- Synthetic user and tenant ownership proven; unauthenticated prepare receives 401.
- Original JSONB double-encoding reproduced; corrected structured parameter passes.
- 100 simultaneous preparation requests using one idempotency key return one instruction.
- Exactly one 10,000-minor-unit instruction and matching single allocation persist.
- Changed idempotency payload, foreign currency and over-capacity attempts are rejected.
- 100 simultaneous authorization requests return one original authorization ID; exactly one authorization row exists.
- 100 simultaneous `SUBMITTED` event deliveries return one persisted event.
- `ACCEPTED`, `SETTLED`, and `REVERSED` transitions succeed with four append-only events.
- An application `SETTLED` label continues to report `settlementVerification=UNVERIFIED` and `verifiedRecoveredCents=0`.

There are **18 assertions/cases**, not 18 independent business scenarios. See the exact-head CI artifact, including before/after failures and source hashes. This is stronger than SQL-equivalent simulations, but **the integration runs locally, not through Floot's hosted HTTP gateway**.

## Hosted staging access gate

Floot M8 project ID `41bb5a26-a38a-4a93-ae8d-a07f9e11f77b`, database Neon project `mute-scene-87269526`, cluster ID `7694301220230018932`, is isolated from production project `c719b60c-9b3b-4193-a543-0be9d3ceaef2`. Direct tooling has observed valid unauthenticated 401 responses. GitHub-runner requests have intermittently received `403 CASE 3: Combini sandbox access denied`, not application responses. This is a hosted access blocker, not proof that the payment endpoint failed. A separate **fail-closed hosted-access gate** remains red and produces a durable blocked receipt; it is not ignored or converted to success.

## Additional production-release blockers

- Positive authenticated *hosted Floot* end-to-end financial acceptance.
- Real independent buyer authorization, claim eligibility provenance, carrier acknowledgments, bank credit/cash verification, and fee collection.
- Partial allocation releases, reversals, refunds, and cross-currency commercial contracts.
- Formal external security/tenant isolation testing and safe legacy migration.
- Original **26 historical OPEN_UNVERIFIED findings** remain open; none closed based on this isolated result.
- GitHub PR chain #306 → #315 → #318 → #325 → M11 draft must be reviewed before any merges. Production source and financial database remain unchanged.

**Release decision: Candidate integration code improved, customer-money release blocked.**
