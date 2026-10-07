# RecoveryOS Phase 2 — payment orchestration, multimode rating, governed analytics

Status: **COMPLETE**
Completed: 2026-10-07 UTC

Phase 2 expands RecoveryOS from LTL/parcel second-look recovery into a broader
freight intelligence and payment-orchestration platform while preserving the
existing evidence standard: candidate value, human-confirmed findings,
authorized instructions, provider events and settled money remain distinct.

## Delivered

### 1. TL / intermodal / air / ocean rating breadth

The canonical freight schema now supports the mode-specific facts required by
the Phase 2 engines, including equipment/container identity and chassis days.

The authority compiler and deterministic rating engine now support all six
declared modes:

- PARCEL;
- LTL;
- TL;
- INTERMODAL;
- AIR;
- OCEAN.

Phase 2 adds:

- TL flat or per-mile linehaul, minimums, fuel and accessorials;
- intermodal base + mileage, fuel, chassis-day charges and accessorials;
- air actual-vs-volumetric chargeable weight, per-kg rates, minimums, fuel,
  security charges and accessorials;
- ocean container rates or W/M rating, minimums, fuel and accessorials.

Missing distance, chassis facts, air dimensions, ocean dimensions or container
type fail to review instead of being silently guessed. Unverified authority can
still calculate an estimate but cannot produce an auto-rated result.

### 2. Provider-neutral PaymentOS

`freight/payment_orchestration.py` and the deployed RecoveryOS application
implement the governed lifecycle:

PREPARED -> AUTHORIZED -> SUBMITTED -> ACCEPTED -> SETTLED -> REVERSED

with FAILED as an explicit terminal provider state where applicable.

Important boundaries:

- a payment instruction requires evidence-bound finding proofs;
- human authorization is separate from preparation;
- provider events require authorization;
- event amounts must match the authorized instruction;
- invalid state jumps are rejected;
- event chronology is enforced;
- provider events are hash chained;
- SETTLED is the only state that produces settled cents;
- a later REVERSED event returns settled cents to zero.

The production Postgres data plane also enforces authorization amount, provider
event amount, prior authorization and lifecycle-transition constraints at the
database layer, in addition to application checks.

RecoveryOS orchestrates evidence and state. It does **not** claim to be a bank,
custodian or payment network.

### 3. Governed natural-language analytics

The deployed application now includes **Ask RecoveryOS**.

The natural-language layer uses a low-cost typed classifier to route a user's
question to one allowlisted analytic intent. The classifier receives the
question and metric catalog only. It does **not** receive customer freight rows,
payment rows or evidence documents.

All financial arithmetic and aggregation runs deterministically against the
authenticated tenant's database records after intent selection.

Supported governed views include:

- overall recovery status;
- billed spend by mode;
- record counts by mode;
- candidate variance by category;
- challenger-only net-new value by category;
- findings by attribution state;
- latest human-confirmed finding count;
- payment lifecycle totals;
- currently settled payment value by provider.

Low-confidence routing fails closed and asks for a clearer analytics question.

### 4. Production RecoveryOS application

Production:

- https://freight-recoveryos.floot.app

Phase 2 adds:

- PaymentOS preparation and owner-authorization UI;
- payment lifecycle queue;
- ingest/API path for externally observed provider events;
- database-backed payment state;
- Ask RecoveryOS natural-language analytics;
- responsive analyst UX for review, payments and analytics.

### 5. Verification completed

Application:

- TypeScript typecheck: **clean**.
- Floot tests: **green**.
- Recovery hash regression tests: **green**.
- Database negative tests confirmed:
  - mismatched authorization amount is rejected;
  - provider event without authorization is rejected;
  - invalid payment lifecycle jump is rejected.
- Phase 2 production publish executed against the existing RecoveryOS domain.

Repository:

- Phase 2 multimode rating regression tests cover TL, intermodal, air,
  containerized ocean and W/M ocean.
- Payment orchestration tests cover authorization gating, submission,
  acceptance, settlement, deterministic replay and reversal.
- Phase 2 tests are wired into Freight Commercial Contracts CI.

## Honest boundary

Phase 2 does not claim:

- direct custody of customer funds;
- a live bank/card/ACH/wire rail owned by Freight Recovery;
- universal carrier-contract coverage for every negotiated rule;
- SOC 2 Type II or ISO 27001 certification;
- independent penetration-test evidence;
- competitor-beating production volume, latency or availability.

Those proof obligations remain Phase 3.

## Remaining phase

- **Phase 3:** external assurance and scale proof: security certification work,
  independent penetration testing, large-scale reliability/throughput
  benchmarks, and the maintained competitor-supremacy matrix.

There is **1 phase remaining after Phase 2**.
