# Hunt 08 Referral — Android OB-USP transaction-envelope evidence

Date: 2026-09-20
Node: 08 — Protocol Moats
Status: STRONG SOURCE-PREDICTED EXPERIMENT FIXTURE; original end-to-end runtime NOT_RUN

## Finding

`TommieLin/SdtTR369-Public@bca4e3cc35bb862c01cf3776637c790e0dd0f2b7` is a low-attention Android/TR-369 integration that makes the OB-USP vendor-transaction boundary concrete rather than hypothetical.

### Explicit hypothesis

If an `allow_partial=false` USP Set contains two valid/writable parameters, parameter A invokes a Java/Android setter that mutates external state immediately, and later parameter B fails dynamically inside its valid setter, then the forked OB-USP core will return an Error and abort its internal DB transaction, but A's external Android side effect will remain unless the integration separately registered and correctly implemented OB-USP vendor transaction hooks or the setter itself stages/compensates the change.

## Discovery modes

1. **Direct integration search:** looked for deployed/firmware-shaped OB-USP integrations and transaction hooks rather than another generic USP engine.
2. **Code-level boundary trace:** followed `allow_partial=false` handling through OB-USP transaction start/abort, vendor setter registration, JNI bridge, Java callback and concrete Android setters.
3. **History/ecosystem check:** verified the public snapshot's current HEAD/history and compared its integration surface with upstream OB-USP vendor transaction APIs.
4. **Negative branch:** inspected an ASUSWRT-Merlin OB-USP vendoring path, but its platform vendor source is partly source-stripped/prebuilt; no transaction-hook conclusion is defensible there.

## Specialist passes

### CODE INSPECTOR

- Forked `handle_set.c` processes `allow_partial=false` by validating/resolving the requested updates, then starting `DM_TRANS_Start()`, applying setters, and invoking `DM_TRANS_Abort()` on failure.
- Forked `dm_trans.c` rolls back the internal Agent database and calls external `start_trans_cb` / `commit_trans_cb` / `abort_trans_cb` only when those vendor hooks are registered.
- Repository-wide search for `USP_REGISTER_CoreVendorHooks` finds only the declaration and core implementation; no integration call site was found. Search for `start_trans_cb` likewise finds core/API definitions, not an integration assignment.
- `vendor/vendor.c` registers set hooks and routes writes through `SK_TR369_API_SetParams`; JNI forwards this synchronously into Java `OpenTR369CallbackSet` / the accessor layer.
- Concrete Android setters perform immediate side effects. Examples include Wi-Fi enable/disable through `WifiManager.setWifiEnabled(...)`, LAN/static-IP mutation through `NetworkUtils.setStaticIP(...)`, Settings/System writes, and other device actions.
- `InterfaceX.SK_TR369_SetWifiEnable()` is a valid registered setter with an environment-dependent dynamic failure path: it returns the Android API result when toggling Wi-Fi and returns false when the requested state is already current or the value is otherwise not handled. This shows that a later valid setter can fail at the adapter layer rather than only at pre-validation.

### SCHEMA / TEST VALIDATOR

- `allow_partial` is consumed by the forked OB-USP Set handler, so the transaction intent reaches the protocol core.
- No source-visible integration regression test was found that exercises a multi-parameter `allow_partial=false` request across Java/Android external side effects and a later setter failure.
- The fixture MUST use two paths that resolve and pass pre-validation. An unknown or non-writable second path is a bad probe because OB-USP can reject it before A mutates state.

### ECOSYSTEM / HISTORY

- Candidate HEAD inspected: `bca4e3cc35bb862c01cf3776637c790e0dd0f2b7` (2024-04-02, README update); public history is very small and old. Treat this as a low-attention architecture/negative-control fixture, not evidence of current commercial deployment.
- README describes Android porting around an OB-USP-based Agent and shows annotation-driven TR-369 get/set integration.

### COMMERCIAL ANALYST

Buyer: CPE / Android-TV / gateway OEM integration lab or ISP device-certification team.
Pain: an atomic USP configuration request can report failure while the underlying OS/device has already changed.
First paid wedge: fixed-scope **USP Vendor Adapter Transaction Integrity Pre-FAT** — plant a late valid-setter failure and compare protocol response, Agent DB state, external/persistent device state, live state and restart state.
Money path: reduce escaped configuration drift, lab debugging and field rollback incidents during TR-369 migration/integration.

### RED-TEAM / VERIFIER

Objections checked:
- **Not proof of a shipped defect.** Correct. Public repo is an old snapshot/reference-style Android integration.
- **Absence of `USP_REGISTER_CoreVendorHooks` might miss hidden/non-indexed integration code.** Repository-wide indexed search plus inspected vendor/JNI path found no registration, but this remains source-visible evidence, not a runtime assertion.
- **Immediate setters might internally compensate/stage state.** Some could; therefore each commercial probe must measure external state directly and use a controlled late failure.
- **OB-USP core itself is not broadly at fault.** Correct. Its transaction API explicitly provides vendor transaction hooks; this finding is about the integration envelope.
- **Unknown-path failure is sufficient.** Rejected. Pre-validation can stop before the first setter. Use a later valid setter that fails dynamically.

Verifier verdict: **STRONG as an EXP-008 negative-control / adapter-envelope fixture; NOT a broad conformance verdict; runtime NOT_RUN.**

## Authority

Current Broadband Forum USP 1.5 R-SET.1 states that with `allow_partial=false`, the entire Set is a single operation; failure must return Error and the state of the Data Model must not change. Use that as the protocol-level invariant, while separately measuring external adapter/device state.

## Score

Candidate repo as a WATCH/fixture source: **22/30**
- A Speed to first revenue: 3
- B Customer value ceiling: 3
- C Build/domain compression: 4
- D Rarity/technical advantage: 4
- E Evidence/reproducibility: 4
- F Rights/deployment clarity: 4

## Experiment packet

`USP-ANDROID-ADAPTER-ROLLBACK-PROBE`

1. Run on a controlled Android image/device/emulator with the candidate adapter or an equivalent adapter preserving its immediate-setter structure.
2. Choose A as a valid writable parameter with directly observable external state (for example Wi-Fi enable or a test Settings-backed parameter).
3. Choose B as a second valid/writable parameter whose setter failure can be deterministically injected after A succeeds. Do not use an unknown path.
4. Send one `allow_partial=false` Set with both updates `required=true`.
5. Capture: USP Error/Response; OB-USP DB/model state; external Android state immediately after failure; state after a later unrelated Set; state after process/device restart.
6. Repeat with explicit vendor start/commit/abort hooks that stage/restore A.
7. Expected discriminator: without transaction-aware adapter, `Error + leaked A` is source-predicted; with correct hooks, `Error + A reverted` should satisfy the atomicity invariant.

## Negative knowledge

- Vendored OB-USP in firmware trees is not automatically evidence of adapter atomicity; vendor source may be omitted/prebuilt.
- Core DB rollback does not prove device/OS side effects rolled back.
- Transaction hooks being available in OB-USP does not prove an integration registered or correctly implemented them.
- A protocol-error reply alone is an inadequate acceptance oracle; external state and restart state must be read independently.

## Knowledge-to-value handoff

- **Capability delta:** CAP-014 gains a real integration-shaped example of the protocol-core ↔ adapter-transaction boundary.
- **Graph edge:** `OB-USP vendor hooks -> Android immediate setter integration -> USP-VENDOR-ROLLBACK-PROBE -> EXP-008`.
- **Radar signal:** strengthens lifecycle-aware virtual commissioning: defects emerge at ownership boundaries, not just parser/protocol layers.
- **Experiment impact:** execute one controlled late-failure adapter probe before collecting another USP engine.
- **Commercial impact:** stronger USP Pre-FAT wedge for OEM/ISP labs: detect "failed atomic Set but device changed" defects.
- **Negative knowledge:** do not infer end-to-end atomicity from `DM_TRANS_Abort()` unless the external adapter participates in rollback.

## Exact next question

Can a controlled Android/OB-USP build reproduce `Error + leaked external A` with no vendor transaction hooks and eliminate the leak when start/commit/abort hooks are added, while the same neutral controller fixture remains unchanged?
