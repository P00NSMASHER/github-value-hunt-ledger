# Hunt 08 R20 — OB-USP vendor atomicity envelope

Date: 2026-09-20
Node: 08 — Protocol Moats
Target: CAP-014 / EXP-008 USP transaction-integrity corpus

## Summary
The existing `USP-SET-TRIANGLE` should not label `BroadbandForum/obuspa` unconditionally rollback-safe. At current HEAD `59028beba21471d19bd3842ef2632ceb6ca8c7fc`, OB-USP correctly implements `allow_partial=false` around its own transaction layer, but rollback of **external side effects performed by non-grouped vendor parameter setters is contingent on the vendor integration registering and correctly implementing the optional `start_trans_cb` / `commit_trans_cb` / `abort_trans_cb` hooks**.

This creates a high-information negative-control fixture: two registered non-grouped vendor parameters, both required, same USP Set, first setter mutates an external backing store and succeeds, second setter fails at runtime. With vendor transaction hooks intentionally absent, source tracing predicts OB-USP returns an Error and aborts its internal DB transaction, while the first external effect remains. With a properly transactional vendor adapter, the same fixture should leave external state unchanged.

This is not evidence that OB-USP core is broadly nonconformant. The public API exposes vendor transaction callbacks precisely to let an integration provide transactional semantics. The finding is an **integration-boundary acceptance requirement**: a pre-FAT harness must test the actual vendor adapter, not infer device atomicity from OB-USP core conformance alone.

## Explicit hypothesis
If two `USP_REGISTER_VendorParam_ReadWrite()` parameters remain `NON_GROUPED`, and the first `set_cb` mutates external state while the second `set_cb` returns a required-parameter failure, then `allow_partial=false` will only restore all-or-nothing semantics if the vendor integration has supplied a functioning abort transaction callback or otherwise stages its external mutation.

## Evidence inspected

### 1. Set-message control flow — IMPLEMENTED
At `src/core/handle_set.c`:
- `Grouped_HandleSet()` preserves `Set.allow_partial` and routes `false` to `ProcessSet_AllowPartialFalse()`.
- `ExpandSetPathExpression()` passes each `UpdateParamSetting.required` bit into `GROUP_SET_VECTOR_Add()`.
- `ProcessSet_AllowPartialFalse()` rejects a Set spanning more than one group ID because cross-service rollback cannot be guaranteed.
- It starts `DM_TRANS_Start()`, executes `GROUP_SET_VECTOR_SetValues()`, aborts on the first required failure, and commits only when all required parameters succeed.

### 2. Same-group gate and mutation order — IMPLEMENTED
At `src/core/group_set_vector.c`:
- `GROUP_SET_VECTOR_AreAllPathsTheSameGroupId()` explicitly documents that cross-owner Sets are rejected because rollback across a USP Service cannot be guaranteed.
- A pre-existing path/permission failure on any required parameter blocks mutation before `SetValues()` starts.
- For `NON_GROUPED` parameters, `GROUP_SET_VECTOR_SetValues()` calls `DATA_MODEL_SetParameterValue()` sequentially and stops when a required runtime set fails.

Important probe design consequence: an *unknown path* is a poor negative for this seam because it is discovered before mutation. The second parameter must be a valid writable registered parameter whose setter fails during execution.

### 3. Vendor parameter semantics — IMPLEMENTED
`USP_REGISTER_VendorParam_ReadWrite()` registers a read-write parameter that is explicitly **not persisted in the USP Agent database** and stores the vendor `get_cb` / `set_cb` callbacks.

`DATA_MODEL_SetParameterValue()` dispatches a vendor parameter to `SetVendorParam()`. `SetVendorParam()` calls the vendor's `set_cb(req, value)` immediately. Only after the set succeeds does the core add the change to its transaction-notification vector. Therefore the external side effect can occur before the Set request reaches its final commit/abort decision.

### 4. Transaction boundary — IMPLEMENTED
At `src/core/dm_trans.c`:
- `DM_TRANS_Start()` always opens the OB-USP internal database transaction, then invokes `vendor_hook_callbacks.start_trans_cb` only if the callback is non-NULL.
- `DM_TRANS_Commit()` invokes optional `commit_trans_cb`, then commits the internal database.
- `DM_TRANS_Abort()` invokes optional `abort_trans_cb` only if non-NULL, then aborts the internal database.

No generic old-value restoration is performed for a non-grouped vendor `set_cb`. Thus external rollback is integration-owned when the vendor layer performs immediate external effects.

### 5. Public vendor API / schema boundary — VERIFIED
`src/include/usp_api.h` exposes:
- `dm_vendor_start_trans_cb_t`
- `dm_vendor_commit_trans_cb_t`
- `dm_vendor_abort_trans_cb_t`
- the three callbacks in `vendor_hook_cb_t`
- `USP_REGISTER_VendorParam_ReadWrite()`

The Quick Start vendor-hook example zero-initializes the callback structure and sets unrelated hooks without transaction callbacks, demonstrating that these callbacks are optional at the API surface rather than automatically supplied by the core.

### 6. Authority comparator — VERIFIED
Current Broadband Forum USP specification, section 7.4.6.2, requirement R-SET.1 states that with `allow_partial=false`, the entire Set is one operation; if any Object update fails, the message fails and **the state of the Data Model MUST NOT change**.

Current TP-469 repository HEAD is `5d53f5280b2a90ea0040887e62828c7b7369a240` (release 1.4.1, 2026-01-06). TP-469 test 1.15 remains an explicit negative-control Set case for `allow_partial=false` with a required failure and checks post-operation state rather than only the returned error. This reinforces that rollback must be measured as a state invariant.

### 7. History / operational evidence — VERIFIED
OB-USP current master remains `59028beba21471d19bd3842ef2632ceb6ca8c7fc` as of this run (v11.0.7, 2026-07-24), so the inspected code is not a stale pin.

Issue #131 (April 2025) independently confirms that OB-USP's data-model mutation machinery expects explicit transaction context. Maintainer Richard Holme advised wrapping a core mutation in `DM_TRANS_Start()` / `DM_TRANS_Commit()` and noted that `usp_api.h` is the supported vendor-layer API. This does not prove the planted vendor rollback case, but it corroborates that transaction ownership is an explicit integration concern.

A repository-wide search for `abort_trans_cb` surfaced the transaction implementation and public API declaration but no dedicated regression test exercising an external vendor setter rollback under `allow_partial=false`. Absence of such a test is negative evidence only; it is not proof of failure.

## Specialist passes

### CODE INSPECTOR
Traced `Set.allow_partial` -> `ProcessSet_AllowPartialFalse` -> group ownership check -> `DM_TRANS_Start` -> `GROUP_SET_VECTOR_SetValues` -> `DATA_MODEL_SetParameterValue` -> vendor `set_cb` -> required failure -> `DM_TRANS_Abort`.

### SCHEMA / AUTHORITY VALIDATOR
Verified the transaction hooks and vendor parameter API in `usp_api.h`; compared behavior to current USP R-SET.1 and current TP-469 negative-state verification.

### HISTORY VALIDATOR
Confirmed the inspected OB-USP pin is current HEAD and inspected path history / issue history. The design is long-lived, not a stale fork artifact.

### COMMERCIAL ANALYST
The economically useful deliverable is not “OB-USP has a bug.” It is **USP Vendor Adapter Transaction Integrity Pre-FAT**: prove that a specific CPE/OEM integration maintains all-or-nothing semantics across the core database and the device's actual configuration backends.

### RED-TEAM / VERIFIER
Attempted to falsify the leak hypothesis:
1. **Could a later unknown path fail only after the first mutation?** No. OB-USP pre-detects required path/permission failures before mutation. Therefore the second failure must occur inside a valid parameter setter.
2. **Could the core automatically restore the first vendor value?** No restoration path was found. `DM_TRANS_Abort()` rolls back the internal DB and calls the optional vendor abort hook if registered.
3. **Could non-grouped vendor parameters fail the same-group gate?** No. `USP_REGISTER_VendorParam_ReadWrite()` creates ordinary non-grouped vendor parameters; multiple such parameters share the `NON_GROUPED` ownership class and can proceed through the same transaction.
4. **Could correct vendor hooks make the hypothesis disappear?** Yes, and that is the point. A correctly staged/rollback-capable adapter should pass. The fixture is an adapter acceptance test, not a universal OB-USP condemnation.
5. **Does source inspection equal runtime proof?** No. Original-package execution of this exact planted vendor adapter was not available in the current runtime. Verdict remains source-predicted until executed.

VERIFIER VERDICT: **STRONG experiment-design correction / acceptance fixture; NOT runtime-proven and NOT a broad OB-USP conformance failure.**

## Proposed probe — `USP-VENDOR-ROLLBACK-PROBE`
Create two registered `NON_GROUPED` vendor read/write parameters backed by a tiny synthetic external store:
- `Device.Test.Atomic.A` — setter immediately writes external `A` and returns success.
- `Device.Test.Atomic.B` — setter returns a deterministic USP error when sent sentinel value `FAIL`.

Initial external state: `A=old`, `B=old`.

Send one neutral-controller Set:
- `allow_partial=false`
- `A=new`, `required=true`
- `B=FAIL`, `required=true`

Run two adapter modes:

### Mode 1 — no vendor transaction callbacks
Predicted source-level result:
- wire: USP Error
- OB-USP internal DB: aborted
- external A: **new** (leaked side effect)
- external B: old
- restart state: depends on synthetic backend persistence, but if external store is persistent the leak survives

### Mode 2 — real start/commit/abort callbacks
Implement staging or a compensating rollback inside the synthetic adapter.
Predicted result:
- wire: USP Error
- external A: old
- external B: old
- restart state: old/old

The strongest proof is a differential over the same OB-USP core with only the vendor transaction integration changed.

## Impact on `USP-SET-TRIANGLE`
Refine the matrix from:
- OB-USP = rollback-safe
- ac-client = reject-but-persist
- Caretaker = accept-invalid-path

to:
- **OB-USP internal DB / transaction-aware adapter = rollback-capable**
- **OB-USP immediate-effect vendor adapter without transaction callbacks = predicted reject-but-leak integration negative**
- ac-client = source-predicted reject-but-persist/deferred-activation path
- Caretaker = source-predicted accept-invalid-path negative control

This makes the corpus more useful because it distinguishes core protocol semantics from device-adapter semantics.

## Score / retention
No new repository score. `BroadbandForum/obuspa` remains a strong comparator. This result changes the acceptance boundary, not the repository's overall value.

Fixture value: A4 / B5 / C5 / D5 / E4 / F5 = **28/30 experiment component**, with E capped because the exact planted adapter has not been run end-to-end.

## Capability delta
CAP-014 gains a vendor-adapter transaction boundary: protocol rollback must be verified across the agent core **and** actual configuration backend, not inferred from the agent's internal database transaction.

## Graph edge
`OB-USP vendor transaction hooks` -> strengthens `USP-SET-TRIANGLE` -> strengthens EXP-008's state/lifecycle observation contract.

## Radar signal
Lifecycle-aware virtual commissioning increasingly depends on tracing side effects across software ownership boundaries: protocol core, vendor adapter, persistent configuration store, applied runtime state and restart state.

## Experiment impact
Add `USP-VENDOR-ROLLBACK-PROBE` to the existing neutral-controller USP corpus before searching another implementation. Record wire response, vendor backing state, OB-USP DB state where applicable, live state, and restart state.

## Commercial impact
First paid wedge: **USP Vendor Adapter Transaction Integrity Pre-FAT** for CPE OEMs and ISP device labs. It can catch a class of integration defect where the USP agent reports a failed atomic Set while the device backend has already changed, creating configuration drift or delayed activation after reboot/reload.

## Negative knowledge
- Do not describe OB-USP as unconditionally rollback-safe without qualifying the vendor adapter.
- Do not use an unknown parameter as the planted late failure; OB-USP detects it before mutation.
- Do not treat internal SQLite rollback as proof that Wi-Fi/system/vendor backends rolled back.
- Do not treat availability of transaction callbacks as proof the OEM integration registered or correctly implemented them.
- Do not infer broad standards nonconformance from this seam until the exact integration is executed and the authoritative customer/profile boundary is known.

## Search policy update
Candidate reusable lesson: **TRANSACTION CORE -> ADAPTER SIDE EFFECT -> ABORT HOOK -> RESTART STATE TRACE**. When protocol software claims atomic operations but delegates writes to vendor/plugin callbacks, trace transaction semantics across the plugin boundary and deliberately test both transaction-aware and immediate-effect adapters. Keep candidate-only until a second distinct protocol task or Hunt 15 promotes it.

## Next highest-value question
Can the exact two-vendor-parameter planted adapter be executed against OB-USP v11.0.7 in both callback modes, proving whether missing vendor transaction hooks produce `Error + leaked external A` while a transactional adapter preserves the R-SET.1 no-state-change invariant?
