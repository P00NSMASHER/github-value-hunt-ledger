# Hunt 13 R15 — EXP-003 provider→bank acceptance matrix

Date: 2026-09-20
Lane: Revenue Leverage / Partner & Commission Payout Assurance
Status: **synthetic acceptance matrix executed; experiment sharpened, not externally commercially validated**

## Why this run changed direction
The current SEARCH_QUEUE and EXPERIMENTS files explicitly say to stop broad commission/payout/reconciliation discovery and execute EXP-003. This run therefore did not add another payout repository. It converted the accumulated provider/bank/return evidence into a falsifiable provider-neutral acceptance matrix.

## Reference contract
A payout is not buyer-grade realized money merely because the commission engine, payout provider, ERP ledger, ACH trace, or bank connector says success. The reference state machine separates:

1. **Authority** — entitlement/plan/assignment is VERIFIED or REVIEW.
2. **Provider outcome** — NOT_SENT / UNKNOWN / DEFINITE_REFUSAL / CONFIRMED.
3. **Independent bank observation** — EXACT_UNIQUE / AMBIGUOUS / NOT_FOUND / UNAVAILABLE.
4. **Observation coverage** — VERIFIED_WINDOW / STALE / INITIALIZING / PARTIAL / UNAVAILABLE.
5. **Economic identity** — unique identity plus amount, currency and time compatibility.
6. **Return/reversal observation** — EXACT_UNIQUE / AMBIGUOUS / VERIFIED_EMPTY / NOT_FOUND / UNAVAILABLE.
7. **Return-window coverage** — the source window through the reporting cutoff must itself be verified before an absence claim can make the payout currently realized.

### Money-bearing rule
`REALIZED_SETTLED` is allowed only when:
- entitlement authority is verified;
- provider outcome is confirmed without an unresolved duplicate-send ambiguity;
- bank observation is EXACT_UNIQUE inside a VERIFIED_WINDOW;
- amount/currency/time compatibility hold; and
- the relevant return/reversal window is VERIFIED_WINDOW with an explicit VERIFIED_EMPTY observation.

`NOT_FOUND` is **not** promoted to `VERIFIED_EMPTY` automatically. Stale/partial/unavailable coverage contributes `$0 realized` in the assurance report even when a local sync job succeeded.

A later exact Return/Reversal creates one counter-event and revokes current realized finality without deleting the original settlement event. An ambiguous return routes to review and does not auto-unwind. A duplicate semantic return must not double-unwind.

## Executed corpus
The local reference execution covered 24 cases:

- happy-path realized settlement;
- unresolved authority;
- provider UNKNOWN with no retry;
- attempted duplicate send while provider outcome is UNKNOWN;
- definite provider refusal and safe release;
- later contradiction of an earlier definite refusal;
- duplicate-trace ambiguity;
- provider-complete / bank-absent;
- unavailable bank source;
- stale bank cursor/window;
- partial bank window;
- unparseable amount / amount mismatch;
- currency mismatch;
- time incompatibility;
- bank-posted then returned;
- duplicate semantic return;
- ambiguous return;
- unavailable return source;
- stale return window;
- `NOT_FOUND` without a VERIFIED_EMPTY receipt;
- equal totals with swapped identities;
- substring/fuzzy reference collision;
- first-unmatched-row trap;
- verified-empty return window happy path.

Reference execution result: **24/24 matched hand-authored expected classifications; unsupported realized dollars = $0.**

Deterministic result digest from the executed reference output:

`7d24e0c5e0cce2ffac5b40590bf346c273639422c0e8a28ce6c0072af491474d`

## Test-the-test / mutation evidence
To avoid a circular green matrix, six deliberately unsafe evaluators were introduced. Every one was killed by at least one planted case:

- **provider_status_is_finality** — caught by 17 cases.
- **ambiguous_first_match** — caught by 4 cases.
- **cursor_continuity_equals_completeness** — caught by 2 cases.
- **not_found_equals_verified_empty** — caught by 2 cases.
- **ignore_later_return** — caught by 6 cases.
- **amount_only_identity** — caught by 14 cases.

This is the most important result of the run: the corpus can distinguish the intended fail-closed policy from several plausible but economically unsafe alternatives.

## Concurrency / one-use checks
A two-writer claim race was repeated **200 times** against the reference one-use claim primitive. Exactly one contender won each race; observed race violations: **0/200**.

The return counter-event primitive was also exercised with the same return identity twice. First application posted `-10000` cents; the replay was rejected; total counter-event remained `-10000` cents rather than `-20000`.

## New EXP-003 acceptance decision
The experiment should explicitly separate **observed settlement** from **currently reportable realized settlement**.

A bank transaction can be independently observed and therefore be stronger than provider status while still not qualify as buyer-grade current realized money if the return/reversal observation window through the report cutoff is stale, partial or unavailable. This is stricter than treating bank-posted as terminal finality and directly incorporates CAP-019 source-authority receipts into CAP-018.

Recommended decision surface:

- `OBSERVED_SETTLEMENT = true/false`
- `CURRENT_REALIZED = amount | 0`
- `SETTLEMENT_MATCH = EXACT_UNIQUE | AMBIGUOUS | NOT_FOUND | UNAVAILABLE`
- `SETTLEMENT_COVERAGE = VERIFIED_WINDOW | STALE | INITIALIZING | PARTIAL | UNAVAILABLE`
- `RETURN_STATE = EXACT_UNIQUE | AMBIGUOUS | VERIFIED_EMPTY | NOT_FOUND | UNAVAILABLE`
- `RETURN_COVERAGE = VERIFIED_WINDOW | STALE | INITIALIZING | PARTIAL | UNAVAILABLE`
- `RETRY_ALLOWED = true/false`
- `CLAIM_LOCKED = true/false`
- append-only original settlement and counter-event identities.

## Commercial effect
The closed-month Commission Payout Acceptance Test can now sell a much more precise result than “we recalculated your commissions.” It can classify each payout into:

- entitlement/authority unresolved;
- provider outcome unresolved;
- provider refused and safely releasable;
- provider confirmed but no independent bank observation;
- bank mapping ambiguous;
- bank-observed but return-window coverage not strong enough for a realized-money certificate;
- realized and current as of a verified observation window;
- later returned/reversed;
- duplicate-send / duplicate-return control breach.

The monetary output should report only the final realized bucket; review/unknown categories remain `$0 realized` while still exposing risk dollars operationally.

## Capability / graph handoff
- **CAPABILITY DELTA:** CAP-018 + CAP-019 now have an executable provider-neutral decision contract rather than a list of component semantics.
- **GRAPH EDGE:** strengthens `CAP-019 -> CAP-018 -> EXP-003 -> Commission Payout Acceptance Test`.
- **RADAR SIGNAL:** strengthens RAD-006 authority-aware money assurance; no score increase is justified from synthetic evidence alone.
- **EXPERIMENT IMPACT:** EXP-003 can move from open-ended component research to execution against real provider/bank adapters or a frozen customer month.
- **COMMERCIAL IMPACT:** the wedge can distinguish unsupported `paid` states, ambiguous bank mappings, stale-source false finality, later returns and unsafe retry/reissue exposure.
- **NEGATIVE KNOWLEDGE:** provider success, cursor continuity, bank transaction presence, trace/reference equality, equal totals and raw `NOT_FOUND` are each insufficient alone for a current realized-money certificate.

## Next highest-value action
Run this exact matrix against one concrete provider/bank adapter pair (Modern Treasury or equivalent) using synthetic/sandbox fixtures, then on one customer-authorized closed month. Only search again if an actual adapter failure exposes a missing semantic.

## Durable executable artifact
`referrals/hunt13-r15-2026-09-20-exp003-provider-bank-matrix.py`
