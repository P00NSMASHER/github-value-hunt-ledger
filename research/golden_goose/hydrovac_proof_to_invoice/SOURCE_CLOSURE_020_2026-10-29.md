# Golden Goose #020 — upstream quantity-to-money provenance closure
Date: 2026-10-29 EDT. Research only; WATCH. No production/customer authority.

## Verified starting point and evidence
- Durable candidate ledger: https://github.com/P00NSMASHER/github-value-hunt-ledger/issues/863
- Existing draft PR (unmerged): https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/870
- Reviewed exact pre-patch bridge blob: `288b394b9b6aa69412c9317e877254a4d20e1dec`; posted amount guard blob: `288f4281aba8d8a901362bcd1588a9da5143ecaf`.
- Official Worcester public procurement listing (2026, two awarded bidders): https://www.worcesterma.gov/finance/purchasing-bids/bids/cr-8693-j6 . Bid comparison amounts are not work orders or receipts.
- Competitor checks, public pages accessed on 2026-10-29: https://fortressticket.com/ (vendor advertises AI ticket/invoice matching, duplicate guard, 30-day trial up to 1,000 tickets, then $0.25/ticket) and https://aimsio.com/features/tickets/ (vendor advertises signed ticket-to-invoice rate books). Marketing, NOT independent tests of their products or proof of our buyer demand.

## Falsification
Hypothesis: a `CLEAR_RECONCILED` quantity row was sufficient input for a synthetic arithmetic-clear label if the separate posted amount proof passed.

Independent 18-case synthetic mutation challenge against the previous bridge:
- 11/18 misleading/contradictory inputs returned `SYNTHETIC_ARITHMETIC_ONLY` even when the upstream quantity row had an undisclosed waiver, credit or discount field, or summary counters contradicted the rows.
- 7/18 were already routed to `REVIEW`.
- None asserted any real receivable or user revenue: a synthetic arithmetic-clear is *not* a debt, payment, collection, or revenue milestone. But it is an unsafe missing-evidence signal in the audit interface.

## Actual repair and measurements
- On existing **DRAFT PR #870 branch only**, the bridge now fails closed on unmodeled quantity summary/row fields, invalid statuses and monetary shapes, contradictory aggregate counts, nonzero clear/review variances, and mismatched candidate-gross arithmetic.
- Updated bridge blob: `85c718960a314b2b9e2d4454ff918c2989fbf930`; original fix commit `8851222622be06ca82aa362f079263ef2b2aad59`.
- New frozen executable source: `test_quantity_source_closure_020.js`. **20/20** in-process V8 checks passed (**18 adversarial review**, **1 valid native-format arithmetic-only**, **1 candidate review**), plus all **28/28** existing bridge checks. Exactly **18/18** mutations now routed to review; no money assertions. Tests ran against connector-readback source, not against a customer or incumbent environment.
- Node CLI, end-to-end Python 100-job JSON integration, GitHub CI for the final head, signed source authentication, real customer invoices and independent software comparison were **not** established by these tests.

## Adversarial commercial gate
FortressTicket's listed $0.25/ticket means $100 equals its *advertised variable fee* for 400 tickets, while the marketing offer includes a trial up to 1,000 tickets. It is **not an apples-to-apples quote for a forensic post-billing audit**, but creates a serious buyer-value hurdle for a generic reconciliation service. No independent incumbent testing has shown a missed, legally collectible invoice.

Hypothetical $100 audit economics with $10 overhead and $35/hour reviewer labor: 2 hours => $20 contribution; 3 hours => -$15, excluding sales, platform costs and tax. A market or public contract value is **not** collectible recovery. Synthetic gross variance is **not** customer savings and neither is the owner's revenue.

**Disposition:** generic field-ticket reconciliation SaaS = NO-GO; source-bounded second-look contract audit = WATCH. No change to integrator priorities. **Verified user revenue $0; collectible recovery $0; customers 0; authorized real invoices 0.**

## Cheapest next falsifiable experiment
Run the frozen 100-job Python fixture through the updated JavaScript bridge, with posted-proof sidecars generated without using the target expected labels; measure arithmetic-only false-clears and review burden. Then attempt a strictly public feature comparison: do not infer actual incumbent false negatives from promotional websites. Any real invoice comparison or sale needs fresh express approval and lawful buyer authorization. Do not send outreach, spend funds, file claims, touch private data, activate services, promote worker status, or merge protected main.
