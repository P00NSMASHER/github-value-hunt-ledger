# Hunt 13 R18 — Late payout return readback and revocable-finality gap

Date: 2026-09-20
Lane: Revenue Leverage
Primary experiment: EXP-003 Partner / Commission Payout Acceptance Test
Capability edges: CAP-018 payout ambiguity/finality; CAP-019 source-observation authority
Execution slot: SLOT-03 / ASSIGN:083df27963a9:slot-03

## Why this run

Current EXP-003 frontier is not another commission formula engine. The unresolved seam is whether a payout that has already reached a success state can be independently re-observed later, demoted when the provider/bank reports a failure/return, and economically unwound without rewriting history or recomputing the original earning under current rules.

## BEST NEW FIND — Polar

### polarsource/polar
- Canonical: https://github.com/polarsource/polar
- Exact revision: `7115a0d76944a4b256bada1c52f33a9727f6d3c0`
- Public license: Apache-2.0
- Score: **26/30** (A4 B5 C5 D3 E5 F4)
- Evidence state: IMPLEMENTED; source-inspected beyond README. Provider sync/reclassification path is implemented. Full automatic economic unwind after a late post-success provider failure is NOT yet verified.

### Verified implementation
1. Stripe `payout.updated`, `payout.paid`, and `payout.failed` webhook actors all route to `payout_service.update_from_stripe`.
2. `PayoutService.update_from_stripe` maps Stripe `paid` to internal attempt `succeeded`, Stripe `failed`/`canceled` to attempt `failed`, and stores arrival time for success.
3. `PayoutService.sync_with_provider` independently re-reads the latest payout attempt from Stripe with `get_payout(processor_id, connected_account)` and applies the same state mapper. This is important because it can rediscover provider state even when a webhook is missed.
4. `PayoutAttempt` is not modeled as immutable once succeeded. The database trigger recomputes the parent Payout after every attempt INSERT/UPDATE. If the only previously-succeeded attempt is later updated to failed, `has_succeeded` becomes false and `all_failed` true, so the parent payout becomes failed.
5. Separate transaction-layer support exists for `payout_reversal` counter-transactions, with a tested/reused reversal mechanism in payout cancellation paths.

### Strongest limitation / red-team result
The inspected code does **not** yet prove that a provider-driven `succeeded -> failed` demotion automatically creates the corresponding payout-reversal ledger transaction, restores merchant economic availability, or re-opens the exact historical obligation. `sync_with_provider` is exposed as a backoffice action; this run did not verify a scheduled job that continuously re-reads already-succeeded payouts. Therefore Polar supplies a strong **independent provider-readback + revocable status primitive**, not the full EXP-003 conjunction.

### Commercial implication
This is the missing evidence primitive for a Commission Payout Assurance diagnostic: re-query the provider for a payout previously treated as successful and prove whether success still holds. The paid wedge can flag `internal paid / provider failed`, missed-webhook failures, and payout states that have drifted since the original close.

## OTHER STRONG CANDIDATE — Makolo

### TraditionLearningCommunity/makolo
- Canonical: https://github.com/TraditionLearningCommunity/makolo
- Exact revision: `8ef40aa16e7367f13b0a5df7941057b68a8a242f`
- Public license: none detected (`license: null`; no root LICENSE at inspected revision)
- Score: **25/30** (A4 B4 C5 D4 E5 F3)
- Evidence state: IMPLEMENTED + TESTED in repository source; no hosted CI run was found for this exact head during this pass.

### Verified implementation
1. Settlements are built from append-only ledger entries, netting positive and negative economic positions. A negative payee position is carried forward as recoverable rather than paid.
2. Payout creation protects against an already-successful sibling payout and supports idempotency keys/attempt numbering.
3. `mark_payout_succeeded` locks payout/settlement state, consumes a provider `source_key` once, appends one `PAYOUT` FundMovement, and marks settlement settled.
4. `reverse_payout` accepts only a previously SUCCEEDED payout, is replay-safe by `source_key`, moves it to REVERSED, and appends a separate `PAYOUT_REVERSAL` FundMovement for the exact negative payout amount/currency/provider reference.
5. The historical settlement deliberately remains SETTLED. The reversal is a new auditable cash fact; future recovery/offset is driven by ledger facts rather than rewriting old history.
6. Tests verify: positive+negative settlement netting; negative-only carry-forward; failure->retry->success idempotency; a refund after payout becoming recoverable without mutating the old payout; payout reversal producing original+reversal movements; and immutability of succeeded payout terms.

### Strongest limitation
Makolo does not supply the external observation mechanism that discovers a missed late provider/bank return. It also does not re-open the old settlement for exact re-pay; its design carries the negative cash fact forward into future economics. It therefore complements, rather than replaces, Familiarise-style original-earning reopen logic.

## NEGATIVE ORACLES DISCOVERED

### UjjwalCodes01/RemitChain@5fc8dc0ba432f1d0364ee9d3c579a70eb53570bb
Strong one-send/idempotency and in-flight reconciliation, but its core explicitly states that a terminal payout is final and that late conflicting provider results are ignored: `if (isTerminal(from)) ... return`. Its reconciler scans only in-flight statuses. This is an excellent EXP-003 mutant: a technically careful payout engine can still encode an unsafe **terminal-success doctrine**.

### Harshit-sehgal/promptpay@d1d449974a95b5bd8a3d1e4ad76216060c912060
Robust processing-state reconciliation: periodic provider polls, external-reference lookup when provider transaction ID is missing, retained ambiguous fences, escalation, attempt logs, and amount/currency self-checks. But the scheduled query is for `PayoutStatus.PROCESSING`; already-PAID payouts are not continuously re-observed for a late provider reversal. Useful negative oracle for **good in-flight recovery but no post-success observation**.

## Cross-source verification

Current Stripe support material confirms the economic premise: a failed payout means the receiving bank could not receive it and sent the funds back to Stripe; missing payouts can remain in bank processing after funds have left Stripe; payout reconciliation requires tracking the actual bank deposit/trace and exceptions. This means a durable `paid` flag cannot safely be treated as permanent finality without later observation authority.

## COMBINATION

Best current conjunction:

`historical earning authority`
→ `one-use payout claim / ambiguous-send protection`
→ `provider payout identity`
→ **Polar independent provider re-read after apparent success**
→ `late failed/returned state`
→ **Makolo append-only payout-reversal cash fact / carry-forward recovery**
→ `Familiarise exact historical earning re-open + future rebatch`
→ `independent bank/network observation for final acceptance`.

No single inspected repository proves this entire path yet.

## EXP-003 DELTA

Add/retain these adversarial cases:
1. provider webhook says PAID, later provider API says FAILED;
2. payout.paid webhook is received, payout.failed webhook is permanently lost, provider API later reports failed;
3. terminal-success engine ignores late FAILED/RETURNED result (must fail acceptance);
4. in-flight-only poller never re-observes a previously paid payout (must remain UNKNOWN after the observation horizon, not VERIFIED);
5. late return creates exactly one economic counter-event;
6. replayed late return does not double-credit/debit;
7. return after plan/rate change must not recompute historical earning under the new plan;
8. economic reversal may be represented as exact obligation reopen or negative carry-forward, but provenance must preserve original payout/earning authority;
9. provider status demotion without corresponding economic ledger compensation must be flagged inconsistent;
10. status/ledger contradiction must not be reported as realized money.

## VALUE HANDOFF

### 1. Capability delta
CAP-018 gains an independently verified provider re-read primitive that can revise a previously-successful payout attempt. It also gains a strong append-only post-success reversal/carry-forward pattern from Makolo.

### 2. Graph edge
Strengthens CAP-018 -> EXP-003. Polar closes part of the observation edge; Makolo strengthens the counter-event/economic-compensation edge. Neither alone closes the full bank-finality path.

### 3. Radar signal
Strengthens RAD-006 / authority-aware money assurance: success must remain revocable when authoritative downstream evidence changes.

### 4. Experiment impact
EXP-003 should explicitly test post-success provider re-read and require the status correction and economic compensation to stay synchronized.

### 5. Commercial impact
New measurable exception class: **paid-state drift** — dollars marked paid internally whose provider/bank state later contradicts that conclusion. Buyer: controller/finance ops/RevOps at firms paying commissions, sellers, contractors, affiliates, or service providers. First paid wedge: read-only payout-integrity audit over historical provider exports/API data plus internal payout/commission records.

### 6. Negative knowledge
- In-flight reconciliation is not post-success reconciliation.
- A terminal `PAID` state is unsafe when the external rail can later fail/return.
- Status demotion alone is not enough; economic ledger compensation must follow.
- Append-only reversal alone is not enough if no independent observer can discover the reversal.

## NEXT HIGHEST-VALUE QUESTION

Can one production implementation prove the full conjunction `previously succeeded payout -> independent scheduled provider/bank re-read -> late return/failure -> exact one-use economic counter-event -> historical earning/obligation re-open or carry-forward -> safe future repayment`, including the case where the late webhook is permanently lost?
