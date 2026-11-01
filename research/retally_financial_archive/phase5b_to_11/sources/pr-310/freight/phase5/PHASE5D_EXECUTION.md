# RETALLY Phase 5D: original D-07 proof and staged Customers B/C

**Source:** draft branch stacked upon Phase 5C PR #309. No merges, production deploys, customer contact, external payments or scheduled changes.

## 1. Original affected-source defect D-07

The original 2026-10-07 Unified Laboratory ZIP (SHA-256 `2dcfd16296454689a391fb76ac57e4a9282091c25d85134334b3c7eeeeafc93b`) was recovered from the user's prior locally mounted original file. It is *not* bundled into this GitHub PR.

Affected source: `RecoveryOS_Unified_Development_Lab/unified/staging.py`, original SHA-256 `36960d9ca245cdd43b61423718aa763102c901cdb8784cd46e5189d9ff7e983c`; `StagingTwin.act` previously read `kind,payload_json` when determining idempotent replay but omitted the `actor`. Both fictional `buyer` and `operator` are authorized for `MESSAGE`.

**Original exact failing reproduction:**
- buyer sends `MESSAGE` with key `SIM-REPLAY-D07`;
- operator retries the same `MESSAGE`, payload and key;
- the original code incorrectly replies `IDEMPOTENT_REPLAY`. The new original counterexample test failed because `Rejected` was not raised.
- same-actor idempotent retry was a passing positive control.

**Focused root-cause repair:** select `actor` in the persisted idempotency row, and require `previous['actor']==actor` before returning an idempotent replay. Different authorized actor now receives `IDEMPOTENCY_CONFLICT`. The same original test with the patch passed, 2/2 tests; full original laboratory suite passed 62/62. The prior Phase 2 patched ZIP (SHA-256 `8e0abb53632b82a6228bbf8fe5dc35da14b52ba9b4e1edfb985f62bf96c02e9d`) already contains actor-bound replay and separately passed the exact same 2 tests.

Files: `phase5d_d07_original.patch`, `test_phase5d_original_d07.py`, `phase5d_d07_offline_receipt.json`. Full original failing/passing logs and verified patch are additionally in the user-downloadable Phase 5D original-source repair package. GitHub CI **only verifies the recorded SHA/source-boundary metadata**, because original archive bytes are not in GitHub. It does **not** rerun the original counterexample inside CI.

**Closure classification:** `REPAIRED_IN_OFFLINE_RESEARCH_ONLY`. The historical D-07 status remains `OPEN_UNVERIFIED`, pending original finding's complete product/external actor controls. No actual production carrier actor authority was verified.

## 2. Actual unpublished Floot QA customer outcomes

Read-only QA isolation: `7257eaf3-a4d7-43db-9136-fe81e5df35bf`, PostgreSQL cluster `7694294930552894346`; production is `7693746749463444100` and was read-only. QA project remained unpublished.

Two **existing fictional founding-customer profiles**, not additional real customers:

- **Customer B (no recovery):** a BUYER-role, ephemerally Ed25519-signed fictional 30% historical contract was accepted by the Phase 5C QA financial endpoint, HTTP 200. A separately, correctly signed carrier-credit assertion without any linked actual handler `SETTLED` event was rejected, HTTP 400 `CARRIER_CREDIT_MISSING_HANDLER_EVENT`. A correctly signed fee invoice without verified customer cash was rejected, HTTP 400 `UNAUTHORIZED_FEE_INVOICE`. Read-only SQL: zero posted customer credits, zero fees, no recovery.
- **Customer C (high-effort, unattractive):** equivalent signed contract accepted; unsupported carrier credit and unsupported fee invoice both rejected, HTTP 400. Read-only SQL: zero posted credits, zero fees. The previous `lab_phase3_simulated_pilot` business model, using explicitly **assumed** labor/recovery/collection probabilities, supplies the negative expected margin and therefore the recommended scope reduction/stop. The actual hosted QA endpoint does **not** know customer dissatisfaction or freight tariff truth.

`phase5d_bc_qa_fixtures.json` contains read-only exported actual QA contract signatures, issuer public keys, zero financial summary and observed negative request outcomes. `test_phase5d_bc_qa.py` verifies the actual cryptographic signatures and no-cash boundaries, plus the **existing** economic model. No private signing keys are committed.

**Limits:** Customer A's richer 400/600 cent partial-credit/reversal/refund path remains in Phase 5C. Customers B/C tested actual QA financial document handlers, but their full invoice/tariff and behavioral simulations are still Python-domain models, not hosted freight pricing acceptance. Actual company revenue = $0. All 26 historic finding IDs remain unchanged and OPEN_UNVERIFIED.

## 3. Release status

Phase 5D exact-head CI covers synthetic signed contracts, no-recovery billing rejection evidence, the previous fictional Phase 5C oracle and original-finding register. The full original D-07 file-level before/after result is independently archived and has a reproducible local test. Production launch remains blocked by authenticated external buyer/carrier/bank records, production-equivalent authorization, and per-finding formal closure.

No production writes or privileged provider activity occurred.
