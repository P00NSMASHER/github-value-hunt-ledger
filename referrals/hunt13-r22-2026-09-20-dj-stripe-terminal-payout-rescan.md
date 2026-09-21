# Hunt 13 Referral — dj-stripe Terminal Payout Rescan

Date: 2026-09-20
Node: 13 — Revenue Leverage
Ledger HEAD immediately before write: `005e9954cbe2ee83adf37cd8cd2b15e9454cbb6f`

## REFERRAL
**Target lanes:** Commission / payout assurance, finance/payments, accounting close.

### Candidate
`dj-stripe/dj-stripe@40882bbcd7e44710244372dec44d9f0e494c7432`

### Why this matters
CAP-018's current bottleneck is rediscovering a payout contradiction **after local success** when the late webhook is permanently lost. dj-stripe provides a mature provider-mirror primitive whose bulk sync lists provider objects without filtering on local payout status, and its tested `sync_from_stripe_data()` path updates an existing object by Stripe identity rather than duplicating it.

This is a materially better architecture for a terminal-state sensor than an in-flight-only poller. It can be scheduled to re-list Stripe `Payout` objects even when the vertical application already believes them paid.

### Evidence
- `djstripe/management/commands/djstripe_sync_models.py`: model-level sync enumerates Stripe provider lists; selection is by supported model/list capability, not local payout state.
- `tests/test_stripe_model.py`: regression test proves an already-persisted Stripe object is updated on later sync and remains one row.
- `tests/test_sync.py`: explicit `fail_on_error=True` produces `CommandError`; restricted-key regression proves the sync actually executes rather than silently doing no work.
- `djstripe/models/core.py` / `tests/test_payout.py`: Payout model carries provider payout state plus failure/reversal lineage fields. Reverse-operation behavior itself remains under-tested.
- Public license: MIT.
- Repository exact revision: `40882bbcd7e44710244372dec44d9f0e494c7432`.

### Independent first-party lifecycle evidence
Stripe's current official SDK contract states that some payouts that ultimately fail may initially appear `paid` and later change to `failed`. Therefore a local terminal-success state is not sufficient evidence to stop provider observation.

## CAPABILITY DELTA
**CAP-018 gains a mature status-independent Stripe provider rescan primitive.** The key reusable ability is not generic webhook handling; it is re-observing provider truth from a population that does not depend on the local state being challenged.

## GRAPH EDGE
`dj-stripe/dj-stripe@40882bb...` -> **STRENGTHENS CAP-018** -> **STRENGTHENS EXP-003**.

It complements:
- `stripe-connect-reckon` for terminal-state provider sensing;
- CAP-019 for scan-health/freshness receipts;
- Modern Treasury / ACHInterbank for independent bank-return evidence;
- Familiarise / EruoFood-style historical earning authority for economic reopen/re-pay.

## RADAR SIGNAL
Strengthens RAD-006 Authority-aware money assurance without changing the score. The new evidence reinforces a key architectural rule: **the observer that challenges a local terminal state must not derive its observation population from that same local state.**

## EXPERIMENT IMPACT
Add this branch to EXP-003:
1. freeze earning E1 under plan V1;
2. payout P1 becomes locally/provider `paid`;
3. permanently suppress the later `payout.failed` webhook;
4. provider truth later changes P1 to `failed`;
5. scheduled provider-wide Payout rescan discovers P1 by exact provider identity and updates the existing row;
6. rescan failure/partial coverage remains UNKNOWN/UNAVAILABLE;
7. provider contradiction alone does not mint repayment authority;
8. independent bank/return evidence + still-owed classification permits exactly one reopen/compensation of E1;
9. repayment uses E1/V1, not current plan V2;
10. replay creates no second compensation.

## COMMERCIAL IMPACT
Adds a concrete **Terminal Payout Drift** exception class to the Commission Payout Acceptance Test: provider currently says failed, local commission/payroll system still says paid. Potential value includes preventing duplicate manual reissues, discovering unpaid-but-marked-paid liabilities and reducing close/reconciliation effort.

## NEGATIVE KNOWLEDGE
- Provider `paid` is not permanent finality.
- A webhook consumer is not an independent observer.
- A provider-wide rescan can still fail open if its source-health result is not elevated into a machine-readable receipt.
- dj-stripe's programmatic `call_command()` deliberately defaults to non-throwing sync failures unless `fail_on_error=True`; this must not be used as VERIFIED coverage without an explicit gate.
- Provider status correction is not beneficiary-bank finality and not economic correction.

## SCORE / VERDICT
**26/30 — A4 B4 C5 D3 E5 F5. STRONG COMPONENT, not a MASTER candidate by itself.**

It is mature and directly useful, but it does not perform the historical entitlement classification/reopen nor independently observe the beneficiary bank. The moat remains the joined assurance stack rather than this provider mirror.

## EXACT UNANSWERED TECHNICAL QUESTION
Can a production Commission Payout Assurance adapter schedule a bounded terminal-success Stripe rescan with a machine-readable completeness/freshness receipt and then join a newly discovered `paid -> failed` contradiction to exact independent bank-return evidence and the original historical earning so that exactly one correct repayment is authorized when still owed?
