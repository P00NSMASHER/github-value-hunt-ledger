# Hunt 08 referral R15 — SECS/GEM duplicate-S2F15 history lock

Date: 2026-09-20
Lane: Node 08 — Protocol Moats
Status: EXP-008 evidence refinement; no new repository promoted

## Explicit hypothesis
The currently predicted duplicate-ECID S2F15 split is not a transient bug at stale revisions but a durable semantic-policy mismatch between the two pinned/current implementations. If both source lineages are stable and a recent real-equipment profile independently chooses one side, the highest-value next action remains one duplicate-specific wire execution rather than another generic SECS/GEM search.

## Discovery / verification modes
1. SOURCE + SCHEMA TRACE — trace S2F15 decode/validation/mutation/reply paths in both pinned implementations.
2. COMMIT-HISTORY ARCHAEOLOGY — determine when each relevant behavior entered and whether later upstream revisions changed it.
3. TEST TRACE — verify the nearest exercised positive/negative behaviors and identify the exact missing duplicate-specific test.
4. OPERATIONAL-PROFILE CHECK — compare the edge case to a recent public equipment manual without treating that manual as universal SEMI authority.

## Specialist passes
- CODE INSPECTOR: parser/schema, handler, mutation order, reply path.
- HISTORY / PROVENANCE VALIDATOR: pinned revision versus current HEAD and path history.
- TEST INSPECTOR: closest S2F15 and Stream-9/T3 regressions.
- COMMERCIAL ANALYST: consequence for pre-FAT compatibility reporting.
- RED-TEAM / VERIFIER: attempt to disprove that the split is durable or operationally meaningful.

## Engine A — Dreamine.Gem
Canonical repository: https://github.com/CodeMaru-Dreamine/Dreamine.Gem
Pinned revision: `82604d6f03c1e95e0558de5c757989b27cd4a3d6`
Observed repository HEAD during this run: same pinned revision.

### Source / schema
- `Protocol/E30/E30WireCodec.cs`: `ReadEquipmentConstantUpdates()` parses the S2F15 list and then enforces ECID uniqueness. A repeated ECID raises `E30WireFormatException` with a duplicate-ECID malformed-message diagnostic before equipment-constant mutation.
- `Protocol/E30/E30EquipmentRouter.cs`: the router converts `E30WireFormatException` on an inbound primary into correlated S9F7. Normal S2F16 generation occurs only after successful parsing/staging and equipment-constant service execution.
- Therefore the duplicate request is source-predicted to leave EC state unchanged and emit S9F7 rather than reach normal S2F16 handling.

### Test evidence
- `tests/Dreamine.Gem.Tests/E30RouterLoopbackTests.cs` contains an actual TCP regression in which a malformed W-bit request produces correlated S9F7 and the original transaction still expires with `SecsTransactionTimeoutException`. This verifies the key liveness mechanism — correlated Stream-9 does not itself resolve the outstanding application transaction — although the regression is not duplicate-S2F15-specific.
- The same loopback suite exercises multi-item S2F15 validation with a valid first item plus invalid later item and verifies no partial mutation, supporting all-or-nothing behavior for rejected batches.

### History evidence
- Current repository HEAD is the pinned revision `82604d6...`; no newer upstream revision supersedes the inspected behavior.
- `Protocol/E30/E30WireCodec.cs` history traces the E30 codec to commit `422cefcd047f98044e302859abee3d98c803202c` (2026-08-12, `Add E30 derived profile and TCP demo`). The duplicate-as-format-error policy is therefore part of the initial frozen E30-derived profile rather than a recent patch layered on top.
- Dreamine's own `docs/SEMI_REQUIREMENTS_TRACE.md` explicitly frames the implementation as an `E30-0611 derived subset profile v1`, not a standards-conformance/certification or external-interoperability claim.

Evidence label: duplicate rejection IMPLEMENTED; S9F7 + unresolved-W-bit/T3 mechanism TESTED on an analogous malformed request; duplicate-specific wire execution NOT_RUN.

## Engine B — bparzella/secsgem
Canonical repository: https://github.com/bparzella/secsgem
Pinned revision: `59a5242d8672dad73367a0acd18088adf461404f`
Observed repository HEAD during this run: same pinned revision (2026-01-25).
Public license: LGPL-2.1-or-later.

### Source / schema
- `secsgem/secs/functions/s02f15.py` defines S2F15 as an ordered outer list of repeated `<ECID, ECV>` pairs and contains no uniqueness constraint.
- `secsgem/gem/equipment_constants_capability.py::_on_s02f15()` first validates every requested entry. If all are valid/in-range (`eac == 0`), a second loop applies every update sequentially via `_set_ec_value(...)`, then returns S2F16 with EAC 0.
- There is no duplicate-ECID guard in that path. Two valid entries for one ECID are therefore source-predicted to be applied in message order with the later value overwriting the earlier one.

### Test evidence
- `tests/test_gem_equipment_handler.py` exercises successful two-item EC updates, invalid ECID rejection, low/high range rejection, callbacks, and predefined constants.
- No duplicate-ECID regression was found in that test file.
- Existing tests therefore validate the surrounding path but do not upgrade duplicate-specific last-value-wins to TESTED.

### History evidence
- Current repository HEAD is the pinned revision `59a5242...`; no later main-branch change supersedes it.
- Commit `6a53375a87542956c0cfd8b109fe570fd21fb4aa` on 2016-03-29 (`Only set equipment constants when all are valid`) explicitly changed the S2F15 handler into the same two-pass structure: validate the whole message first, then iterate the message to set each constant. That historical patch contains no duplicate filtering.
- Commit search shows the equipment-constant facility dates to March 2016; the key all-valid-then-sequential-update semantic has therefore existed for roughly a decade, while the modern 2024 refactor preserves the same shape.
- The latest repository revision continues to receive automated CodeQL runs successfully as of 2026-09-20. This is maintenance evidence, not duplicate-semantic test evidence.

Evidence label: repeated-list schema IMPLEMENTED; validate-all then sequential mutation IMPLEMENTED and historically stable; surrounding S2F15 behavior TESTED; duplicate-specific last-value-wins SOURCE-PREDICTED / original-package runtime NOT_RUN.

## Operational profile comparator
Public source: Despatch / ITW EAE, `Protocol Manager Pro SECS/GEM Owner's Manual`, Revision 2.1.0, dated 2025-05-30, available at https://manualzz.com/doc/85197703/despatch-protocol-manager-pro-secs-gem-owner-s-manual

Its S2F15 section states operationally that when the format is correct, ECIDs are valid, and ECVs are in range, S2F16 EAC=0 is returned; if duplicate valid ECIDs occur, the final ECV in the message becomes the value for that ECID. It separately says format errors produce S9F7, no constants change, and no S2F16 is sent.

This is strong profile-specific evidence that last-value-wins is a real deployed-equipment behavior. It is NOT universal SEMI standards authority and must not be used to label Dreamine non-conformant without an applicable licensed standard/customer profile.

## RED-TEAM / VERIFIER verdict
**STRONG HISTORY-STABLE DIFFERENTIAL HYPOTHESIS; DUPLICATE-SPECIFIC WIRE RESULT STILL UNVERIFIED.**

Attempts to disprove:
- Stale-revision explanation: rejected. Both inspected pinned revisions are current repository HEADs during this run.
- Recent regression explanation: weakened. secsgem's two-pass validation-then-sequential-mutation structure is directly visible in a 2016 semantic commit and persists in current source; Dreamine's duplicate rejection entered with its initial 2026 E30-derived profile.
- Schema-deduplication explanation on secsgem: rejected by the S2F15 data format, which is simply a repeated list and has no uniqueness declaration.
- Universal correctness claim: rejected. The Despatch manual establishes one current commercial profile, not the SEMI standard itself.
- Runtime confirmation: not achieved in this execution environment; the original pinned packages could not be materialized/executed here. Do not relabel the duplicate-specific prediction as TESTED.

## Commercial interpretation
Buyer: semiconductor equipment OEMs, fab automation/EAP/MES integration teams, retrofit/integration firms.
Painful problem: a host/equipment pair can disagree on an edge-case transaction in a way that changes not only ACK behavior but equipment state and requester liveness, surfacing late in FAT or production integration.
First paid wedge: fixed-scope `SECS/GEM Pre-FAT Profile Compatibility Report` using customer-authorized fixtures/profiles.
Deliverable for this case: same frozen S2F15 fixture sent to both engines, with recorded raw reply class, Stream/Function, System Bytes/header correlation, requester completion/T3, and deterministic readback of EC post-state.
Money path: reduce commissioning/debug time, avoid FAT rework and production-interface surprises.
Moat: growing corpus of profile-specific semantic edge cases plus lineage-independent execution evidence, not merely protocol parsing.

## Exact next experiment
Fixture: one W-bit S2F15 containing two individually valid entries for the same valid ECID, with two distinct in-range values A then B.

Record independently for each pinned engine:
1. whether request is accepted by the decoder;
2. any S2F16 and EAC;
3. any S9F7 and its embedded offending header/System Bytes;
4. whether the original W-bit transaction completes, aborts, or reaches T3;
5. EC value before request and deterministic readback afterward;
6. transport/session logs sufficient to reproduce the result.

Predictions to falsify:
- Dreamine: correlated S9F7, no S2F16, unchanged EC state, original request remains unresolved until T3.
- secsgem: S2F16 EAC0, no S9F7, final EC state B (last-value-wins), original request completes normally.

Only after an actual wire-level disagreement should a third independent engine be added, and only if adjudication changes the customer-facing conclusion.

## Candidate reusable search lesson — not promoted
**SEMANTIC DIFFERENCE → HISTORY-STABILITY CHECK**

WHEN TO USE: after source/test work predicts a meaningful semantic split between independent protocol implementations.
PROCEDURE: verify each pinned revision against current HEAD; trace the relevant file/semantic commit history; identify whether the behavior is original design, recent regression, or superseded; then seek an operational/customer profile for the same exact edge case before hunting another implementation.
WHY IT WORKED: it separated a durable profile-policy difference from a potentially transient stale-code discrepancy and reduced the value of another broad repository search.
FAILURE MODES: refactors may hide lineage; commit-message search can miss semantic changes; operational manuals are profile evidence, not universal standards authority.
NEXT IMPROVEMENT: validate this method in a second protocol lane before considering promotion to `SEARCH_SKILLS.md`.

## VALUE HANDOFF
- CAPABILITY DELTA: CAP-014 gains history-aware semantic differential evidence, reducing the chance that a pre-FAT finding is merely a stale-version artifact.
- GRAPH EDGE: strengthens EXP-008 from static source disagreement toward a tightly specified duplicate-S2F15 wire experiment.
- RADAR SIGNAL: reinforces RAD-007 — high-value virtual commissioning depends on profile-derived semantics, transaction liveness, post-state, and implementation independence.
- EXPERIMENT IMPACT: continue freezing generic SECS/GEM discovery; execution of the duplicate fixture remains higher information value than another library hunt.
- COMMERCIAL IMPACT: strengthens the case for profile-specific compatibility reporting rather than generic `SECS/GEM compliant` claims.
- NEGATIVE KNOWLEDGE: current-HEAD status and long-lived semantics still do not equal runtime proof or standards correctness; history stability must be kept separate from conformance authority.

## Next highest-value question
When the exact duplicate-ECID S2F15 W-bit fixture is executed end-to-end against both current pinned revisions, does the observed reply/liveness/post-state tuple match the history-stable prediction, and if it diverges from the customer's authoritative profile, is the difference reproducible enough to become a paid pre-FAT defect report?
