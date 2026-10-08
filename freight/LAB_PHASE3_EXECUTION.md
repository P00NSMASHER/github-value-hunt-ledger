# RETALLY Phase 3: Integration candidate and simulated founding pilot

**Scope:** Research-only, no production deploy or PR merges. Branch stacks on #288, #286, #284 and #279. The original 26 findings remain OPEN_UNVERIFIED. The 2 research gate bugs are not application fixes.

## Deliverables and what is actually executed

- `lab_phase3_economics.py` implements the **real flagship commercial model**: $0 upfront bounded audit and a configurable contingency rate read from `commercial_terms.py`, 30% working default. It models unvalidated probabilities, reversals, recovery delays, labor and acquisition costs. Negative expected margins and break-even candidate value remain visible. This replaces **neither** a signed customer contract nor the optional fixed-fee forensic offer.
- `lab_phase3_integration.py` executes the **existing** Python rating engine (Lab 1), canonical source checks (Lab 4), `SettlementStore` and independent financial verifier (Lab 5), contingency model (Lab 8), and temporary-copy tamper replay (Lab 11) in one genuine function-call chain with fictional input. The other nine laboratory engines remain explicitly BLOCKED in this chain. No fake success count is used for work routing.
- `lab_phase3_trust.py` adds an Ed25519 public-key evidence admission port with tenant/role/time bounds and fail-closed signature verification. Local tests use **ephemeral test keys**, not buyer/carrier/bank authority. Authentic issuer enrollment, contracts, and externally controlled credentials remain a prerequisite.
- `lab_phase3_simulated_pilot.py` executes a **three-customer fictional** founding pilot. Includes a retrospective partially recovered credit with a later reversal, a no-recovery positive control, and a prolonged uncertain dispute. Real customers secured, actual customer funds and actual RETALLY cash are all **zero**.
- `lab_phase3_console.py` generates a completely local, self-contained HTML operator report with simulated pilot, exact model margins, 26 historical open findings, and 49 routed-but-unexecuted work items. It has searchable, sortable laboratory queues. No hosted data or services.
- `lab_phase3_release_manifest.py` enforces source/file presence, the 28 finding IDs and 26 OPEN statuses, and ancestry of four frozen PR heads, producing a non-production research receipt.
- The isolated Floot RecoveryOS **unpublished preview** also contains `helpers/recoveryPaymentReplay.tsx`, eight Jasmine cases, and an endpoint guard integrated into `payment_event_POST.ts`. TypeScript typecheck and selected suites passed. It was **not published**, nor tested on authentic provider callbacks or production DB.

## Assurance gates

Before accepting any financial proof, require independently controlled buyer entitlements, signed historical fee documents, carrier response identity, bank/customer credit posting, and appropriate evidence timestamp windows. Self hashes and local HMAC fixture keys are insufficient. Never claim real revenue from synthetic results.

## Release sequence

All four earlier PRs are open stacked drafts. Keep this PR a draft until exact-head acceptance, code review, DB/staging test isolation, license audit and owner approval. **Do not auto-merge this PR, edit running schedules, use real customer records or perform external carrier/payment actions.**

Run in repository with Python 3.11 and the pinned project CI requirements plus `cryptography==46.0.4`:

```bash
PYTHONPATH=. python -m unittest -v freight.test_lab_phase3_economics freight.test_lab_phase3_trust freight.test_lab_phase3_real_chain freight.test_lab_phase3_simulated_pilot freight.test_lab_phase3_release_manifest freight.test_lab_phase3_console
PYTHONPATH=. python -m freight.lab_phase3_release_manifest --root . --check-git-ancestry
PYTHONPATH=. python -m freight.lab_phase3_console --output /tmp/retally-phase3
```

## Unresolved completion dependencies

A fully segregated hosted Floot RecoveryOS staging tenancy and its database still need to be established, and real provider integration must be tested without touching published production. Nine lab adapters beyond the executable five-lab chain need source-safe implementation. The simulated pilot is a rehearsal, not independent buyer evidence. No historical finding may be closed from these artifacts without its exact original affected-code reproduction and independently reviewed closure receipt.
