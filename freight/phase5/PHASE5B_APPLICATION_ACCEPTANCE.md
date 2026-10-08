# RETALLY Phase 5B | Actual RecoveryOS Handler Acceptance on Isolated Floot QA

**Evidence scope:** 2026-10-08. Unpublished Floot QA project; real PostgreSQL and the current production-source TypeScript payment-event handler copied verbatim into QA. All callers, tenants, amounts, provider references, and receipts are fictional.

## Independently observed isolation

| | Published RecoveryOS | Unpublished QA |
| --- | --- | --- |
| Project ID | `c719b60c-9b3b-4193-a543-0be9d3ceaef2` | `7257eaf3-a4d7-43db-9136-fe81e5df35bf` |
| PostgreSQL system_identifier | `7693746749463444100` | `7694294930552894346` |
| Production writes performed here | **0** | Only synthetic QA fixture writes |
| Published | Yes | No |

The difference in PostgreSQL system identifiers verifies distinct clusters. Both cluster IDs were checked with separate **read-only** queries. The isolated QA project has a dedicated database resource; no production credentials or customer data were copied.

## Repair to test-harness failure

The original 20-request attempt raised a JavaScript `TypeError` while serializing an undefined helper return. At that checkpoint, a follow-up database query found zero events. The harness was corrected to use Floot's **write-enabled** SQL execution interface for the mutation-bearing `SELECT phase5_qa.record_provider_event(...)` statement, then separately inspect the real database.

One later 16-request batch was rejected for `MOCK_PROVIDER_ACTOR_UNAUTHORIZED` after the isolated QA function acquired a mock-actor requirement. The function was *not* weakened: a SIM-only actor was explicitly registered in the QA actor table. Re-running the 16-request test then produced one committed event and 15 legitimate replays, with all return IDs equal and one database row independently observed.

See `phase5b_handler_acceptance.json` for failure and success records; `phase5b_independent_queries.sql` for database-only checks.

## Actual TypeScript handler tested

Copied these source files **unchanged** from the currently connected published-source project into the QA project:

- `endpoints/recovery/payment_event_POST.ts`
- `helpers/recoveryPaymentReplay.tsx`
- `helpers/recoveryHash.tsx`
- `endpoints/recovery/payment_event_POST.schema.ts`

The first three were compared source-to-source and found equal after normalizing terminal newlines. The actual handler uses a PostgreSQL transaction, `SELECT ... FOR UPDATE` locking on tenant/instruction, and the existing unique event constraints.

To avoid production authentication services, `helpers/recoveryTenant.tsx` is an explicitly mock-only QA substitute. The QA project also has synthetic payment instruction, authorization and event tables with compatible columns and basic constraints. **This is real handler-code and PostgreSQL behavior, but NOT full production authentication/schema equivalence.**

The QA project remains unpublished. Do not copy the mock authentication into published RecoveryOS.

## Observed acceptance

- PostgreSQL function: new submission accepted, exact sequential retry returned the same event.
- Eight parallel exact retries: same ID, zero additional events.
- New 16-request parallel race: **1 new durable event, 15 exact replays, 1 database row.**
- Two parallel conflicting source-digest attempts: **1 committed, 1 rejected**, no incompatible double posting.
- Wrong source hash under same reference: rejected.
- Cross-tenant reuse of the same provider reference: accepted *only* under a distinct fictional tenant/instruction.
- Unregistered actor and wrong-tenant instruction: rejected.
- Chronologically earlier new state: rejected.
- Full SUBMITTED → ACCEPTED → SETTLED → REVERSED chain persisted; replay of earlier SUBMITTED and SETTLED returned their original references.
- OUTCOME_UNKNOWN stopped further automatic SUBMITTED events.

**Actual TypeScript HTTP handler:**

- Twelve concurrent exact HTTP callbacks: **12 HTTP 200, 1 unique ID/hash, 1 durable database row**.
- Two competing first SUBMITTED callbacks using different provider references: **1 HTTP 200, 1 HTTP 400**, 1 durable database row.
- Valid ACCEPTED, SETTLED, REVERSED transitions: HTTP 200; historical SUBMITTED replay after reversal: same original ID.
- Altered source digest under existing event reference: HTTP 400.
- Cross-tenant lookup of another tenant's instruction: HTTP 400.
- Independent PostgreSQL query showed 1 A submission event, B's 4-event lifecycle, and 1 C first-submission winner.

All QA evidence uses test-only values and may not be presented as real cash recovered.

## Financial limitations and historic findings

Payment events only establish **application provider-event states**; `SETTLED` is not customer received/reconciled cash. The current staging handler deliberately has no authoritative buyer-bank/carrier ledger or contractual fee receipts. It therefore cannot independently reconstruct final customer cash, earned contingency fees, or refund liabilities.

The original 26 cumulative laboratory findings remain `OPEN_UNVERIFIED` in this PR. Earlier Phase 2 separately reproduced and patched original offline laboratory flaws, but neither a QA payment-event test nor a research checker independently proves those specific original implementations meet the complete historical closure conditions.

A notable old finding `D-07` concerns idempotent replay of an operation by a *different actor*. The isolated PostgreSQL function now checks SIM-only actor role and binds the actor to its replay, while the actual TypeScript event table does not persist external provider actor identity as a financial authority. This is **not** sufficient to close D-07 across both systems. It needs a documented, actual original counterexample replay and proof of real actor attestation, or explicit waiver with controls, before status advancement.

## Decision and release gate

**Verified:** Separate PostgreSQL clusters, the SQL mock-provider function's durable concurrency controls, and the actual handler's row-locked duplicate-event behavior against a fictional QA schema.

**Not verified:** Production authentication equivalence, real issuer authority, real financial settlement/recovery, complete source/contract-to-cash application flow, original finding closures, production release safety.

No production database mutations, customer contact, carrier claims, banking transactions, paid resources, merges, publishes, or scheduled task changes occurred in this work.
