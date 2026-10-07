# RecoveryOS Phase 1 — incumbent challenge + enterprise delivery

Status: **COMPLETE**
Completed: 2026-10-06 / 2026-10-07 UTC

Phase 1 converts the Phase 0 rating foundation into a usable second-look product
surface. It adds incumbent attribution, enterprise ingestion adapters, a deployed
authenticated data plane, and a human review control room.

## Delivered

### 1. Incumbent Challenge Engine

`freight/incumbent_challenge.py` freezes the incumbent-known universe before
challenger attribution. It distinguishes:

- `CHALLENGER_ONLY`;
- `INCUMBENT_KNOWN`;
- `SUPPRESSED`;
- `REVIEW`.

Incumbent findings, automatic/pre-existing credits, open claims and known disputes
can therefore receive credit before RecoveryOS measures net-new candidate value.
Duplicate challenger economic identities fail to REVIEW rather than being counted
twice. Only `CHALLENGER_ONLY` candidates carry nonzero net-new candidate cents.
Candidate value remains separate from human confirmation, external authorization,
claim state, settlement and recovered cash.

### 2. Enterprise adapters

`freight/enterprise_adapters.py` provides:

- canonical API-record normalization;
- SFTP manifest verification against exact accepted SHA-256 receipts;
- bounded X12 envelope parsing;
- explicit X12 field mapping profiles;
- X12 invoice projection without hidden transaction semantics.

Transport metadata never grants commercial authority.

### 3. Deployed RecoveryOS application

Deployed application:

- https://freight-recoveryos.floot.app

The Phase 1 application has:

- email/password authentication;
- tenant memberships and tenant-scoped server queries;
- a managed PostgreSQL data plane;
- immutable evidence tables;
- composite tenant + object foreign keys;
- append-only human review dispositions;
- hashed ingest-only API keys;
- canonical population/record/incumbent/finding hash verification on import;
- import idempotency;
- an analyst control room with evidence, attribution and human review actions.

The application intentionally does not call a confirmed finding "recovered" money.
Settlement remains a later governed state.

### 4. Tenant isolation evidence

The deployed database schema enforces composite tenant/population and
tenant/finding foreign keys. A transaction-scoped negative test attempted to insert
a Freight record under tenant B while referencing tenant A's frozen population.
PostgreSQL rejected the insert with a foreign-key violation. The entire fixture was
rolled back.

This proves the tested database constraint, not a SOC 2 report or an external
penetration test.

### 5. Import integrity

The deployed import boundary rejects:

- non-FROZEN population imports;
- population manifest hash mismatch;
- record hash or scope mismatch;
- billed-total mismatch against canonical charge lines;
- incumbent snapshot hash/scope/source mismatch;
- findings without a frozen incumbent snapshot;
- findings linked outside the tenant/population;
- variance arithmetic mismatch;
- invalid net-new attribution;
- incumbent matter IDs not present in the frozen snapshot;
- challenge finding hash mismatch.

### Verification completed

- RecoveryOS TypeScript typecheck: **clean**.
- Floot project tests: **green**.
- Database cross-tenant negative constraint test: **PASS**.
- Production deployment: **live**.
- Phase 1 Python tests are wired into Freight CI in this change.

## Honest boundary

Phase 1 does not claim:

- production payment orchestration;
- TL/intermodal/air/ocean rerating parity;
- natural-language analytics;
- SOC 2 Type II or ISO 27001 certification;
- independent penetration-test evidence;
- competitor-beating volume or availability.

Those are Phase 2 / Phase 3 work.

## Remaining phases

- **Phase 2:** payment orchestration, TL/intermodal/air/ocean rating breadth, and
  natural-language analytics.
- **Phase 3:** external assurance and scale proof, including security
  certification work, penetration testing, large-scale reliability benchmarks,
  and the maintained competitor-supremacy matrix.

There are **2 phases remaining after Phase 1**.
