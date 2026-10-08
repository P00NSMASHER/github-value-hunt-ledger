# RETALLY Phase 5 — Isolated staging acceptance and boundaries

This is **executed** PostgreSQL QA engineering, not financial or commercial certification. The published RecoveryOS service remains unchanged.

## Real resource separation
Published Floot project: `c719b60c-9b3b-4193-a543-0be9d3ceaef2`. Its PostgreSQL system identifier was independently read as `7693746749463444100`. Separate unpublished Floot QA project: `7257eaf3-a4d7-43db-9136-fe81e5df35bf`, with PostgreSQL system identifier `7694294930552894346`. Read-only inspection showed 23 public production tables and six preexisting QA tables, with distinct names. No test writes were sent to the published database. The QA project was already present and is shared with an independently named M7 QA effort; this phase added only its own `phase5_qa` namespace and fictional records.

## QA PostgreSQL implementation and actual results
`isolated_postgres.sql` protects itself with the QA-specific cluster identifier and refuses the production payment-event table. It adds tenant-scoped fake instructions, mock provider/actor admission, an event table with unique provider reference and sequence, transaction-scoped advisory lock plus row lock, append-only mutation trigger, and a canonical event hash. This intentionally **does not** authenticate a real carrier or make a bank transfer.

Initial implementation failed against the real QA Postgres because restricted `search_path` hid unqualified pgcrypto `digest`. The function was corrected to `public.digest` and rerun.

Observed QA data-plane experiments: 20 concurrent identical SUBMITTED requests resulted in **one** event, **19** read-only replays, and no errors. Eleven subsequent expected cases covered acceptance, settlement, reversal, post-reversal retry, altered payload, invalid transition, cross-tenant reference reuse, and terminal OUTCOME_UNKNOWN. An added mock-actor authorization check rejected a spoofed actor; an approved mock actor proceeded. Database mutation of an existing event was prevented by the VM's write policy before SQL execution; therefore **the original QA trigger was not adversarially exercised in that observation**. The disposable PostgreSQL CI acceptance independently tests the append-only trigger and uniqueness directly.

The PostgreSQL event status `SETTLED` is **not** customer-realized recovery. The script tracks mock provider events only; it has no authoritative buyer-bank credit reconciliation or legitimate fee accrual.

## Historical original failure replay
Original Unified Five-Step archive SHA-256:
`2dcfd16296454689a391fb76ac57e4a9282091c25d85134334b3c7eeeeafc93b`.
Original audit reproduced **7/7** known offline defects, including an unbacked $1 million fictional cash journal row.
The independently extracted Phase 2 repaired ZIP SHA-256:
`8e0abb53632b82a6228bbf8fe5dc35da14b52ba9b4e1edfb985f62bf96c02e9d`.
The five Phase 2 original probes reproduced **0/5** on the patched standalone code, and the 89-test legacy+patch suite passed, with cleanup ResourceWarnings. These constitute a **research-only repair** of those original offline classes. They do not prove fixed hosted RecoveryOS implementations, real buyer source ownership, or support closing any of the 26 cumulative historical findings.

## Acceptance and remaining blockers
Run:
```sh
PYTHONPATH=. python -m pytest -q -rs freight/phase5/test_isolated_postgres.py
```
Only in a disposable PostgreSQL service called `retally_phase5_ci`, with `RETALLY_PHASE5_CI_DSN` set; the test itself refuses other database names and the known production cluster identifier. The GitHub workflow provisions PostgreSQL 16 and pinned `psycopg[binary]`.

The previous 14 Python laboratory adapters, independent finance verifier, Ed25519 research tests and three fictional founding customers are inherited; do not interpret their CI success as hosted end-to-end application execution. The connected published application source currently contains a Kysely transaction with `FOR UPDATE` on instruction rows; its database index scoping differs from this staging implementation. No automatic deploy/merge or live payments/customer contact occurred.

**Unresolved before a real customer pilot:** genuine buyer/carrier/bank issuer control, per-account historical contracts, full RecoveryOS staging application/auth flow, authenticated carrier callback ingress, signed settlement data, and independent per-finding defect closure. The 26 historical entries remain `OPEN_UNVERIFIED`.

The business-readiness judgment for a real recovery engagement remains **BLOCKED pending external financial evidence and application integration**. Simulated customer casework is still available from Phase 3; do not present its numbers as actual revenue.
