# Hunt 08 referral — SECS/GEM duplicate-ECID dispatch/reply reachability

Date: 2026-09-20
Lane: Node 08 — Protocol Moats
Primary graph edge: CAP-014 / EXP-008

## Executive result
The previous `EC-DUPLICATE-PROBE` hypothesis survives, but the Dreamine side is more severe and more commercially interesting than the earlier handler-level reading suggested.

At the pinned revisions, a duplicate valid ECID in one S2F15 request is source-predicted to produce materially different wire behavior:

- `bparzella/secsgem@59a5242d8672dad73367a0acd18088adf461404f`: duplicate entries survive schema decode, all entries validate, both are applied sequentially, S2F16 returns EAC=0, and the second value wins.
- `CodeMaru-Dreamine/Dreamine.Gem@82604d6f03c1e95e0558de5c757989b27cd4a3d6`: the wire codec rejects duplicate ECIDs before the equipment-constant service is called. Dreamine.Gem pins `Dreamine.Secs.Com` 1.0.0, whose primary dispatcher catches handler exceptions and emits diagnostics but does not send a fallback response/error. Therefore the likely on-wire result is no S2F16 response and host-side transaction timeout, with equipment-constant state unchanged.

This is SOURCE-PREDICTED, not yet end-to-end runtime-confirmed. It must not be called a SEMI conformance defect without standards/customer-profile authority.

## Explicit hypothesis
`EC-DUPLICATE-PROBE` will produce a buyer-relevant runtime divergence when the same W-bit S2F15 request contains the same valid ECID twice with different valid values: secsgem returns EAC=0 and leaves the second value, while Dreamine rejects during parsing and likely provides no S2F16 reply, causing host timeout and leaving state unchanged.

## Discovery / verification modes
1. Source call-path trace: codec -> router -> service -> transport dispatcher.
2. Schema/codec trace: determine whether duplicate list entries survive decode before application logic.
3. Test/history/version archaeology: exact Dreamine dependency-version matching, actual-TCP loopback tests, issue/history checks.
4. Falsifiable micro-test: isolated Python contract harness reproducing secsgem's inspected validation/mutation control flow.

## Specialist passes
### CODE INSPECTOR
Dreamine `E30WireCodec.ReadEquipmentConstantUpdates` converts the S2F15 entries to an array and throws a malformed-wire exception if ECIDs are duplicated. This occurs before `GemEquipmentConstantService.SetValues` runs. The service itself also has a duplicate check and a `Duplicate` result, and the router maps `Duplicate` to EAC 4, but that branch appears unreachable for a normal duplicate-on-wire S2F15 because parsing fails first.

Secsgem `equipment_constants_capability._on_s02f15` performs a full validation pass, then a mutation pass. It has no duplicate-ECID check. Two valid entries for one ECID pass validation and are applied in order, implying last-write-wins with EAC=0.

### SCHEMA / SEMANTIC VALIDATOR
Secsgem S2F15 is modeled as a repeated list of `{ECID, ECV}` entries with no uniqueness constraint in the function schema, so duplicate ECIDs survive decode to the handler.

Dreamine's codec imposes uniqueness itself and throws before the handler service can emit its explicit duplicate status.

### TEST / HISTORY VALIDATOR
Dreamine's actual-TCP `E30RouterLoopbackTests` verifies mixed-valid/invalid S2F15 atomicity: `[known valid update, unknown ECID]` returns rejection and preserves the known constant's original value. This confirms the earlier `EC-ATOMIC-PROBE` partial-mutation prediction was wrong and remains an expected-convergence guardrail.

Dreamine.Gem's central package file pins `Dreamine.Secs.Com` version 1.0.0. The matching Secs.Com 1.0.0 source (`2e8c15d649e277b398e57e3e49f095ac503fd048`) catches arbitrary Primary-handler exceptions, records a diagnostic and does not send a Secondary or Stream-9 fallback from that catch path. This makes the no-reply/timeout outcome the strongest static prediction for duplicate S2F15.

Neither inspected project's issue search surfaced a duplicate-S2F15 issue, and neither inspected semantic test set contains an explicit duplicate-ECID end-to-end regression.

### MICRO-TEST
A local isolated Python contract harness reproducing the exact inspected secsgem `_on_s02f15` control flow produced:

- duplicate valid `[20->123, 20->456]` -> EAC 0, final value 456;
- valid then unknown `[20->123, 999->1]` -> EAC 1, original value preserved;
- duplicate with second out-of-range `[20->123, 20->501]` -> EAC 3, original value preserved.

This confirms the static control-flow interpretation only. The original pinned secsgem package and HSMS wire runtime were NOT_RUN in this environment.

## Independent RED-TEAM / VERIFIER verdict
**PROCEED WITH ONE END-TO-END DUPLICATE PROBE.**

Strong evidence exists for a real implementation disagreement, but not for normative standards correctness. If the runtime result matches the source prediction, classify it as an implementation/profile disagreement until the customer's required profile or authorized SEMI material establishes the expected behavior.

Do not add another generic SECS/GEM engine before running this probe. Introduce the retained third engine only if the two pinned engines actually diverge and adjudication would materially change the buyer report.

The strongest new static defect candidate is internal Dreamine reachability: the service/router expose a duplicate-specific EAC mapping, yet the wire parser rejects duplicates before that mapping can be reached, and the exact pinned transport dispatcher appears to convert the parse failure into a logged exception with no reply. This is more commercially relevant than an ACK-code mismatch because it can manifest as a hung W-bit transaction.

## Commercial implication
The sellable wedge is now more concrete: **SECS/GEM semantic edge-case regression with reply/timeout/post-state evidence.** A buyer can receive a reproduction packet that shows not merely different return codes, but whether malformed or ambiguous input causes a transaction to succeed, reject deterministically or hang until timeout before FAT/production connection.

## Candidate reusable search lesson
### PARSER -> HANDLER -> REPLY REACHABILITY TRACE
WHEN TO USE: protocol implementations that advertise explicit ACK/error statuses for malformed, duplicate or invalid requests.

PROCEDURE: trace the error class through wire/schema decoding, handler dispatch, validation/service logic, exception handling, reply generation and post-state. Confirm that the advertised handler-level error branch is actually reachable from an on-wire request. Then build the smallest malformed-but-decodable perturbation that distinguishes reply-vs-timeout and state side effects.

WHY IT WORKED: Dreamine appeared at first to support `Duplicate -> EAC 4`, but the wire codec throws on duplicate ECIDs before `SetValues`, while the exact pinned dispatcher only logs handler exceptions. Handler-level status mapping therefore does not prove an on-wire reply.

FAILURE MODES: assuming parser failures are automatically translated to Stream-9 or application ACKs; inspecting a different transport/runtime version than the package actually pinned; treating a contract micro-test as full network execution.

STATUS: candidate only — first hunt confirmation; do not promote to SEARCH_SKILLS.md until independently confirmed on another task/lane or Hunt 15 approves.

## Knowledge-to-Value handoff
1. CAPABILITY DELTA — CAP-014 can now test parser/error-path reachability and transaction liveness, not just semantic state/ACK equality.
2. GRAPH EDGE — EXP-008 receives a precise high-information discriminator after the mixed-invalid atomicity hypothesis was falsified.
3. RADAR SIGNAL — virtual FAT moat increasingly depends on lineage-independent endpoints + malformed semantic probes + reply/state/timeout traces.
4. EXPERIMENT IMPACT — stop generic SECS/GEM discovery; execute one duplicate-ECID W-bit request and normalize response-vs-timeout plus post-state.
5. COMMERCIAL IMPACT — the service can catch hung provisioning/configuration transactions that would otherwise consume FAT debugging hours, not merely protocol-code differences.
6. NEGATIVE KNOWLEDGE — a handler's advertised ACK mapping does not imply the same error is reachable on the wire; parser and dispatch exception paths can preempt it.

## Exact next question
When the same duplicate-ECID S2F15 W-bit request is sent over HSMS to both pinned revisions, does Dreamine indeed provide no S2F16 reply and preserve state while secsgem returns EAC=0 with last-value-wins, and—only if that divergence is runtime-confirmed—does a third independent engine materially adjudicate the buyer-facing expected behavior?
