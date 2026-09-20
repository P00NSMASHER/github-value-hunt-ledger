# Hunt 08 referral — USP SET atomicity / latent configuration drift

Date: 2026-09-20
Lane: Protocol Moats / TR-369 USP / OpenWrt
Source candidate: `optim-enterprises-bv/ac-client@132c20aacf50911d3e3ecb5fb61033c400b3876c`
Status: **STRONG EVIDENCE DELTA on an existing WATCH candidate; not a conformance oracle**

## Hypothesis
A low-attention current OpenWrt USP agent can contribute unusually valuable real-device semantics to CAP-014 / EXP-008, but adversarial tracing may expose a hidden transaction-boundary defect that its self-described TP-469 compliance work does not test.

## Discovery modes used
1. **Low-attention current implementation search** — 0-star Rust TR-369/USP 1.3 OpenWrt agent, actively pushed in September 2026.
2. **Code-level side-effect trace** — USP SET decode -> flattening -> per-parameter dispatch -> UCI persistence -> deferred reload -> error response.
3. **Official test-plan comparison** — Broadband Forum `usp-test` v1.3.2 / TP-469 Set tests, especially 1.15.
4. **Commit-history archaeology** — field-failure commits from real BPI-R4/D50 devices plus the commit that introduced one-reload-per-SET behavior.

## CODE INSPECTOR
The repository's own protobuf describes `Set.allow_partial=false` as all-or-nothing and preserves each parameter's `required` bit. The actual Agent SET path does not preserve those semantics:

- `handle_incoming()` extracts a flat `Vec<(path,value)>` and calls `dm::set_params()`; it never forwards `allow_partial` or `required`.
- `extract_set_updates()` iterates `update_objs` and `param_settings` in request order, but keeps only path/value.
- `dm::set_params()` dispatches updates sequentially and returns immediately on the first error (`?`). There is no rollback/staging transaction.
- Multiple WiFi setters call `uci_set()` and `uci_commit("wireless")` immediately, then call `mark_wifi_reload()`.
- `wifi::flush_reload()` is called only after the *entire* update loop succeeds. If a later parameter fails, the function returns before `flush_reload()` and the pending flag remains set.
- The outer Agent then sends a generic USP Error (7200) without rolling back earlier UCI commits.

### Minimal falsifiable probe — `USP-SET-LATENT-DRIFT`
Initial state: SSID persistent UCI=`A`, running radio=`A`.

Send one SET with `allow_partial=false`:
1. valid `Device.WiFi.SSID.1.SSID = B`
2. later required invalid/unknown path

Source-predicted result at the pinned revision:
- first parameter is committed persistently (`B`), and reload is marked pending;
- second parameter fails;
- SET returns an Error;
- running radio can remain `A` because the reload flush is skipped;
- persistent UCI is already `B`;
- a later successful SET (even unrelated, because every successful `set_params()` calls `wifi::flush_reload()`) or reboot can activate the stale `B` unexpectedly.

This is more serious than ordinary partial application: the failure can create **time-shifted configuration activation** after the controller was told the SET failed.

A small extracted-control-flow micro-test reproduced this inferred state machine (`persistent=B`, `runtime=A`, `reload_pending=true` after the failed SET; later flush -> `runtime=B`). This is not original-package runtime evidence and must not be labeled TESTED against the repository binary.

## SOURCE / SCHEMA / TEST / HISTORY VERIFICATION
### Schema
`proto/usp-msg.proto` (USP Amendment 3 / 1.3) explicitly defines:
- `Set.allow_partial`: "When true, apply as many updates as possible; when false, all-or-nothing."
- `UpdateParamSetting.required`.
The runtime SET handler discards both fields before mutation.

### Official TP-469 comparator
Broadband Forum `usp-test` tag `v1.3.2` resolves to commit `a2fc32b216a13c3750f3906e26e2d84eb5d5852e`.
Test 1.15 (Set, allow_partial=false, multiple objects, required parameter fails in one object) requires the previously valid first object **not** to have its value updated. This directly supplies a deterministic acceptance oracle for the planted case.

### Repository tests
`src/usp/tp469/tests.rs` contains mostly structural/unit checks. Three integration tests are ignored because they require ac-server + OpenWrt/UCI. It has no observed multi-object SET rollback test.
The March 5 TP-469 report says 17 unit tests pass / 3 integration tests ignored, simultaneously calls SET complete and estimates 85% compliance while also stating 120+ scenarios remain and full conformance is future work. Treat it as self-reported status, not external certification.

### History
Commit `14343eab0dd594adcba14573850330f79f015dce` (2026-08-31) introduced one-radio-reload-per-SET after a live BPI-R4 exposed a 23-reload storm. Its diff explicitly says that on a later parameter error, early return deliberately avoids bringing radios up on a "half-applied config" — but the same diff leaves each prior `uci_commit()` intact and does not clear `WIFI_RELOAD_PENDING`. That commit therefore documents awareness of the half-applied state while preserving a latent persistent-state divergence.

Recent history otherwise raises the repository's technical value: commits describe and test real field failures involving 6 GHz security, mesh creation, NeighboringWiFiDiagnostic, TR-143 diagnostics, usteer/UCI persistence, and controller liveness. This makes the repo valuable as a field-derived acceptance-fixture source even though it should not be used as the correctness oracle.

## STANDARDS / ECOSYSTEM ANALYST
- Candidate targets USP 1.3, so the comparison was intentionally made to TP-469 `v1.3.2`, not only the newer 1.4.x test plan.
- Official TP-469 provides a clean all-or-nothing negative control for `allow_partial=false`.
- Existing lane assets `BroadbandForum/obuspa`, `OktopUSP/oktopus`, and `BroadbandForum/obuspa-test-controller` can serve as independent endpoints/controllers for a differential regression matrix.

## COMMERCIAL ANALYST
Buyer: CPE/AP OEMs, OpenWrt integrators, regional ISPs/MSPs migrating or validating TR-369/USP device management.
Pain: a failed management transaction can leave persistent configuration mutated but unapplied, then activate after a later unrelated SET/reboot, producing delayed outages/drift that are difficult to correlate to the original failed request.
First paid wedge: **OpenWrt USP Pre-FAT Transaction Integrity Report** — run customer-authorized Set/Get/Add/Delete fixtures, inject late required failures, compare response + persistent UCI + live radio + post-reboot state.
Money path: fewer field rollbacks, truck rolls, AP outages, provisioning escalations and migration regressions.
Build compression: ac-client contributes unusually rich current OpenWrt/TR-181/UCI failure semantics and hardware-derived fixtures; its defect itself supplies a high-value planted negative case.

## RIGHTS / PROVENANCE
Public license at the pinned revision is Business Source License 1.1, with production use limited to Aether absent a separate commercial license; change license is GPL-2.0-or-later on/after the stated change date. Under the user's standing assertion, separate commercial authorization exists for public repository-owned code. Do **not** extend that authorization to Broadband Forum standards text, trademarks, external services, or other independently owned materials.

Repository tree contains certificate/key filenames in package fixtures. Their contents were **not inspected, copied, validated, or treated as value** under the source-safety boundary.

## RED-TEAM / VERIFIER
Attempts to disprove the finding:
1. **Could UCI save rollback globally?** No evidence: the inspected WiFi setters perform `uci_set` + `uci_commit` per parameter before later parameters are attempted.
2. **Could runtime reload make it atomic?** No: reload is explicitly deferred until after the loop; early failure skips it, leaving persistent/runtime divergence.
3. **Could a later error clear the pending flag?** No clear-on-error path was found; `flush_reload()` clears via atomic swap only when called after a successful full loop.
4. **Could the protocol legitimately ignore allow_partial?** The candidate's own schema says false means all-or-nothing, and BBF TP-469 v1.3.2 test 1.15 requires the earlier successful object to remain unchanged when a later required update fails.
5. **Is this runtime-confirmed on the original package?** No. Original-package OpenWrt/UCI execution was not available in this run; classify the exact probe as **SOURCE-PREDICTED / OFFICIAL-TEST-PLAN-CONTRADICTED**, not runtime TESTED.

**VERDICT:** Strong enough to become an EXP-008 negative-control fixture and to sharpen the existing WATCH entry for ac-client. Not enough to call the product broadly nonconformant or to promote ac-client as a correctness oracle.

## Score / disposition
Repository remains **WATCH / strong fixture source**, approximately **25/30 as a component** (A4 B4 C5 D5 E3 F4). The atomicity defect prevents using it as a reference oracle, but the field-derived code/history materially increases its value as a source of adversarial migration/pre-FAT cases.

## VALUE HANDOFF
1. **CAPABILITY DELTA:** CAP-014 gains a concrete TR-369 transaction-integrity fixture that measures response + persistent desired state + live applied state + delayed activation.
2. **GRAPH EDGE:** EXP-008 should add `USP-SET-LATENT-DRIFT` beside the SECS/GEM semantic probes; this extends virtual FAT from protocol response matching into persistent/applied-state atomicity.
3. **RADAR SIGNAL:** Supports the emerging pattern that device-management moats live in side-effect/liveness semantics, not parser coverage.
4. **EXPERIMENT IMPACT:** Run the planted two-object `allow_partial=false` SET against ac-client, OB-USP-Agent and another independent USP agent/controller pair; read UCI/live state immediately and after a subsequent unrelated successful SET/reboot.
5. **COMMERCIAL IMPACT:** Stronger fixed-price wedge for OpenWrt/CPE firmware migration validation because it detects delayed configuration activation after an explicit failed management request.
6. **NEGATIVE KNOWLEDGE:** Never infer SET atomicity from a successful TP-469 checklist, a protobuf field, or a deferred-reload comment. Trace request flags through mutation, persistence, activation, error handling and later lifecycle events.

## Exact next question
Can `USP-SET-LATENT-DRIFT` be reproduced end-to-end on a real/synthetic OpenWrt UCI environment, and do OB-USP-Agent plus one unrelated agent preserve all-or-nothing state under the same TP-469 v1.3.2 fixture?