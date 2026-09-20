# Cross-lane referral — Hunt 01 Run 20 — 2026-09-20

## To
Money-State / Payment Integrity / Partner-Commission Payout Assurance integrator.

## Candidate
`hands-platform/hands-app@64cddd8261fc649b6b5d9365fbe67875de3875e3`

## Why this matters
The repository now supplies a rare bank-evidence/counter-event reference for CAP-016/CAP-018 and EXP-003/EXP-010:

- `apps/api/src/settlements/historical-settlement-reconstruction.ts` reconstructs a paid historical settlement from retained earning, exact fee/tax logs, policy-version/rule snapshots, captured payment, completed booking and wallet lifecycle; ambiguity/mismatch fails closed.
- `infra/scripts/provider-payout-reversal-lifecycle-smoke.mjs` proves original payout accounting plus bank outflow reconciliation, then a returned-bank-transfer reversal with separate approval, stable reversal reference, exactly one inverse accounting journal, wallet restoration, separate returned-bank-inflow evidence and reconciliation back to the reversal journal/payout batch.
- The original earning/batch remain PAID while the later return is represented through compensating ledger evidence rather than history rewrite.
- Separate refund-after-paid tests create partner-receivable/clawback evidence, supporting reason-aware separation between `BANK_RETURN_STILL_OWED` and `REFUND_CLAWBACK_NOT_OWED`.

## Important limitation
The payout-return correction is still initiated through an explicit finance/admin reversal path. This does **not** prove automatic independent discovery of a late return after local PAID when the reversal webhook is permanently lost. It also does not yet prove that a subsequent re-payment consumes the restored historical obligation exactly once without reconsulting changed current policy.

## Exact unanswered technical question
**After a returned-bank inflow and compensating wallet adjustment, can a subsequent payout be created exactly once from the restored historical obligation while current service/fee/tax policy has changed, using only the original earning/rule authority rather than current policy—and can the same correction be triggered from independent provider/bank readback if the post-success webhook never arrives?**

## Suggested EXP-003 / EXP-010 fixture
1. Create earning under policy/rate A and retain exact authority snapshot.
2. Change current policy/rate to B.
3. Pay the original earning and reconcile the bank outflow.
4. Suppress the provider reversal webhook.
5. Inject independently observed bank/provider return evidence with exact prior payout identity.
6. Classify it as `BANK_RETURN_STILL_OWED` rather than refund/clawback.
7. Require exactly one compensating reopen / wallet restoration.
8. Re-pay exactly once and assert amount/authority still equal A.
9. Replay the return and re-pay triggers; assert no duplicate economic effect.
10. Run a sister case classified `REFUND_CLAWBACK_NOT_OWED`; assert it does not create re-payment eligibility.

## Cross-check negative oracles from the same run
- `chase-sets/chase-sets@baf0106...`: scheduled reconciliation selector excludes terminal completed payouts.
- `web098cros7/Towing@ff48364...`: scheduled reconcile starts from `staleNonTerminal`, so post-PAID contradiction is invisible.
- `OxyHQ/Mercaria@fabf24d...`: strong semantic oracle that downstream connected-account payout failure does not automatically mean the merchant earning should reopen; cash location and underlying entitlement are distinct.
