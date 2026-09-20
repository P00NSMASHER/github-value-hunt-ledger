# Hunt 08 referral — SECS/GEM duplicate-S2F15 Stream-9 correction

Date: 2026-09-20
Lane: Node 08 — Protocol Moats
Primary graph edge: CAP-014 / EXP-008

## Executive result
The prior Hunt 08 referral (`hunt08-r12-2026-09-20-secs-gem-duplicate-dispatch.md`) correctly identified duplicate ECID handling as a high-information differential probe, but its Dreamine transport interpretation was incomplete.

At the pinned revisions, the strongest source-and-test-backed prediction for a duplicate valid ECID in one W-bit S2F15 is now:

- `CodeMaru-Dreamine/Dreamine.Gem@82604d6f03c1e95e0558de5c757989b27cd4a3d6`: `ReadEquipmentConstantUpdates()` rejects duplicate ECIDs with `E30WireFormatException`; `E30EquipmentRouter.InvokeHandlerAsync()` catches that exact exception and sends correlated S9F7. Because the host transaction manager accepts only F0 or the adjacent normal secondary on the same stream, the S9F7 does not close the original S2F15 transaction. Dreamine's actual-TCP test already proves the analogous malformed W-bit path: correlated S9F7 is observed and the originating request later ends in T3 timeout. Since duplicate rejection happens before `SetValues`, equipment-constant state remains unchanged.
- `bparzella/secsgem@59a5242d8672dad73367a0acd18088adf461404f`: S2F15 is a repeated list with no uniqueness constraint; `_on_s02f15` performs one validation pass and then applies all entries sequentially if validation succeeds, with no duplicate-ECID check. Two individually valid writes to one ECID are therefore source-predicted to produce S2F16 EAC=0 with the second value winning.

The economically interesting difference is therefore **correlated protocol error + eventual T3 timeout + unchanged state** versus **normal S2F16 success + last-value-wins**, not merely `no reply` versus EAC=0.

This is still not a standards-conformance verdict. Runtime execution of the exact duplicate fixture against both original pinned packages remains NOT_RUN in this environment.

## Explicit hypothesis
**STATUS: STRONGLY SUPPORTED STATIC / DUPLICATE-SPECIFIC RUNTIME NOT_RUN.**

When the identical duplicate-ECID W-bit S2F15 request `[ECID x -> valid A, ECID x -> valid B]` is sent to both pinned engines:
1. Dreamine will emit correlated S9F7, leave EC state unchanged, and the waiting S2F15 transaction will later expire T3 because S9F7 is not a normal S2F16 secondary.
2. secsgem will return S2F16 EAC=0 and leave ECID x at value B.

## Discovery / verification modes
1. **Parser -> router -> transport call-path trace.** Followed duplicate S2F15 from `E30WireCodec.ReadEquipmentConstantUpdates()` through `E30EquipmentRouter.InvokeHandlerAsync()` into `Dreamine.Secs.Com` receive/transaction handling.
2. **Schema + handler semantics.** Compared Dreamine's explicit uniqueness check with secsgem's unconstrained repeated-list S2F15 schema and two-pass validate-then-mutate handler.
3. **Actual-TCP test archaeology.** Inspected Dreamine's `E30RouterLoopbackTests.ObservableFundamentalErrorsEmitCorrelatedS9AcrossActualTcp`, which proves a malformed W-bit primary yields correlated S9F7 and then T3 timeout.
4. **History / exact revision verification.** Dreamine.Gem pins `Dreamine.Secs.Com` 1.0.0; matching transport source was inspected at `2e8c15d649e277b398e57e3e49f095ac503fd048`. Dreamine's pinned head had a successful CI run. Secsgem pinned head is active in 2026 and its S2F15 handler/schema were inspected at the exact revision.

## Specialist passes
### CODE INSPECTOR
Dreamine:
- `E30WireCodec.ReadEquipmentConstantUpdates()` materializes entries, then checks `Distinct().Count() != result.Length` and throws `E30WireFormatException` for duplicate ECIDs.
- `E30EquipmentRouter.HandleS2F15Async()` does contain a downstream `GemConstantBatchStatus.Duplicate -> EAC 4` mapping, but an ordinary duplicate-on-wire request does not reach it because the codec throws first.
- The router wraps handler execution in `InvokeHandlerAsync()` and converts `E30WireFormatException` directly to `E30WireCodec.StreamNine(primary, 7)` via `_session.SendAsync(...)`.
- `StreamNine()` preserves Session ID and System Bytes and embeds the offending 10-byte header.

Dreamine.Secs.Com:
- The receive loop treats only function-zero or even functions as candidate normal transaction completions. S9F7 is an odd-function primary, so it is delivered as an application message rather than completing the pending S2F15 transaction.
- The transaction manager accepts only F0 or the adjacent even secondary on the same stream; otherwise T3 remains active.

Secsgem:
- `SecsS02F15` declares a repeated `<L <L <ECID><ECV>>>` structure and does not impose ECID uniqueness.
- `_on_s02f15()` validates every entry, then, when EAC remains zero, iterates the original sequence and applies each update. No duplicate key check exists. The same ECID therefore gets written twice in order.

### TEST / HISTORY VALIDATOR
Dreamine's actual-TCP `ObservableFundamentalErrorsEmitCorrelatedS9AcrossActualTcp` establishes the crucial liveness semantics independent of source interpretation:
- a malformed W-bit request produces correlated S9F7 carrying the offending header and System Bytes;
- the original `SendPrimaryAsync` request still throws `SecsTransactionTimeoutException` after T3;
- an oversized W-bit request analogously produces S9F11 then T3 timeout.

Dreamine's main pinned revision `82604d6...` had a successful CI run on 2026-08-17. The E30 router file history shows the profile was introduced in August 2026 and the pinned head followed with reliability/coverage hardening.

Secsgem's pinned revision is version 0.3.0 / LGPL-2.1-or-later and remains active; scheduled code scanning is still succeeding on the pinned head in September 2026. Existing tests exercise S2F15 equipment-constant handling but no explicit duplicate-ECID regression was found in the inspected corpus.

### SCHEMA / SEMANTIC VALIDATOR
The two implementations disagree before any standards interpretation is introduced:
- Dreamine adds a profile-level uniqueness rule to S2F15 decoding and classifies violations as illegal data through S9F7.
- secsgem preserves duplicate entries as ordinary sequence elements and resolves them operationally by sequential assignment.

Without separately authorized SEMI/customer profile authority, neither behavior is labeled normatively correct. The correct buyer-facing category is `IMPLEMENTATION/PROFILE DISAGREEMENT — AUTHORITY REQUIRED`.

### COMMERCIAL ANALYST
Buyer: semiconductor equipment OEM integration teams, fab MES/EAP teams, automation integrators.
Pain: FAT/bring-up time lost to edge-case dialog behavior that single-engine simulators conceal.
First paid wedge: fixed-price pre-FAT semantic regression pack that reports `normal secondary / Function 0 / Stream-9 / timeout / post-state` for a frozen customer-authorized dialogue corpus.
Money path: reduced FAT debugging hours, fewer line-side integration surprises, faster equipment acceptance.
Moat: lineage-independent engines + adversarial fixtures + normalized reply/timeout/post-state evidence, not protocol parsing alone.

## Independent RED-TEAM / VERIFIER verdict
**VERDICT: STRONG STATIC DIFFERENTIAL; DO NOT CLAIM DUPLICATE-SPECIFIC RUNTIME CONFIRMATION OR SEMI CONFORMANCE.**

The verifier attempted to disprove the Dreamine timeout prediction by locating any path where S9F7 completes the original transaction. The transport source does not: Stream-9 Function-7 is treated as an inbound primary/application message, while normal transaction completion requires F0 or the adjacent even secondary on the original stream. The existing actual-TCP malformed-W-bit test confirms S9F7 + later T3 timeout in practice for the same router catch mechanism.

The verifier attempted to disprove secsgem last-write-wins by locating schema uniqueness, duplicate validation or transactional deduplication. None was found in the exact S2F15 schema/handler. However, because the exact duplicate fixture has not been executed in the original package here, retain `SOURCE-PREDICTED` rather than `TESTED` for that specific case.

A third engine is still unnecessary until the duplicate fixture is actually executed and the disagreement is observed. If observed, use the third engine only as additional implementation evidence, not as standards authority.

## Correction to prior referral
The R12 phrase `Dreamine ... likely provides no S2F16 reply, causing host timeout` remains directionally correct about the absence of S2F16 and the timeout, but the causal description `transport dispatcher only logs the parser failure` is wrong/incomplete. The E30 router catches `E30WireFormatException` first and emits S9F7. The outer primary-dispatcher catch is therefore not the normal duplicate path.

## Commercial implication
The sellable evidence packet should normalize at least four distinct outcomes:
1. normal application secondary;
2. Function 0 transaction termination;
3. correlated Stream-9 protocol error;
4. eventual transaction timeout;
plus deterministic post-state readback.

This avoids collapsing a protocol error that still leaves the requester waiting into a generic `rejected` status.

## Candidate reusable search lesson
### PARSER -> ROUTER -> TRANSACTION-LIVENESS TRACE
WHEN TO USE: protocol stacks where malformed/duplicate inputs may trigger application ACKs, protocol-error messages or transaction timers.

PROCEDURE:
1. trace wire/schema decode;
2. trace router-local exception conversion;
3. trace actual transport classification of the generated error message;
4. verify whether that message closes, aborts or leaves the original transaction pending;
5. inspect an actual transport test for reply/error + timeout behavior;
6. only then define the buyer-visible outcome.

WHY IT WORKED: stopping at the outer dispatcher produced a wrong causal model. The intermediate E30 router converted the parser error to S9F7, while transaction semantics independently kept the original W-bit request open until T3.

FAILURE MODES: assuming any correlated error closes a request; reading only downstream ACK mappings; conflating a wire-visible protocol error with application-level transaction completion.

STATUS: candidate only. This extends the prior `PARSER -> HANDLER -> REPLY REACHABILITY TRACE` lesson but still needs a distinct second protocol-lane confirmation before promotion to SEARCH_SKILLS.md unless Hunt 15 approves.

## Knowledge-to-Value handoff
1. **CAPABILITY DELTA** — CAP-014 can distinguish wire error evidence from transaction completion/liveness and verify both against post-state.
2. **GRAPH EDGE** — EXP-008's SECS/GEM discriminator is now sharper: `S9F7 + T3 timeout + unchanged state` versus `S2F16 EAC0 + last-write-wins` is the predicted outcome matrix.
3. **RADAR SIGNAL** — RAD-007 gains evidence that virtual-FAT moats require error-path/liveness semantics, not only state-machine coverage.
4. **EXPERIMENT IMPACT** — no more generic SECS/GEM discovery before this exact duplicate fixture is executed. Record reply class, correlated System Bytes/header, T3 behavior and post-state on both engines.
5. **COMMERCIAL IMPACT** — buyer report can expose a class of integrations where an equipment endpoint emits an error yet leaves the host request hanging until timeout, a materially different FAT failure from explicit rejection.
6. **NEGATIVE KNOWLEDGE** — a parser failure is not necessarily swallowed by the transport dispatcher; intermediate routers may emit protocol errors, and correlated errors do not necessarily close transactions.

## Exact next question
When the exact duplicate-ECID S2F15 fixture is executed against both pinned packages, does Dreamine reproduce the statically/test-backed `correlated S9F7 + unchanged EC state + T3 timeout` path while secsgem returns `S2F16 EAC0 + second-value-wins`, and if so which customer-authorized profile/authority should determine expected behavior?
