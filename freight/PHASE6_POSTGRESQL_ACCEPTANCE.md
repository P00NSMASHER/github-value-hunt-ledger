# RETALLY Phase 6: real PostgreSQL payment invariants

**Status:** Nonproduction financial-safety research. This is not hosted Floot certification, release approval, or financial audit of real carrier/bank evidence.

## Source identity

- Hosted RecoveryOS Floot project: `c719b60c-9b3b-4193-a543-0be9d3ceaef2`.
- Floot editor version of inspected Phase 5 candidate: `1791467756188`; checkpoint `ad915374-b5df-4b6a-9028-83ef34296f92`.
- Actual application files inspected: `endpoints/recovery/payment_event_POST.ts`, `helpers/recoveryPaymentReplay.tsx`, `helpers/recoveryPaymentReplay.spec.tsx`, `helpers/recoveryTenant.tsx`, `endpoints/recovery/payment_authorize_POST.ts`.
- Frozen predecessor laboratory commit: `6e3b49c382763f907b4778f193651d3a297b6b52` (PR #297). The Phase 6 PR is stacked on that research branch.
- Exact CI source revision: see `GITHUB_SHA` in the generated `phase6-postgres-manifest.json` for each run.

## Actual isolated QA database acceptance

A separate unpublished Floot project named `RETALLY RecoveryOS M7 Isolated QA` was inspected read-only before testing. Its Neon project identity and PostgreSQL cluster/system identifier are distinct from those of the published RecoveryOS project. No production credentials, data, or tables were copied.

Within the QA database, synthetic objects were created only under `phase6_lab_20261008`. The live M7 QA's `m7_*` tables were not modified. The database runs PostgreSQL 18.6, read committed.

Recorded real PostgreSQL results:

| Test | Measured result | Interpretation |
|---|---|---|
| Unlocked baseline, two concurrent different provider references | Two successful inserts; two persisted records | Existing unique keys do not prevent same-instruction distinct-reference race |
| `FOR UPDATE` transaction, 100 concurrent identical deliveries | 100 completed; 1 INSERT; 99 REPLAY; 1 persisted record; 0 errors; 4,385 ms | DB transaction invariant passed using test-only SQL implementation |
| Two different references under row lock | One INSERT; second `CONFLICTING_SUBMISSION`; 1 persisted | Conflicting race rejected |
| Injected failure after insert and before commit | Injected exception; no row persisted | PostgreSQL rollback proven |
| Cross-tenant instruction lookup | `TENANT_INSTRUCTION_NOT_FOUND`; no modification | Tenant-scoped query rejects wrong tenant |
| Retry after simulated lost acknowledgment | Stable previously inserted event | DB-side replay recognized |

These synthetic database operations **mirror** the relevant Phase 5 transaction shape and constraints. They do **not** execute the complete actual Floot HTTP endpoint or externally authenticated carrier callbacks.

## Ephemeral GitHub CI acceptance

The preexisting `.github/workflows/freight-phase4.yml` now includes a `phase6-postgresql-concurrency` job with an ephemeral PostgreSQL 18 service. `freight/test_lab_phase6_postgres.py` executes six independent unittest regressions attached to existing Lab 05/06/11/12 responsibilities. Failures raise nonzero process exit codes. The run uploads an exact-head JSON manifest and test transcript, including on test failure. There is no new scheduler or fifteenth lab.

## Material limitations / release blockers

1. **Hosted application parity is not proved.** The product's TypeScript handler has a transaction with `FOR UPDATE`, but no full API/DB concurrency test has been executed against its unmodified real source in a separate complete Floot staging build.
2. **Authorization meaning is unresolved.** The Phase 5 helper rejects new transitions after a missing authorization. Production authorization records have no standard revocation flag/endpoint in the inspected payment authorization schema, so the original missing-record state may be reachable only by unusual/manual data changes. Real provider settlement reports and post-revocation corrections need separate evidence-authenticated authority.
3. **Provider authenticity is not certified.** A scoped API key does not itself prove a carrier/bank signed a cash settlement.
4. **Financial conservation is not hosted-certified.** The published RecoveryOS schema has payment instructions/authorizations/events, but no independently established cash/credit/fee subledger to verify candidate->claim->carrier credit->bank cash->fee->reversal end-to-end. Do not equate SETTLED status with recovered cash.
5. **UNKNOWN outcomes and partial carrier settlements remain unsupported or unverified in hosted payment-event states.**
6. Existing 26 historical findings remain `OPEN_UNVERIFIED`; these newer SQL-equivalent regression tests cannot close them.
7. No production deployment, payment, real customer data, scheduled-task modification, or paid resource provisioning occurred.

## Acceptable next release proof

Deploy the **candidate only to independently segregated staging** with actual Floot handler, authentication, tenant API, PostgreSQL schema, provider mocks, and exact source pin. Run 100 concurrent identical and conflicting HTTP callbacks, injected transaction failure, lost-ack replay, revocation correction, and externally evidenced reversal/cash conservation tests. Obtain independent acceptance before release.

The verified improvement here is **real database-level evidence**, not yet production-verified financial integrity.
