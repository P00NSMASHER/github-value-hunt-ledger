# Hunt 13 R17 — Event-time commission reversal / original-authority preservation

Date: 2026-09-20
Lane: Revenue Leverage / Commission Payout Assurance
Primary experiment: EXP-003 Commission plan-to-bank acceptance test

## Strong finding — pixparker/arad-crm-os

- URL: https://github.com/pixparker/arad-crm-os
- Exact revision: `abf2222879ff86f8426ff364e7ffede981930250`
- Status: **strong component / acceptance oracle; not a MASTER promotion**
- Score: **25/30 — A4 B5 C5 D4 E4 F3**
- Public license/provenance: no root public license reported by GitHub metadata at inspection time. User standing repository-code authorization applies to repo-owned code only; external services/data remain separate. Operational clarity is reduced by a submodule checkout dependency and a failing exact-head GitHub Actions checkout.

### Verified implementation evidence

1. `apps/worker/src/processor.ts` resolves the active commission plan using the economic event time: `activePlanVersion(db, orgId, paidAt)` selects the latest active version whose `effectiveFrom <= paidAt`. It does not choose the plan using current wall-clock time.
2. Earn entries are persisted with the selected immutable `planVersionId`.
3. `packages/commission/src/store.ts::reverseForPayment()` locates the original earn rows by original `paymentRef`, then appends a negative reversal per original earn with:
   - `amountRial = -earn.amountRial`
   - `planVersionId = earn.planVersionId`
   - `reversesEntryId = earn.id`
   - original account/opportunity references
   - a reversal basis naming the original entry and reason.
4. Reversal insertion is idempotent on the refund event identity; replay does not double-reverse.
5. The original earning amount is not rewritten; only its lifecycle status moves to `reversed`, with an append-only status-audit row.
6. `apps/worker/src/__tests__/processor.db.test.ts` is a real-Postgres test: a 15% plan applied to 13,500,000 net produces 2,025,000; replay remains one earn; a later refund appends -2,025,000, links the original earn, sets the original status reversed, nets seller earnings to zero, and replaying the refund still leaves only two money rows.

### Adversarial findings / limits

- This closes the **no-rerating-on-reversal** half of the EXP-003 late-counter-event requirement: a reversal copies the actual original earning and original plan-version authority rather than applying a newer plan.
- It does **not** close the remaining bank-finality gap. The counter-event is a customer payment refund, not an externally observed return of the commission payout itself.
- The state machine makes `reversed` terminal. There is no verified `reopen payable` / counter-counter-event path after a returned payout, and therefore no verified repayment path that reuses the original immutable obligation after the plan has changed.
- Exact-head GitHub Actions is not green evidence: the run for `abf222...` failed during recursive submodule checkout, so install/typecheck/tests were skipped. The source contains substantial DB tests, but hosted CI did not execute them at this exact revision.

### Why it matters commercially

This provides an unusually clean acceptance oracle for a high-value error class in Commission Payout Assurance: **historical-plan drift during clawback/refund processing**. A paid diagnostic can test whether the incumbent recomputes a clawback under today's plan versus reversing the exact historically authorized earning.

The stronger customer-facing invariant is now:

`event-time plan authority -> immutable earning -> payout -> exact external counter-event -> exact original-obligation link -> append-only reversal/reopen -> any later repayment reuses the original obligation/authority; never current-plan recomputation.`

## Complementary finding — mobazha/mobazha

- URL: https://github.com/mobazha/mobazha
- Exact revision: `2a30c669e9ff2de29ee96359e056d8b12296a249`
- License: MPL-2.0
- Status: **watch / complementary immutable-affiliate oracle**
- Score: **24/30 — A4 B4 C5 D4 E4 F3**

Verified source behavior:
- Referral sessions and immutable order attribution freeze `CommissionRateBPSSnapshot` plus payout destinations.
- Per-line commission rows retain net merchandise amount, currency, frozen rate, commission amount and reversal metadata.
- Partial refunds reverse only the exact affected order-line commission IDs; unallocated/full refunds reverse all.
- Chargeback and lost-dispute facts also reverse commissions.
- A provider-payment-risk event listener can reconcile late payment-risk facts even without a new P2P order message.

Limit: lifecycle is `pending|reversed`; no verified external payout-return -> re-open -> repay path. Valuable mainly as independent convergence on immutable authority snapshots and exact line-scoped counter-events.

## Negative / adversarial oracle — CC90210/oasis-command-center

- URL: https://github.com/CC90210/oasis-command-center
- Exact revision: `50f57adba6c645e327aa38c8861e276d883a9edf`
- Status: **watch / acceptance oracle**

Verified source/tests:
- Commission ledger persists authoritative `basis_amount_cents`, `rate_bps`, `amount_cents`, `comp_version` and append-only refund-offset rows.
- Real migration-backed libSQL tests verify that a refund writes one negative offset per accrual and replays idempotently.
- Payout workflow tests require an independently verified payment receipt before approval/payment and require a payout reference to mark a commission paid.

Limit: the payout reference is still an internal/manual terminality assertion; no independent bank/provider-return proof was established in this pass.

## EXP-003 experiment delta

Add a dedicated **counter-counter-event authority matrix**:

1. Earn under plan version V1 at event time T1; persist earning E1 and immutable plan reference V1.
2. Pay E1 and freeze the payout reference.
3. Change the active plan to V2 with a materially different rate.
4. Observe an exact late external return/reversal for the paid payout.
5. Require an append-only counter-event linked to E1/payout P1. Do not mutate E1's amount/rate authority.
6. Re-open the payable obligation, if business policy requires repayment, from E1's original obligation and V1 authority.
7. Re-pay using that same obligation identity; **V2 must never be used to recalculate the returned historical earning.**
8. Replay the return, reopen and repayment messages; each economic transition must apply at most once.
9. Reject zero/multiple candidate payout mappings as REVIEW/UNKNOWN; never first-match.
10. Keep externally observed return, internal reversal, reopened payable and re-payment as distinct evidence-bearing states.

## Commercial impact

This sharpens the Commission Payout Acceptance Test from generic 'refund/clawback correctness' to a concrete high-value control:

**Did a late payout return cause the system to recover/re-pay the exact historical obligation under the original commission authority, or did it silently re-rate the money under today's plan?**

That defect can create both underpayments and overpayments and is measurable on a frozen closed period.

## Capability / radar handoff

- Capability delta: CAP-018 gains a concrete original-authority-preserving reversal primitive; the re-open/repay half remains missing.
- Graph edge: strengthens CAP-018 -> EXP-003, specifically event-time authority + counter-event lineage.
- Radar signal: strengthens RAD-006 Authority-aware money assurance; no numeric score increase warranted.
- Experiment impact: add the 10-case counter-counter-event authority matrix above.
- Commercial impact: add 'historical-plan drift on reversal/repayment' as an explicit recovered-dollar exception class.
- Negative knowledge: a correct reversal does not prove a correct returned-payout recovery flow; a terminal `reversed` state can itself conceal the absence of an authority-preserving re-open path.

## Next highest-value question

Can a production implementation prove `external payout return -> exact prior payout/earning -> append-only re-open -> re-pay from the original immutable plan/earning authority` after the active commission plan has changed, without recomputation under the new plan?
