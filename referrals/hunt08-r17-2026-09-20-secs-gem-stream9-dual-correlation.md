# Hunt 08 R17 — SECS/GEM Stream-9 dual-correlation correction — 2026-09-20

## Hypothesis
A neutral HSMS harness that correlates Stream-9 errors only by the Stream-9 message's outer HSMS System Bytes can misclassify the same protocol error, because implementations/equipment may choose different System Bytes for the S9 message itself while the embedded MHEAD remains the authoritative evidence of the offending request.

STATUS: **SUPPORTED / STRONG experiment-design correction; duplicate-S2F15 endpoint execution still NOT_RUN.**

## Discovery modes used
1. **Direct source trace:** `bparzella/secsgem@59a5242d8672dad73367a0acd18088adf461404f`, `CodeMaru-Dreamine/Dreamine.Gem@82604d6f03c1e95e0558de5c757989b27cd4a3d6`, and pinned `CodeMaru-Dreamine/Dreamine.Secs.Com@e57b98dfabebbf65143e2c6911866f98d3cd4fda`.
2. **Real-equipment issue evidence:** open secsgem issue #220 contains a February 6, 2026 trace from actual equipment returning S9F7 with a fresh outer System Bytes while the 10-byte MHEAD body embeds the original offending S5F5 header/System Bytes.
3. **Cross-implementation analog:** `younglifestyle/secs4go@16d365e9e3346d6ca07f42f62152e0a4c0bde936` deliberately builds S9F7 using the offending message's System Bytes as the S9 message's own System Bytes, matching Dreamine's policy rather than the real-equipment trace in issue #220.
4. **History/API trace:** secsgem HEAD commit `59a5242d...` changed `set_ecs()`'s return annotation from a broad `int | str | float | bytes | None` to `int` without adding expected-response validation.
5. **Small falsifiable contract test:** an extracted control-flow simulation of secsgem's exact queue-key/decode/get semantics showed that a same-outer-System-Bytes S9F7 is consumed by the waiter and yields a 10-byte `bytes` result from `set_ecs()` semantics, while a fresh-outer-System-Bytes S9F7 is routed as unsolicited and leaves the original request pending to T3. This is NOT original-package runtime evidence.

## Source / schema / test / history verification

### Dreamine equipment-side Stream-9 policy
`Dreamine.Gem` pins `Dreamine.Secs.Com` 1.0.0. The pinned/current Secs.Com tree is `e57b98dfabebbf65143e2c6911866f98d3cd4fda`.

`E30WireCodec.StreamNine(offending, function)` constructs the S9 message with:
- the offending Session ID;
- Stream 9 / requested S9 function;
- W-bit false;
- **the offending message's System Bytes as the S9 message's own System Bytes**;
- the offending 10-byte header encoded as MHEAD in the body.

`E30EquipmentRouter.InvokeHandlerAsync()` catches `E30WireFormatException` and sends `StreamNine(context.Primary, 7)`. For duplicate S2F15, `ReadEquipmentConstantUpdates()` rejects duplicate ECIDs before the constant service is reached, so the predicted Dreamine endpoint tuple remains S9F7 + unchanged EC state + no normal S2F16.

`Dreamine.Secs.Com`'s `HsmsFrameCodec.WriteHeader()` serializes `header.SystemBytes.Value` directly, so the explicit System Bytes chosen by `StreamNine()` survive onto the wire.

### secsgem requester correlation policy
`secsgem/common/protocol.py` stores pending response queues in a dictionary keyed only by `system_id`. `send_and_waitfor_response()` registers one queue for the outbound request System Bytes and returns the first message inserted into it.

`secsgem/hsms/protocol.py::_on_connection_message_received()` routes every inbound HSMS data message to the pending queue when `message.header.system` matches a pending key; otherwise it fires the unsolicited `message_received` event. It does not validate that the inbound stream/function is the expected adjacent Secondary before queue delivery.

Therefore the same S9F7 semantic error produces two different native-host outcomes depending on the endpoint's S9 outer-System-Bytes policy:

- **S9 outer System Bytes = offending request System Bytes:** secsgem's waiter consumes the S9F7 immediately.
- **S9 outer System Bytes = fresh System Bytes:** secsgem treats the S9F7 as unsolicited and the original request remains pending until T3 unless some normal response arrives.

### secsgem high-level `set_ecs()` type/result seam
`SecsHandler.set_ecs()` sends S2F15, passes whatever message the low-level waiter returns into `StreamsFunctions.decode()`, and then returns `.get()` with no assertion that the decoded function is S2F16.

`StreamsFunctions.decode()` chooses the decoder from the **actual inbound stream/function**. Thus a same-System-Bytes S9F7 becomes `SecsS09F07`, not an S2F16 decode error.

S9F7's body is MHEAD, defined as Binary length 10. `Binary.get()` returns `bytes` for lengths other than one. Consequently, when an S9F7 shares the original outer System Bytes, secsgem's `set_ecs()` is source-predicted to return the 10-byte MHEAD as `bytes` even though the current signature says `-> int`.

History strengthens the finding: HEAD commit `59a5242d...` changed the prior broad return annotation `int | str | float | bytes | None` to `int` because `StreamsFunctions.decode()` cannot return None, but it added no expected-reply validation. Runtime control flow still permits a different valid stream/function object to be decoded.

### Real equipment evidence that outer System Bytes can differ
Open secsgem issue #220 (created 2026-02-06, still open in the inspected 2026-09-20 state) includes a real-equipment S9F7 trace. The offending S5F5 W request used outer System Bytes `e9:f7:7d:b6`. The returned S9F7 used its own outer System Bytes `09:07:3b:fb`, while its MHEAD body was `12:34:85:05:00:00:e9:f7:7d:b6`, embedding the original offending header/System Bytes. secsgem logged the S9F7 as an unexpected unsolicited function rather than satisfying the outstanding request.

This is operational-profile evidence, not universal standards authority.

### Cross-implementation counterexample
`younglifestyle/secs4go`'s `sendS9F7IllegalData()` extracts the offending header's System Bytes, calls `BuildS9F7(...)`, and then explicitly sets the S9 message's own Session ID/System Bytes to the offending values. This matches Dreamine's policy and differs from the commercial equipment trace in secsgem #220.

The diversity is the point: a neutral harness must support both policies rather than assuming one is universal.

## Independent RED-TEAM / VERIFIER verdict
**STRONG experiment-design correction; NOT a SEMI-conformance verdict.**

Strongest objections considered:
- The commercial equipment in issue #220 could itself be profile-specific or nonconforming; therefore its fresh-System-Bytes behavior is evidence of deployed diversity, not proof of the standard.
- `secs4go` and Dreamine using offending System Bytes does not prove that policy is universally correct either.
- The extracted contract test is not original secsgem runtime execution.
- The duplicate-S2F15 cross-endpoint run remains NOT_RUN.

What survives red-team is implementation-independent: **Stream-9 has two distinct correlation surfaces that must be recorded separately — the S9 message's outer HSMS System Bytes and the embedded MHEAD/SHEAD describing the offending message. Using only the outer value can change the measured requester outcome.**

## Corrected neutral-harness contract
For every inbound S9F1/F3/F5/F7/F9/F11 during a pending transaction, record at minimum:
1. S9 outer Session ID / Stream / Function / System Bytes;
2. raw 10-byte MHEAD or SHEAD body;
3. parsed embedded offending Session ID / Stream / Function / PType / SType / System Bytes;
4. whether outer System Bytes equals the pending request;
5. whether embedded offending System Bytes equals the pending request;
6. whether any normal expected Secondary or Function-0 arrived;
7. independent logical T3 outcome;
8. post-state readback.

**Correlation rule for the neutral oracle:** classify S9 relationship to the pending request primarily from the embedded MHEAD/SHEAD, while retaining the S9 message's own outer System Bytes as a separate interoperability dimension. Do not let a candidate SDK's waiter decide endpoint correlation.

## Commercial implication
The paid SECS/GEM pre-FAT report should add a distinct field: **Stream-9 correlation policy**. A host/equipment pair can observe the same underlying Illegal Data event yet differ drastically at the application API:
- early return of S9/MHEAD bytes;
- unsolicited S9 event plus later T3;
- or a stricter SDK-specific protocol exception.

That is a real commissioning risk. It can explain why a customer sees "timeout" with one host library and an immediate error with another even though the endpoint emitted essentially the same S9 semantic error.

## Search-policy candidate
**DUAL-CORRELATION ERROR TRACE**

WHEN TO USE: protocols where an error message carries both its own transaction identifier and an embedded reference to the offending transaction/message.

PROCEDURE: trace outer correlation fields separately from embedded offending-message fields; then test host requester behavior under both same-ID and fresh-ID error policies.

WHY IT WORKED: it converted a vague requester-correlation concern into a concrete two-policy compatibility matrix backed by source code, a real equipment trace, and an independent implementation.

FAILURE MODES: treating one vendor trace as standards authority; assuming an embedded header is always authoritative without checking the applicable profile; conflating host SDK outcome with endpoint wire behavior.

STATUS: candidate only. Do not promote to `SEARCH_SKILLS.md` until it succeeds on a second distinct benchmark/hunt task or Hunt 15 approves it.

## VALUE HANDOFF
1. **CAPABILITY DELTA:** CAP-014 gains a protocol-error oracle that can correctly correlate Stream-9 even when the S9 message's own System Bytes differ from the offending request.
2. **GRAPH EDGE:** EXP-008's neutral HSMS harness contract is materially strengthened before duplicate-S2F15 execution.
3. **RADAR SIGNAL:** RAD-007 now has a concrete reason independent observation must preserve both outer wire identifiers and embedded error evidence.
4. **EXPERIMENT IMPACT:** the next duplicate-S2F15 run must compare both S9 correlation fields; native secsgem host behavior should be tested twice conceptually: against same-System-Bytes S9 endpoints such as Dreamine and against fresh-System-Bytes equipment profiles such as the trace in issue #220.
5. **COMMERCIAL IMPACT:** adds a buyer-visible host/equipment compatibility failure class that generic protocol simulators can miss.
6. **NEGATIVE KNOWLEDGE:** same semantic S9 error does not imply the same host/API liveness outcome; outer System Bytes alone is an unsafe oracle.

## NEXT HIGHEST-VALUE QUESTION
**When the neutral raw-HSMS duplicate-S2F15 fixture is executed against Dreamine and secsgem equipment endpoints, what exact `(S9 outer System Bytes, embedded MHEAD System Bytes, expected Secondary, logical T3, post-state)` tuple does each produce, and how do Dreamine/secsgem native hosts behave when replayed the same tuple?**
