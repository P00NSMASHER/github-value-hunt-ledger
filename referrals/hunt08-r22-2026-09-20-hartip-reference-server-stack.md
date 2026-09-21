# Hunt 08 Referral — HART-IP Reference Server Stack / Pre-FAT Gap

Date: 2026-09-20
Node: 08 — Protocol Moats
Ledger HEAD immediately before write: `899b5bbd7d63081422056be2651c98670b1980f4`

## HYPOTHESIS
A server-side HART-IP implementation with real device/application separation, subscriptions, burst delivery, audit/security paths, and a swappable simulator/gateway app can close the current client-only HART-IP gap in CAP-014 and become a high-value pre-FAT fixture when paired with an independent client.

## BEST FIND
### FieldCommGroup/hipserver + FieldCommGroup/hipflowapp
- hipserver exact revision: `8c5b565a93c3bb50a8eec47df62d2b3ea2edd45c`
- hipflowapp exact revision: `1c5b22112b95f4e7e14cb62539c3806f98040c1e`
- companion developer-kit docs: `FieldCommGroup/HART-IP-Developer-Kit@d1bdc81524edf8e35e840e604df909bff29437bc`
- public license: Apache-2.0 for both code repositories (actual LICENSE files inspected; GitHub metadata for hipserver incorrectly reports NOASSERTION)
- score: 24/30 — A3 B4 C5 D5 E3 F4
- status: STRONG COMPONENT / WATCH, not a conformance oracle

## DISCOVERY MODES
1. Direct domain/problem search: HART-IP server/device simulator and HART-IP pre-FAT infrastructure.
2. Analog/missing-edge search: existing `f0rw4rd/hartip@29d56ab6b6afa6aee47d85cf75d815da4ef6becf` is a client-only v1/v2 library with TLS, Direct PDU, Audit Log and integration-test hooks requiring a server; searched specifically for the missing server side.
3. Code-level + organization graph: traced FieldComm Group server source, developer kit, and companion flow-device app; inspected current source, history, license, and test surface.

## SOURCE / SCHEMA / TEST / HISTORY VERIFICATION
### Source
`hipserver` README and source show a client-facing HART-IP server with configurable concurrent clients, published-message subscriptions, burst delivery, HART-IP/HART framing, token-passing communication to a companion app, audit log, syslog, read-only command policy, TCP and UDP handling. The architecture explicitly allows replacing the companion app with a wired-device pass-through, device simulator, or I/O/gateway implementation.

`hssubscribe.cpp` contains actual subscription-table state and sends published responses only to matching subscribed clients while updating audit back-counters. `hsauditlog.cpp` implements bounded session/audit records and message counters.

Transport security is implemented despite a stale README known-issue sentence claiming security is not implemented. `onetcpprocessor.cpp` creates an OpenSSL TLS server context, requires TLS 1.2+, performs `SSL_accept`, and routes reads/writes through SSL for secure sessions; PSK/SRP callback plumbing is present. `hsudp.cpp` contains DTLS server handling. The Developer Kit independently documents HART-IP v1/v2 plus TLS/PSK or SRP and DTLS/PSK or SRP.

### Device/application implementation
`hipflowapp` plus `hipserver` forms a complete Raspberry-Pi HART-IP flow device. The app implements HART command/data behavior and physical ADC/DAC integration, and therefore gives a real stateful endpoint scaffold rather than a parser-only server.

### Tests / evidence limits
The repository tree contains extensive bundled `safestringlib` unit tests, but no similarly obvious first-party automated HART-IP semantic/integration test suite was observed for the server itself. Do not count the bundled safe-string tests as HART-IP protocol evidence.

The `hipserver` README is stale in two important places: it says security is not implemented even though current source clearly contains TLS/DTLS and security configuration code; it also says there is no released HART-IP device test specification. As of September 2026, FieldComm Group publishes `FCG TT20008 Rev. 1.0` as the HART-IP Server Test Specification, and HART Test System 4.0 (March 2026) references HART-IP registration/test procedures. Therefore README claims must not be used as current authority.

### History
Current hipserver HEAD at inspection is `8c5b565a...` (2026-04-15, CR 889). That commit changes expanded-command response handling/checksum behavior in `AppConnect/tppdu.cpp`, showing the framing layer is still receiving maintenance in 2026. `hipflowapp` is older (`1c5b2211...`, 2023-06-08), so current server evolution is not matched by equally recent device-app evolution.

## INDEPENDENT COMPARATOR
`f0rw4rd/hartip@29d56ab6b6afa6aee47d85cf75d815da4ef6becf` is an independent pure-Python HART-IP client only. It supports v1 plaintext TCP/UDP and v2 TLS, Direct PDU and Audit Log, and explicitly provides integration tests that require a HART-IP server. This makes it a useful independent requester for a neutral differential harness, while FieldComm's own clients remain same-lineage comparators rather than independent oracles.

## RED-TEAM / VERIFIER VERDICT
**STRONG COMPONENT; NOT STRONG ENOUGH FOR MASTER AS A STANDALONE PRODUCT OR CONFORMANCE ORACLE.**

Strongest objections that survived:
- The main server README is partially stale and contains statements contradicted by current source and current FieldComm documentation.
- No robust first-party HART-IP semantic test suite was observed in the server repository; current public test specifications are separate standards/test assets with their own access/rights and cannot be assumed bundled with the code.
- `hipflowapp` documents incomplete behavior: tertiary totalizer missing, on-change burst trigger missing, some data types blank, burst combinations not fully tested, no automatic power-cycle recovery, and no write-protect support.
- `hipserver` itself documents malformed Token-Passing PDU checking as incomplete.
- Standards-body lineage makes the implementation highly useful as a reference-shaped endpoint but not independent evidence of universal interoperability.

VERDICT: use as one endpoint/fixture in differential pre-FAT, never as the only oracle. Runtime differential execution against the independent Python client is still NOT_RUN in this hunt cycle.

## COMMERCIAL EVALUATION
BUYER: HART instrument OEMs, WirelessHART/HART-IP gateway vendors, remote-I/O vendors, process-automation integrators and protocol test labs.

PAINFUL PROBLEM: client/server, subscription, burst, audit, security and device-state incompatibilities are expensive to discover only when real instruments/gateways and test hardware are available.

FIRST PAID WEDGE: fixed-price **HART-IP Virtual Device Pre-FAT** — instantiate a customer-specific simulated Flow Device/gateway profile on the FieldComm server scaffold, run an independent requester corpus, and return a replayable evidence pack covering session setup, TLS/DTLS policy, direct/token-passing messages, subscription/burst behavior, audit evidence, malformed framing, timeout/reconnect behavior and state transitions.

MONEY PATH: reduced lab time, fewer hardware-dependent integration cycles, earlier interoperability defect discovery, faster OEM/gateway releases.

BUILD COMPRESSION: likely months. The stack supplies concurrent connection/session handling, TCP/UDP and secure transport paths, HART-IP framing, subscription fanout, audit/syslog, command routing and a complete stateful field-device example.

MOAT: customer-profile-derived device behavior + independent client/server lineages + adversarial error/lifecycle corpus + current test-authority mapping. The open server code alone is not the moat.

RIGHTS / PROVENANCE: Apache-2.0 code. HART specifications, HART-IP Server Test Specification, certification procedures, trademarks, EDD assets and any member-only materials remain independently owned and require separate rights/access; do not infer rights from the code license.

## KNOWLEDGE-TO-VALUE HANDOFF
1. CAPABILITY DELTA: closes CAP-014's HART-IP server-side endpoint gap with a stateful, swappable server/app architecture.
2. GRAPH EDGE: `f0rw4rd/hartip client -> hipserver/hipflowapp server -> CAP-014 -> EXP-008`.
3. RADAR SIGNAL: supports RAD-007/customer-profile-derived virtual commissioning in a new industrial protocol family; server/app separation is well-suited to profile-derived simulators and gateways.
4. EXPERIMENT IMPACT: add a HART-IP differential slice only after the current SECS/USP corpus bottlenecks are cleared; use a neutral wire recorder and independent client, not FieldComm-only tooling.
5. COMMERCIAL IMPACT: creates a credible HART-IP virtual-device/gateway pre-FAT wedge for a niche but high-cost industrial buyer group.
6. NEGATIVE KNOWLEDGE: do not equate a standards-body repository, an outdated README, or bundled utility-library tests with current conformance evidence.

## SEARCH POLICY LESSON (CANDIDATE ONLY)
**STALE README -> SOURCE + CURRENT AUTHORITY TRIANGULATION**
When a protocol repository's README is older than active source/history, explicitly compare README claims against implementation and the current standards/test-authority site. This hunt caught two materially stale statements (security implementation and test-spec availability). Keep this as a candidate lesson; do not promote to SEARCH_SKILLS.md until it succeeds on a second distinct benchmark task or Hunt 15 approves it.

## NEXT HIGHEST-VALUE QUESTION
Can the current `hipserver@8c5b565a...` + a simulation-oriented companion app be executed against `f0rw4rd/hartip@29d56ab6...` with a neutral packet/state recorder to produce a reproducible differential corpus for TLS/session, Direct PDU, Audit Log, subscription/burst and malformed-frame behavior?