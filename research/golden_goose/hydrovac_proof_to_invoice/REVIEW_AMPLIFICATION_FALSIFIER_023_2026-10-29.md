# Golden Goose iteration 023 | Duplicate-ID cohort review amplification (2026-10-29)
**Stage:** UNCLAIMED, isolated research-only experiment on existing DRAFT PR #870. No worker/lease claim, no protected-main update, no integrator priority change.

## Fresh official/public context
- City of Worcester 2026 vacuum-excavation procurement CR-8693-J6: https://www.worcesterma.gov/finance/purchasing-bids/bids/cr-8693-j6 . Bid opened 2026-04-16, closed 2026-05-13. It lists two awardees and published bid comparisons; these are **not actual contractor invoices, collectible variances, customer payments or our revenue**. Bid and signed-award scopes must not be silently conflated.
- Worcester earlier 2023 vacuum-excavation procurement CR-8017-W3: https://www.worcesterma.gov/finance/purchasing-bids/bids/cr-8017-w3 . Raw 2023 vs 2026 tender totals are **not a valid inflation or recoverable-invoice comparison**, absent common scope, quantities and executed terms. A generic public-bid price-change alert is **NO-GO** as a first-$100 route without demonstrated paid demand or authorized invoice evidence.
- FortressTicket advertises automatic ticket-invoice matching, duplicate-ticket controls and **$0.25/ticket pay-as-you-go** (https://fortressticket.com/). This is a current published *vendor claim/list price*, not an independent verification of efficacy or buyer adoption. It further undermines differentiation for generic reconciliation.

## Hypothesis and controlled falsifier
Question: Could a single repeated posted-invoice ID make our otherwise fail-closed contract-aware batch audit uneconomic at a hypothetical $100 fixed price?

New zero-dependency deterministic [synthetic test](test_blast_radius_023.js) creates **100** quantity-cleared rows with complete fictional, internally matching posted monetary proofs. Direct [#019 bridge](cohort_amount_bridge_019.js) produces **100 arithmetic-only, 0 review** in the control.

Mutate exactly one existing posted invoice-line ID on the second job to duplicate the first's. The bridge's intentional cohort-level collision safeguard then returns **0 arithmetic-only, 100 review**, although only **2 job rows directly share the conflicting identifier**. The other **98 remain conservatively held**, not shown to be incorrect. **50x review-amplification ratio** is a synthetic fail-closed workload risk, not a measured real operating cost, technical false-clear, money due or established commercial loss.

Hypothetical downside if a human investigated *every* additionally held record: 98 × 5 minutes = **490 minutes** (8 h 10 m); at $35/hour assumed labor this is **$285.83** before fixed overhead, acquisition and tax. A hypothetical $100 fixed-price report cannot cover that conditional excess-review cost. If reviewers can batch-close 98 untouched records without inspecting each, this cost model overstates reality. Both work-time and pricing assumptions remain unvalidated.

Test also asserts **zero collectible assertions, zero customer invoices and $0 owner revenue**. The “all review” behavior is conservative and may be appropriate pending global uniqueness proof; do not optimize it by allowing questionable identifiers to be cleared.

## Repository evidence and current limits
- Prior latest [Release Gate #40932468079](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/40932468079) completed **success** on **6fb293714b70e163bd5dca960c0cbd26a18c26eb**, confirming #022 integration acceptance was run in CI. This does not certify real-world financial accuracy.
- #023 added [test_blast_radius_023.js](test_blast_radius_023.js) and wired it into [CI test wrapper](../../../../tests/test_ti_golden_goose_hydrovac_integration_022.py), commits **29b55a5** and **b80cbc9**. Final #023 CI **must be separately observed**; no pass is inferred from the prior head.
- The 100 records in this test are *new deliberately synthetic records*, not customer samples, not the other frozen 100-job fixture, and not an actual incumbent comparison. All signed-rate flags are *synthetic assumptions*, not authenticated authority.

## Stop/next gate
**Disposition:** Generic hydrovac invoicing SaaS and generic public-bid monitoring remain **NO-GO**; contract-specific second-look exception audit remains **WATCH**, not promoted. A commercial wedge requires an independently authorized incumbent comparison, observed buyer willingness to pay, proof of incremental lawful variances and observed review duration. The first-dollar business case is not established.

**Next minimal experiment:** Build a *diagnostic-only* collision localization output, then adversarially test aliasing, whitespace/case collisions, split invoices, partial exports and missing job ownership. Do not upgrade any rows to arithmetic-only merely because the cross-job collision is localized. Quantify human review time using synthetic work packets first. Only with fresh explicit permission attempt a blind 100-job comparison with actual signed contracts, credit memos and incumbent controls.

**Exact financial status:** verified owner revenue **$0**; independently verified collectible **$0**; paying customers **0**; authorized real customer invoices **0**; actual incumbent head-to-head comparisons **0**. No outreach, customer ingestion, filings, payment movement, funds, subscription, trades, Work usage, duplicate issue or protected-main release.
