# Hunt 08 Referral R23 — Independent HSMS measurement harness candidate

Date: 2026-09-20
Node: 08 — Protocol Moats
Scope: close EXP-008's neutral-measurement gap before adding another SECS/GEM endpoint.

## HYPOTHESIS

**Hypothesis:** EXP-008 can be made materially more falsifiable without adding a third equipment endpoint if an independent HSMS transport can (a) preserve raw frame evidence, (b) fan out all inbound data messages including orphan/mismatched messages, (c) refuse to let same-System-Bytes but semantically wrong data complete the expected S2F16 transaction, and (d) keep its own transaction semantics separable from the experiment's external logical-T3 oracle.

**Status:** SUPPORTED for `arloliu/go-secs@020da48962dee4b14a7496b7f57f2734ff8a7256`, with important neutrality limits recorded below.

**Confidence:** high for source/test behavior; runtime against Dreamine/secsgem duplicate-S2F15 remains NOT_RUN in this environment.

## DISCOVERY MODES USED

1. **Direct problem search:** SECS/GEM/HSMS packet recorder, replay, raw requester, simulator/workbench searches. Current public search surfaced `NOKTRA-secsgem-workbench`, `NHSE/Secs-Gem-Simulator`, `pysemisecs`, `go-secs` and other requester/simulator projects.
2. **Code-level search:** searched HSMS implementations for `SystemBytes`, `AddDataMessageChan`, reply registries, strict reply matching, T3, raw trace and error-message paths. This surfaced `arloliu/go-secs`, `RRQM/TouchSocket.Semi`, `superbayes/QHSMS`, `younglifestyle/secs4go`, and older demos/forks.
3. **History/conformance archaeology:** inspected `go-secs`'s 2026 conformance audit, reply-matching implementation plan, current reply-matching tests, current HEAD history and v2.4.1 package surface. This was higher-information than adding another endpoint because it directly tested the experiment's observation boundary.
4. **Low-attention comparison:** inspected older/less mature HSMS projects as candidate harnesses. `QHSMS` is stale (HEAD 2022) with placeholder README material; `NHSE/Secs-Gem-Simulator` is an educational host simulator implementing only a subset of timers; `TouchSocket.Semi` has useful parsing/session code but its inspected `HsmsClient` wait pool is wired to control responses while data messages are delivered to plugins, making it a poor drop-in synchronous differential requester.

## BEST NEW FIND — `arloliu/go-secs`

- URL: https://github.com/arloliu/go-secs
- Exact revision: `020da48962dee4b14a7496b7f57f2734ff8a7256`
- Current package release verified externally: v2.4.1, published 2026-08-14.
- Public license: Apache-2.0.
- GitHub metadata at inspection: 38 stars, 6 forks, 1 open issue; created 2024-10-27; pushed 2026-08-14.
- Classification: **strong component / experiment-enabler**, not conformance oracle.
- Score: **26/30** — A3 B4 C5 D4 E5 F5.

### Capability delta

`go-secs` can serve as the independent **measurement/requester plane** for the current duplicate-ECID S2F15 experiment, provided the experiment still records its own external logical T3 and does not equate `go-secs` behavior with SEMI authority.

The useful properties are unusually aligned with the existing EXP-008 confounds:

1. `hsms.DataMessage` preserves the full 10-byte header, System Bytes, Session ID, stream/function/W-bit, encoded body and trailing-byte count. `ToBytes()` emits length + header + stored body bytes.
2. `SECS2Endpoint.AddDataMessageChan` fans inbound data messages to a caller-controlled channel. Tests document delivery of primaries and orphan secondaries.
3. `WithTraceTraffic(true)` logs sent/received frame hex and logs raw bytes for inbound frames that fail decode.
4. `WithStrictReplyMatching(true)` makes same-System-Bytes but wrong Stream/Function secondaries miss the reply transaction and fall through to the data handlers rather than completing it.
5. `WithSessionIDValidation(true)` is a separate option, so SessionID policy is explicit rather than silently bundled into the reply registry.
6. T3 is configurable; `WithAutoS9F9` is disabled by default; automatic linktests are disabled by default. Those defaults reduce active interference in a measurement harness.
7. The code contains extensive connection-level tests for default-vs-strict reply matching, correct replies, SxF0, mismatched replies, T3 stall and later conforming-reply recovery.

### Why this specifically helps the current S9F7 confound

The current EXP-008 issue is that a correlated Stream-9 error and transaction completion are not the same fact.

`go-secs` makes the key distinction structurally:

- `DataMessage.IsPrimary()` classifies an odd-function message as a primary; S9F7 is therefore a primary notification, not a secondary reply.
- `DeliverOwnedFrame()` offers only secondaries to the pending-reply registry.
- Therefore an S9F7 cannot satisfy the pending S2F15->S2F16 transaction merely because its **outer System Bytes** equals the S2F15 System Bytes.
- The S9F7 instead reaches the ordinary data-message fanout/channel, where the harness can parse both its outer System Bytes and embedded 10-byte MHEAD independently.
- The S2F15 wait can remain open until a legitimate S2F16/S2F0 or T3.

That behavior is especially useful because prior analysis showed native requester libraries can disagree on whether a same-System-Bytes Stream-9 message completes a waiter.

### Source verification

Inspected at the pinned revision:

- `hsms/data_msg.go`
  - immutable 10-byte header and body storage;
  - `SystemBytes()`, `HeaderBytes()`, `Stream()`, `Function()`, `WaitBit()`;
  - `IsPrimary()` returns true for odd functions or W-bit messages; SxF0 is explicitly secondary;
  - `TrailingBytes()` exposes bytes after the first decoded SECS-II item.
- `hsms/connection_runtime.go`
  - `DeliverOwnedFrame()` routes only secondaries into the reply registry;
  - primaries always fall through to session handlers/fanout;
  - `RouteReply()` preserves the pending registration on a strict field mismatch;
  - inbound SessionID validation and S9F1 handling are explicit.
- `hsms/connection_config.go`
  - explicit T3;
  - auto-linktest default 0/off;
  - session-ID validation opt-in;
  - strict reply matching opt-in;
  - auto-S9F9 disabled by default;
  - trace-traffic option.
- `hsms/reply_matching_test.go`
  - proves default mismatched replies still complete but are counted;
  - proves strict mismatched replies become unsolicited and stall to T3;
  - proves same-stream F0 remains a valid abort completion;
  - proves a later conforming reply can still complete after a strict mismatch.
- `hsmsss/integration_reply_matching_test.go`
  - real active/passive Select and Linktest controls under strict/default modes.
- `docs/specs/secs2-hsms-conformance-audit.md`
  - candidly records deviations instead of self-declaring blanket conformance;
  - documents the historical System-Bytes-only reply-matching gap and the current observe/default vs enforce/strict posture;
  - keeps several deliberate deviations visible rather than silently upgrading them.

### History verification

Current HEAD is `020da48962dee4b14a7496b7f57f2734ff8a7256` (2026-08-14). The head commit tightens integration-test state-edge ordering after a race was reproduced under `-race`; the commit message records a deliberately failing negative condition (refusing every redial still fails the re-Select assertion). The preceding commit cuts v2.4.1. This is useful maintenance evidence because the project is actively testing failure behavior rather than only happy paths.

The reply-matching feature itself is not hidden accidental behavior: current package documentation exposes `WithStrictReplyMatching`, its default-vs-strict semantics, and the T3 consequence.

## COMPARATORS / TRIAGE

### `RRQM/TouchSocket` — `TouchSocket.Semi`
Exact inspected revision from code search: `df47a0d58edae9cb16ea7ede49bfa5db0e6869cf`.

Useful as a code-level comparator, but **not preferred for the EXP-008 neutral requester**:
- `HsmsMessage` implements `IWaitHandle.Sign` using System Bytes;
- `HsmsClient.SendHsmsMessageAsync()` allocates a wait handle whenever `ReplyExpected` is true;
- inspected `OnTcpReceived()` calls `m_waitHandlePool.Set(message)` for Select/Deselect/Linktest responses, but the `DataMessage` case only raises `OnHsmsReceived()`/plugins;
- repository-wide search found the same pattern in `HsmsSessionClient`.

This makes its built-in synchronous data-transaction behavior a poor choice for the current experiment without additional custom correlation logic. Treat this as negative knowledge, not a defect claim beyond the inspected source path.

### `superbayes/QHSMS`
Exact HEAD `2744a09f9fc23cdf7b9ee443354dd3b436960817`, last updated 2022-10-08. It contains low-level HSMS framing/SystemBytes code but the README is mostly a GitHub Pages placeholder and the project is stale. It does not beat `go-secs` on tests, maintenance, evidence or observability.

### `NHSE/Secs-Gem-Simulator`
Exact HEAD `07c3e206ee531f03d84f403b0618fcccd1c45da3` (2026-02-24). Educational C++/Qt host simulator with direct HSMS/T3/T5/T6 implementation and logging. README explicitly says it is learning/practice oriented and only T3/T5/T6 are implemented for its HSMS host focus. Useful as a teaching/comparison surface, not a better neutral acceptance harness.

### `NOKTRA-secsgem-workbench`
Current public discovery surfaced a desktop decoder/session driver/simulator with raw-wire JSONL record/replay. This is potentially useful as a **human inspection tool**, but it was not available through the connected GitHub action in this run for source/history/license verification, so it is not promoted above the verified `go-secs` component.

## SPECIALIST PASSES

### CODE INSPECTOR
**Verdict: STRONG component evidence.** The relevant behavior is in implementation and tests, not just README. The strongest evidence is the `DeliverOwnedFrame -> isSecondaryReply -> RouteReply/RouteData` chain plus strict-reply/T3 tests.

### ECOSYSTEM ANALYST
**Verdict: healthy for a niche library.** Current v2.4.1 package, recent August 2026 push, Apache-2.0, modest-but-real adoption, separate v1 maintenance branch, package docs and benchmarks. This is not an abandoned one-file demo.

### COMMERCIAL ANALYST
**Buyer:** semiconductor equipment OEMs, fab integration teams, SECS/GEM host vendors, commissioning/test houses.

**Painful problem:** library-specific requester behavior can misclassify a protocol-error path, creating false pre-FAT defect reports or hiding host/equipment compatibility differences.

**First paid wedge:** **SECS/GEM Differential Pre-FAT — neutral-wire edition**. Run a small frozen corpus (starting with duplicate-ECID S2F15) through two independent equipment implementations, capture raw/message evidence with the independent harness, compute an external logical-T3 result, and read post-state. Native host SDK behavior becomes a second matrix, not the oracle.

**Money path:** reduced fab/tool integration debug time, fewer on-site commissioning surprises, earlier host/equipment incompatibility detection.

**Build compression:** likely weeks of HSMS session/timer/codec/observability plumbing avoided; more importantly, it closes an experiment-design gap already blocking CAP-014/EXP-008.

### RED-TEAM / VERIFIER
**Independent verdict: STRONG AS A MEASUREMENT COMPONENT; NOT A NEUTRAL CONFORMANCE ORACLE.**

Objections that survive:
1. `go-secs` still parses and routes the connection. A true packet tap/raw TCP observer is one layer more independent.
2. Strict reply matching is opt-in; the default intentionally delivers same-System-Bytes wrong-S/F secondaries to the waiter while only counting the mismatch.
3. Session-ID validation is separate and also opt-in.
4. The project documents deliberate protocol deviations, including reconnect/T5 behavior. That is evidence of honesty, but it means the library must be configured for the exact experiment and must not grade conformance by itself.
5. `WithTraceTraffic` raw logging should be supplemented by the harness's own structured tuple extraction; human log text is evidence transport, not the result schema.
6. Original Dreamine/secsgem duplicate-S2F15 runtime execution remains NOT_RUN here because the execution container cannot fetch the external repositories directly. Source/test verification is not a substitute for that wire experiment.

What survives red-team:
- S9F7 is structurally kept out of the expected-secondary waiter because it is a primary odd-function message.
- inbound message fanout and strict mismatch fallthrough are source- and test-backed;
- automatic S9F9/linktest behavior can be left disabled;
- raw/encoded evidence is inspectable;
- the library can reduce, rather than increase, the current requester-correlation confound if used as plumbing plus an external oracle.

## PROPOSED EXP-008 HARNESS CONTRACT

For the duplicate-ECID probe, configure/record:

1. active HSMS requester with controlled SessionID and T3;
2. automatic linktest disabled;
3. automatic S9F9 disabled;
4. strict reply matching enabled;
5. SessionID validation either enabled or explicitly measured as a separate variant;
6. trace/raw frame sink enabled;
7. inbound `AddDataMessageChan` collector;
8. experiment-owned deadline independent of the library return;
9. classify each inbound frame as:
   - EXPECTED_SECONDARY (S2F16),
   - FUNCTION_ZERO (S2F0),
   - STREAM9 (including S9F7),
   - OTHER_SAME_SYSTEM,
   - OTHER;
10. for S9, retain BOTH outer System Bytes and embedded MHEAD/SHEAD System Bytes;
11. at experiment T3, record whether expected transaction completion occurred independently of what the client API returned;
12. read EC post-state through a separate deterministic readback after the probe;
13. then run Dreamine and secsgem native requesters against the same endpoint behavior as a compatibility matrix.

This preserves the current acceptance invariant: **correlation is not completion, and implementation agreement is not standards authority.**

## EMERGENCE / GRAPH / VALUE HANDOFF

### Capability delta
`CAP-014` gains a credible independent HSMS measurement/requester plane rather than relying on either equipment implementation's native client behavior.

### Graph edge
`arloliu/go-secs -> STRENGTHENS CAP-014 -> enables cleaner EXP-008 neutral measurement`.

### Radar signal
Strengthens `RAD-007` customer-profile-derived virtual commissioning: a defensible pre-FAT system needs a third observation plane in addition to two endpoint implementations.

### Experiment impact
Do **not** add another SECS/GEM equipment engine yet. First execute the frozen duplicate-ECID S2F15 through Dreamine and secsgem equipment endpoints using the independent harness contract above. A third endpoint remains a tie-breaker only after an actual observed endpoint disagreement.

### Commercial impact
Makes the SECS/GEM pre-FAT offer more defensible by separating:
1. what the equipment emitted on the wire;
2. whether the expected transaction completed;
3. what state changed;
4. how each native host SDK interpreted the same traffic.

### Negative knowledge
- A generic HSMS client is not automatically a neutral observer.
- Same System Bytes alone is not expected-secondary completion.
- A Stream-9 notification needs outer + embedded correlation recorded independently.
- Default compatibility/leniency modes must be surfaced; they cannot silently define the acceptance result.
- More endpoint repositories are currently lower information value than executing the two existing endpoints through an independent observation plane.

## SEARCH POLICY UPDATE CANDIDATE

**INDEPENDENT OBSERVER BEFORE THIRD IMPLEMENTATION**

WHEN TO USE: two protocol implementations disagree or are predicted to disagree, and the measurement path is entangled with one implementation's native requester/runtime.

PROCEDURE: before adding a third implementation, search for or build a rights-clean independent observer/requester that preserves raw identifiers/messages, uses an experiment-owned timeout, and can expose unmatched/error traffic without consuming it as a normal reply. Run endpoint semantics and native-requester compatibility as separate matrices.

WHY IT WORKED HERE: the highest-value open question was not another SECS/GEM engine; it was whether requester correlation policy was contaminating the observed duplicate-S2F15 result. `go-secs` directly closes that missing measurement edge.

FAILURE MODES: observer auto-replies or normalizes errors; wrong default reply-matching posture; raw bytes are reconstructed/lost; observer becomes the conformance oracle; transport behavior changes the endpoint.

PROMOTION STATUS: **DO NOT add to SEARCH_SKILLS.md yet.** This lesson has not satisfied the required repeated benchmark-task success/Hunt-15 approval threshold.

## NEXT HIGHEST-VALUE QUESTION

Can the frozen duplicate-ECID S2F15 fixture be executed against Dreamine and secsgem equipment endpoints with `go-secs` (or an even thinner raw TCP wrapper) as the independent observation plane, producing a reproducible tuple of `(raw inbound frames, outer System Bytes, embedded MHEAD System Bytes, expected-secondary completion, external logical T3, EC post-state)` for each endpoint?
