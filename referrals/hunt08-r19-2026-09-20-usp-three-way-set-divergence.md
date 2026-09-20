# Hunt 08 referral — USP Set three-way transaction divergence

Date: 2026-09-20
Lane: Protocol Moats / TR-369 USP / virtual pre-FAT
Primary new candidate: `awksedgreep/caretaker@08b309dd927f7f2c26d4aa42fec4533dceeb7cf1`
Comparators: `BroadbandForum/obuspa@59028beba21471d19bd3842ef2632ceb6ca8c7fc`; `optim-enterprises-bv/ac-client@132c20aacf50911d3e3ecb5fb61033c400b3876c`
Status: **STRONG three-way semantic divergence / Caretaker WATCH component, not a conformance oracle**

## Hypothesis
A third, unrelated USP Agent will make the existing `USP-SET-LATENT-DRIFT` fixture more informative by showing whether the defect is specific to the OpenWrt/UCI adapter or reflects a broader implementation tendency to preserve the protobuf shape while dropping `allow_partial` / `required` semantics at the mutation boundary.

## Discovery modes
1. **Direct domain search** for independent open-source TR-369/USP Agents.
2. **Code-level schema-to-side-effect trace** from USP protobuf -> Agent Set handler -> device-state mutation -> response construction.
3. **Official implementation comparator** using OB-USP-Agent transaction code and current-head history.
4. **Standards / conformance history archaeology** using Broadband Forum USP releases plus OB-USP issue #114 discussion around R-SET behavior.
5. **Low-attention search**: Caretaker is an active 0-star / 0-fork repository with a full device-side USP Agent plus simulator/controller surfaces.

## New candidate: awksedgreep/caretaker
Exact revision: `08b309dd927f7f2c26d4aa42fec4533dceeb7cf1` (v0.4.0 release, 2026-09-06)
Public license: MIT.
Attention: 0 stars, 0 forks at inspection time.

### CODE INSPECTOR
Caretaker's protobuf contains both fields required for the atomicity contract:
- `Set.allow_partial`
- `UpdateParamSetting.required`

But `Caretaker.USP.Agent.handle_set/3` never branches on `set.allow_partial` and never reads `setting.required`. Instead it iterates every `update_obj`, iterates every `param_setting`, and immediately calls `safe_set()` for each path/value. It always constructs a `SET_RESP` from the per-parameter result list.

The underlying `Caretaker.CPE.DeviceState.set/3` is even more permissive: it mutates the state immediately via `Agent.get_and_update`; its documentation says it **creates intermediate keys if needed**. `put_by_path()` recursively inserts missing map keys. Therefore an unknown TR-181 parameter path is not rejected by the generic DeviceState store — it can be materialized into the simulator state.

Source-predicted consequence for a controller request with `allow_partial=false` containing one legitimate update plus one required unknown parameter:
1. first update mutates state immediately;
2. second unknown path is also materialized successfully rather than rejected;
3. Agent returns SET_RESP rather than Error;
4. both changes remain in state.

This is a different failure class from ac-client. ac-client is source-predicted to reject the late bad path but retain an earlier UCI commit; Caretaker is source-predicted to accept and create the bad path; OB-USP is designed to fail the entire Set and roll back.

### TEST INSPECTOR
`test/caretaker/usp/agent_test.exs` contains one basic Set test that checks only that a normal single-parameter Set returns `SET_RESP`. No test was found for:
- `allow_partial=false` rollback;
- a required-parameter failure;
- unknown-parameter rejection;
- multi-object Set transactionality.

`test/caretaker/usp/proto_test.exs` verifies the builder can encode `allow_partial`, but this does not establish that the Agent honors it at execution time.

Original-package runtime execution was **NOT_RUN** in this environment because Elixir/Mix is not installed. This result therefore remains SOURCE-PREDICTED rather than TESTED.

### HISTORY INSPECTOR
TR-369 support entered Caretaker at commit `81df5e9f14210b62d47c6d6a10f5386e77c4c152` (2025-12-26, "tr369 support added").
Recent Agent fixes at `eca63d9fbae734138bd21819f33a1f7068fb6ceb` (2026-09-06) hardened DeviceState failure handling so Set/Add return USP error results rather than crash when the state store is unavailable, but did not add `allow_partial` / `required` transaction semantics. This suggests the current behavior is not an accidental transient edit introduced after the main Agent implementation; the transaction boundary simply has not been modeled.

### OFFICIAL COMPARATOR — BroadbandForum/obuspa
At current head `59028beba21471d19bd3842ef2632ceb6ca8c7fc`, `ProcessSet_AllowPartialFalse()`:
- rejects path-resolution errors before mutation;
- rejects an `allow_partial=false` Set spanning multiple USP Services when rollback cannot be guaranteed;
- starts a data-model transaction with `DM_TRANS_Start()`;
- applies values through `GROUP_SET_VECTOR_SetValues()`;
- calls `DM_TRANS_Abort()` if any required parameter failed;
- commits only after all required updates succeed.

`DM_TRANS_Start/Commit/Abort` wraps the internal database transaction and optional vendor transaction callbacks. The implementation therefore expresses the correct architecture for all-or-nothing behavior, with an important boundary: external vendor side effects are only truly atomic if the vendor transaction callbacks participate honestly.

### STANDARDS / CONFORMANCE HISTORY
Current Broadband Forum USP 1.5 states that with `allow_partial=false`, a failure to update any Object causes the entire Set to fail, returns an Error, and **the state of the Data Model MUST NOT change** (R-SET.1). It also clarifies rollback for Search Paths under R-SET.2c.

OB-USP issue #114 is useful archaeology rather than a defect finding. In Oct 2024 a conformance test temporarily expected SetResp for a failure case; an OB-USP maintainer initially acknowledged the mismatch. On 2024-12-09 the maintainer reported that after further BBF discussion the intended behavior was again an Error response and would be clarified in USP 1.5; the issue was then closed in Jan 2025. This aligns current OB-USP source with the later published authority.

## Three-way planted fixture — `USP-SET-TRIANGLE`
Use a rights-clean synthetic TR-181 model with an existing writable parameter `P1=A` and no parameter `P2_BAD`.

Send one Set:
- `allow_partial=false`
- update 1: `P1=B`, required=true
- update 2: `P2_BAD=X`, required=true

Observe independently:
1. wire response class and error details;
2. immediate state of P1;
3. whether P2_BAD exists;
4. persistent backing state (where applicable);
5. live applied state (where applicable);
6. state after another unrelated successful Set;
7. state after restart/reboot.

Source-predicted outcomes:
- **OB-USP:** Error; P1 remains A; P2_BAD absent, assuming target vendor hook participates transactionally.
- **ac-client:** Error; P1 may persist as B in UCI while live state can remain A until a later flush/reboot; P2_BAD rejected.
- **Caretaker:** SET_RESP; P1=B; P2_BAD=X created in simulator state.

This fixture is more valuable than a binary pass/fail check because the three implementations fail in three different layers: transactional rollback, persistence/activation boundary, and data-model authority/path validation.

## SPECIALIST VERDICTS
### ECOSYSTEM ANALYST
Caretaker is valuable specifically because it is independent in language/runtime/design lineage (Elixir Agent-backed simulator) and has almost no attention. It should not be mistaken for a mature conformance reference, but it supplies a clean third architecture for falsifying assumptions.

### COMMERCIAL ANALYST
Buyer: CPE/AP OEMs, ISP device-management teams, OpenWrt integrators, ACS/USP migration programs.
Pain: two products can both claim USP Set support yet differ on whether a failed multi-update request rolls back, partially persists, silently accepts unknown paths, or later activates stale state.
First paid wedge: **USP Transaction Integrity Pre-FAT** — run a small authority-backed Set/Add/Delete corpus against firmware/agents before controller migration or field rollout; report wire result + persistent state + applied state + restart behavior.
Money path: avoided provisioning regressions, field outages, rollbacks, support escalations and truck rolls.
Moat: independently authored edge-case corpus + authority versioning + multiple unrelated endpoint implementations + post-state/lifecycle measurement, not merely parser interoperability.

### RED-TEAM / VERIFIER
Attempts to disprove the three-way finding:
1. **Could Caretaker honor allow_partial elsewhere?** No branch from `handle_set` to another transaction layer was found; it directly iterates and calls `safe_set`.
2. **Could `required` be enforced in DeviceState?** No: `required` is not passed to DeviceState.
3. **Could unknown paths fail?** Generic `DeviceState.set` explicitly creates intermediate keys, so the opposite is source-predicted.
4. **Could OB-USP still leak non-transactional vendor side effects?** Yes. Its internal architecture is correct, but a vendor callback that performs irreversible external effects outside the transaction could still violate the state invariant. Therefore OB-USP is a stronger comparator, not an omniscient oracle.
5. **Does current spec settle the core state invariant?** Yes for USP 1.5 R-SET.1: when `allow_partial=false` and an Object update fails, the whole Set fails and Data Model state must not change. Response-shape history changed, but the no-partial-state invariant is the decisive acceptance condition.
6. **Was original runtime executed?** No for Caretaker and no new OpenWrt execution for ac-client in this run. Keep the exact outcomes SOURCE-PREDICTED until executed.

**VERIFIER VERDICT:** STRONG as an adversarial EXP-008 fixture and Caretaker WATCH/negative-control component; not sufficient to call either third-party implementation broadly nonconformant without end-to-end runtime evidence on the exact request/profile.

## Score / disposition — Caretaker
A3 B3 C4 D4 E3 F5 = **22/30 WATCH / architecture + negative-control fixture**.
- Speed: useful immediately for synthetic harnessing, but not a direct production wedge by itself.
- Value ceiling: component-level.
- Compression: strong for TR-069/TR-369 simulation/controller/agent test scaffolding.
- Rarity: 0-star independent Elixir implementation with both Agent and Controller.
- Evidence: source/tests/history clear, but exact conformance probe not runtime-executed.
- Rights/deployment: MIT and straightforward local stack.

## VALUE HANDOFF
1. **CAPABILITY DELTA:** CAP-014 gains a three-way USP transaction-semantic matrix: rollback-safe, reject-but-persist, and accept-invalid-path.
2. **GRAPH EDGE:** `awksedgreep/caretaker` should CHALLENGE CAP-014 data-model-authority/transaction assumptions and STRENGTHEN EXP-008 as an unrelated negative-control endpoint.
3. **RADAR SIGNAL:** strengthens RAD-007 evidence that virtual commissioning moat lives in semantic side effects and authority, not message-format interoperability.
4. **EXPERIMENT IMPACT:** replace the single two-agent USP probe with `USP-SET-TRIANGLE`, preserving response + authoritative model state + persistent state + live applied state + restart state.
5. **COMMERCIAL IMPACT:** improves the proposed fixed-price USP Transaction Integrity Pre-FAT report by demonstrating three commercially distinct failure modes from one compact fixture.
6. **NEGATIVE KNOWLEDGE:** a protobuf field being encoded is not evidence it reaches mutation semantics; a simulator that creates arbitrary paths can pass superficial Set round-trip tests while violating data-model authority.

## Search lesson candidate
**SCHEMA FIELD -> HANDLER USE -> SIDE EFFECT -> ROLLBACK TRACE**
Before trusting an atomicity/required/partial-update field, prove that the field is consumed by the handler, changes the mutation plan, reaches a real transaction/staging primitive, and survives failure/restart testing. This lesson has now succeeded in two distinct protocol investigations in this lane (SECS/GEM transaction semantics and USP Set side effects), but it is not promoted to `SEARCH_SKILLS.md` here because central promotion remains Hunt 15-owned unless explicitly delegated.

## Exact next question
Can `USP-SET-TRIANGLE` be executed end-to-end against Caretaker, ac-client and OB-USP with one neutral controller, and does OB-USP preserve the no-state-change invariant when its target parameter writes are backed by a realistic vendor adapter rather than only its internal database?