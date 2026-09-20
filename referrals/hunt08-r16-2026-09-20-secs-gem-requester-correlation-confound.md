# Hunt 08 referral R16 — SECS/GEM requester-correlation confound

Date: 2026-09-20
Lane: Industrial / protocol pre-FAT
Central edges: CAP-014 -> OPP Industrial Pre-FAT -> EXP-008; RAD-007

## Explicit hypothesis
The EXP-008 duplicate-ECID S2F15 result currently mixes two different facts: the equipment endpoint's wire behavior and the requester's transaction-completion policy. A correlated S9F7 can leave Dreamine's own requester pending to T3 while a different requester may treat the same-System-Bytes S9F7 as the response and return immediately. Therefore T3 must not be recorded as an endpoint-invariant property of the Dreamine equipment behavior.

## Evidence modes
### 1) CODE INSPECTOR — current source
- `bparzella/secsgem@59a5242d8672dad73367a0acd18088adf461404f`, `secsgem/common/protocol.py`: response waiters are stored only by System Bytes. `send_and_waitfor_response()` creates a queue for that System Bytes and returns the first message dequeued before T3; it does not validate expected stream/function.
- Same revision, `secsgem/hsms/protocol.py`: for an inbound SECS data message, if its System Bytes has a response queue, the message is put directly into that queue. Thus a correlated S9F7 can satisfy the waiting call even though it is not the expected S2F16.
- Same revision, `secsgem/secs/functions/streams_functions.py` + `secsgem/secs/functions/s09f07.py`: the returned message is decoded according to its actual header, so a same-System-Bytes S9F7 is a recognized S9F7 object rather than an expected-secondary check failure at this layer.
- `CodeMaru-Dreamine/Dreamine.Secs.Com@e57b98dfabebbf65143e2c6911866f98d3cd4fda`, `Transactions/SecsTransactionManager.cs`: `TryCompleteDeferred()` requires Function 0 or the expected adjacent even Secondary, same session, same stream, no W bit. Invalid correlation does not consume the transaction.
- Same Dreamine revision, `Hsms/HsmsSession.cs`: only inbound Secondaries or Function 0 are passed to transaction completion; a Stream-9 Function-7 is not treated as the normal completion of an open S2F15 transaction.
- `Dreamine.Gem@82604d6f03c1e95e0558de5c757989b27cd4a3d6`, `Directory.Packages.props` pins `Dreamine.Secs.Com` 1.0.0; the Gem host client uses the provider-neutral request path and converts actual T3 expiration into a TimedOut call outcome.

Evidence labels: requester correlation rules IMPLEMENTED in both stacks. Duplicate-specific two-endpoint wire execution remains NOT_RUN.

### 2) TEST INSPECTOR
- secsgem `tests/test_hsms_protocol.py` verifies a no-response T3 timeout but has no test proving that an unrelated/same-System-Bytes Stream-9 message must leave the original request pending.
- Dreamine `tests/Dreamine.Secs.Com.Tests/TransactionAndTimerTests.cs` explicitly verifies that wrong stream/function correlations do not consume an open transaction, Function 0 can complete one, and T3 expiration removes the still-open transaction.
- Extracted-control-flow micro-test for secsgem's queue contract: create a waiter keyed by one System Bytes, inject a representative S9F7 with that same key, and the waiter completes immediately before its timeout. This is a test of the inspected queue contract, not an execution of the original package.

### 3) HISTORY INSPECTOR
- secsgem commit `bd4b4aef7c939251b3c8951fb1acb40cf769c6d9` (2023-11-02, "Generalize protocol and add that to HSMS") already routed an inbound data message to `_response_queues[system]` solely on System Bytes. The requester-side correlation behavior is therefore history-stable at least to that protocol refactor, not a newly introduced quirk.
- Dreamine's current transaction manager makes strict stream/function correlation a first-class invariant with dedicated tests; treat that as requester policy, not equipment semantics.

## Specialist decomposition
### CODE INSPECTOR verdict
CONFIRMED: secsgem and Dreamine use materially different requester-side correlation rules. secsgem's low-level wait is System-Bytes-only; Dreamine's transaction manager is expected-secondary/function-zero aware.

### ECOSYSTEM / EXPERIMENT DESIGN verdict
The exact same Dreamine equipment emission can produce two different host-observed liveness outcomes depending on which requester library is used. Therefore native-host behavior cannot be used as the sole cross-engine measurement harness.

### COMMERCIAL ANALYST verdict
A pre-FAT report that says "equipment timed out" when only one requester implementation preserved the pending transaction would create false-positive incompatibility findings. Buyer-facing evidence must separate endpoint wire behavior from host policy.

### RED-TEAM / VERIFIER verdict
STRONG correction to experiment design, not a new conformance conclusion.

The durable endpoint statement should be narrower:
- Dreamine duplicate-input path: predicted correlated S9F7, no normal S2F16, unchanged EC state.
- secsgem duplicate-input path: predicted normal S2F16 EAC=0, last-value-wins state.

Requester liveness is a second dimension:
- Dreamine requester policy: correlated S9F7 is not the expected S2F16/Function0 completion, so the original transaction can remain open to T3.
- secsgem requester policy: a same-System-Bytes S9F7 can be delivered to the response waiter immediately; a T3 is therefore not guaranteed under this requester.

Do NOT label either behavior SEMI-correct from implementation evidence alone.

## EXP-008 correction requested from MASTER Integrator
Do not edit central EXP files from Hunt 08. Integrator should revise the EXP-008 measurement contract so endpoint behavior and requester policy cannot contaminate each other.

Recommended neutral harness contract:
1. Send the same frozen duplicate-ECID S2F15 W-bit frame to each equipment endpoint with a raw/neutral HSMS requester.
2. Record every correlated wire message without letting Stream-9 implicitly count as the expected Secondary.
3. Classify independently: `EXPECTED_SECONDARY`, `FUNCTION_ZERO`, `STREAM9`, `OTHER_SAME_SYSTEM`, `NO_CORRELATED_MESSAGE`.
4. Maintain a logical T3 clock as an independent observation; do not cancel it merely because a Stream-9 primary reuses System Bytes.
5. Read back EC state independently after the observation window.
6. Report endpoint tuple = `(wire reply class, S/F, System Bytes/header evidence, logical T3 state, post-state)`.
7. Separately run a requester-compatibility matrix if useful: neutral harness vs native Dreamine host vs native secsgem host. That matrix is compatibility evidence, not endpoint truth.

## Capability / graph / radar / commercial handoff
- CAPABILITY DELTA: CAP-014 gains an explicit separation between equipment semantics and requester correlation/liveness policy.
- GRAPH EDGE: strengthens EXP-008 by removing a measurement confound; does not change repository scores.
- RADAR SIGNAL: RAD-007 should treat the harness/oracle as an independent evidence plane, not reuse a candidate implementation as both subject and judge.
- EXPERIMENT IMPACT: the duplicate probe can still proceed, but its T3 assertion must be generated by the neutral harness; native-host T3 is a secondary compatibility observation.
- COMMERCIAL IMPACT: reduces false defect reports in SECS/GEM pre-FAT and creates a useful second product dimension: host/equipment pairing compatibility under error paths.
- NEGATIVE KNOWLEDGE: same System Bytes is correlation evidence, not sufficient proof of expected transaction completion. Never make requester liveness an endpoint invariant without controlling the requester implementation.

## Next exact question
Can the neutral raw-HSMS harness execute the frozen duplicate S2F15 against both pinned endpoints and produce a stable endpoint tuple while the two native requester libraries are tested separately as host-policy comparators?
