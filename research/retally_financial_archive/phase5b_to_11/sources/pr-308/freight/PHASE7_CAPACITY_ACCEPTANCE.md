# RETALLY Phase 7: Payment Finding Capacity Conservation

**Status:** Unpublished Floot candidate and isolated PostgreSQL acceptance. No merge, production publish, customer records or payment actions.

## Why Phase 7 exists

Original real Floot endpoint `endpoints/recovery/payment_prepare_POST.ts` (editor version `1791467756188`) checked the requested payment against the sum of reviewer-confirmed finding variances. It neither subtracted capacity referenced by existing instructions nor checked currency against the source freight invoice. Same idempotency key returned a prior instruction without comparing request terms.

These are defects in money-bearing *preparation*, not evidence of recovered cash or money movement.

## Original counterexamples, isolated real Postgres QA

Separate Floot QA project `7257eaf3-a4d7-43db-9136-fe81e5df35bf`, unpublished, distinct production Neon project/cluster. Test namespace `phase7_capacity_qa` contains fictional buyers and invoices only; existing `m7_*` schema was untouched.

1. **Duplicate capacity:** Two independent $10 instructions each passed original per-request check for one $10 finding; combined $20 was accepted.
2. **Currency contamination:** An ostensibly USD $9 instruction against a EUR 900-cent finding passed original amount-only check.

Proposed conservative post-repair SQL control used tenant-row FOR UPDATE, underlying source currency, first-existing-instruction reservation, and request-digest comparison. Isolated database results:
- First USD instruction inserted.
- Second USD instruction for same finding rejected `ALREADY_RESERVED`.
- Identical retry returned original instruction.
- Same idempotency key + changed terms rejected.
- USD instruction on GBP finding rejected.
- Cross-tenant source rejected.
- 100 concurrent identical preparations: 1 insert, 99 replays, 0 errors, one 1,000-cent reserved record. The test completed in approximately 3.7 seconds.
- A first attempt to issue this concurrency test had a malformed SQL expression and failed 100/100 before committing anything; the corrected test was rerun successfully. Do not count the first attempt as an invariant failure.

These are direct real-PostgreSQL *equivalent SQL* tests; they are not full Floot HTTP request executions.

## Actual Floot implementation (unpublished)

Development project `c719b60c-9b3b-4193-a543-0be9d3ceaef2` changes:
- `helpers/recoveryPaymentCapacity.tsx`: pure guard, source currency, positive safe-integer amount, BigInt sum, no repeat finding IDs, reservation conflict, fail-closed malformed histories.
- `helpers/recoveryPaymentCapacity.spec.tsx`: nine independent scenarios validating the guard.
- `endpoints/recovery/payment_prepare_POST.ts`: canonical digest before idempotency lookup; same-key altered financial terms rejected; transaction and tenant-row lock around lookup/validation/insert; joined source invoice currency; all existing payment instructions inspected for overlapping finding references; rejects overlap even if prior instruction failed or reversed pending a separately verified release workflow.

Floot reported 8 spec files passed, no failures; TypeScript typecheck clean. Two hook specs excluded by default.

**Conservative restriction:** This candidate temporarily prevents *any* reuse of a finding ID across instructions, including legitimate partial subsequent instructions, because a trustworthy per-finding allocation and release ledger does not exist in the hosted application. It is a fail-closed pilot gate, not a finished partial-credit engine.

## Existing laboratory acceptance

`freight/test_lab_phase7_capacity_postgres.py` extends the existing Phase 6 ephemeral PostgreSQL CI job and reuses its database service. It provides eight tests:
- Existing control's double-capacity counterexample.
- Duplicate capacity rejection.
- 100 concurrent identical preparations.
- Two simultaneous competing requests.
- Currency mismatch.
- Cross-tenant source rejection.
- Changed idempotency digest rejection.
- Transaction rollback on injected precommit failure.

The CI job must preserve original Phase 6 tests, run all new tests, and retain source-pinned logs/manifest. A green workflow is not proof of full hosted Floot parity.

## Remaining release blockers

1. Full Floot request handler running in separately authorized hosted QA with matching schema, authentication and tenant contexts.
2. Real source entitlement, carrier/bank credit or cash documents, and independently signed effective fee terms.
3. Per-finding partial allocation and release ledger, with exact-cent conservation across issued, failed, reversed and refunded instructions.
4. Cross-finding duplicate economic issue identity, currency conversion (if ever supported) and historical tariff provenance.
5. Provider reconciliation and post-revocation correction semantics.
6. 26 original historical laboratory findings remain OPEN_UNVERIFIED; Phase 7 does not close any.

**Production unchanged. No merge, publishing, real carrier/bank operations, scheduler changes, or paid infrastructure were authorized or performed.**
