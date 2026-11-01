# Golden Goose #015 | Worcester 2026 vacuum excavation public-rate falsifier

**2026-10-29 status: WATCH / research only.** Existing [ledger #863](https://github.com/P00NSMASHER/github-value-hunt-ledger/issues/863) and draft PR #870. No changes to protected main, worker claims or Integrator priority.

## Primary evidence

The [City of Worcester bid CR-8693-J6](https://www.worcesterma.gov/finance/purchasing-bids/bids/cr-8693-j6) opened April 16 and closed May 13, 2026; its listed awardees are Phoenix Communications and R.H. White. Published service window: July 1, 2026 through June 30, 2027. The [four-page source pricing PDF](https://www.worcesterma.gov/sites/default/files/bids/CR-8693-J6%20-%20Bid%20Results%20%28Unit%20Pricing%20Pages%29.pdf) shows four bidders and five rate tiers for each, a **four-hour minimum on any vacuum-excavation call**, and a warning that estimated annual hours are for bid comparison only, not guaranteed orders. PDF pages have been visually inspected. The pages show **no specifically named disposal-charge line**. That is not proof that other charges are prohibited by the executed contract.

## Reusable public dataset and reproduction

`worcester_bid_rates_2026.json` transcribes 20 source price rows with bidder/page attribution and the 4h minimum; `worcester_public_rate_audit.js` validates arithmetic with zero dependencies.

Run with Node: `node -e "const d=require('./worcester_bid_rates_2026.json'); console.log(require('./worcester_public_rate_audit.js').verifyPublicBidRates(d))"`.

**V8 source-code execution performed:** 20/20 quantity×price row checks; 4/4 published total checks; 4/4 purely fictional minimum-hours scenarios. Reported bid totals: Phoenix **$375,300**, R.H. White **$375,496**, New England Vacuum Excavation **$452,100**, Champion Environmental Services **$2,850,492**. **Those are competing bid comparisons, not amounts we can earn or recover.** Manual PDF transcription and arithmetic checks do not independently authenticate an executed contract or invoicing outcomes. No CI acceptance asserted.

## Material adversarial finding

The prior in-sample proof used a fabricated uniform **$175/hour plus $180 per disposal load**. It does not generalize to Worcester's time-tiered public pricing or four-hour minimum. A one-hour *hypothetical* standard weekday qualifying call at Phoenix's listed **$315/hour** would have a four-hour minimum of **$1,260** instead of the naive one-hour **$315**, a *conditional* **$945** difference. Four *different fictional calls* across both listed awardees yield **$3,335 total constructed sensitivity**, not real invoicing errors or collectible money. Even an official bid minimum is not by itself proof an invoice is deficient: actual signed terms, dispatch tier, credits, waivers, call eligibility and invoice ledger completeness are missing.

Existing substitutes: [Aimsio](https://aimsio.com/industries/hydrovac/) markets mixed per-hour/per-load client-specific rates and ticket-to-invoice integration; [Spira](https://www.spiradata.com/hydrovac-software) markets rate-aware ticketing and invoicing. Neither vendor's marketing proves actual customer payments or a measurable advantage for our audit.

**Commercial gate:** General ticketing SaaS NO-GO. Independent contract-rate/ERP reconciliation WATCH only. Actual buyers **0**, verified collectible **$0**, owner receipts **$0**. Asking $100 for a fixed review remains hypothetical. No labor cost or ROI established for a real buyer.

**Next cheapest test:** Seal a 20-case scenario set covering tier ambiguity, four-hour minimum, adjustments, missing contract authority and fully billed controls; measure false monetary candidates against a properly configured baseline. Only with fresh authorization could actual 100-job customer data, incumbent software and true receivables be tested. No outreach, spending, claims, funds, trades, enrollment, production deployment or Work mode.

## Independent source-identity tamper challenge (this iteration)

The first standalone checker **incorrectly accepted 3 deliberately altered authority fields**: a fabricated PDF URL, a wrong billing-tier label, and a substituted bidder name. These defects did not invent actual money, but made the nominally source-bound calculations misattributable. The checker was **patched before completion** to pin the exact municipal source URL, bid ID, PDF path, tier identities and all four bidder names. The permanently committed `test_worcester_public_rate_audit.js` now reproduces **20 line-price checks + 4 bid totals + 4 fictional calls + 10/10 rejected mutations**, including source/tier/name tampering, changed quantity/rate, fabricated revenue and false awardee. All cases were executed against the exact JS/JSON bytes subsequently read back from the draft branch in V8. **Node CLI and GitHub CI were not independently run or passed.** No actual invoices, legal contract, paid customers or real savings were audited.
