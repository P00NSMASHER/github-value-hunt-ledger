# PROJECT GOLDEN GOOSE #031: private freight first-$100 fee vs 20–35% incumbents

**As of October 29, 2026 EDT | UNCLAIMED research addendum to draft PR #878 and existing issue #863.** The preceding #030 falsified the federal-direct buyer path. This addendum examines the *existing higher-priority private buyer path*, without changing Hunt 15's integrator order, main, customer systems, or worker leases. No outreach, bids, data access, spending, claims, or Work credits.

## Market evidence and contradiction

| Source and observation | What it supports | What it does **not** prove |
| --- | --- | --- |
| [FMC chairman's June 3, 2026 congressional testimony](https://www.fmc.gov/ftdo/testimony-of-chairman-dibella-before-congress-future-of-united-states-maritime-review-of-fiscal-year-2027-maritime-administration-and-federal-maritime-commission-budget-requests/) | 195 FY2026 charge complaints *through the testimony date*, 372 informal disputes facilitated/resolved in FY2025. Agency also mentions ~$11.4 million in FY2025 mediation settlements. | Not vendor willingness-to-pay, RETALLY fees, or any RETALLY-collectible portion of mediations/settlements/penalties. Do **not** project these counts to full-year 2026. |
| [FMC's Oct. 1, 2024 consumer-assistance guide](https://www.fmc.gov/articles/fmc-services-available-during-supply-chain-challenges/) | The agency offers free informal mediation and charge-complaint routes for eligible shipping disputes. | Not a commercial referral, and generic filing assistance is not a unique monetizable product. |
| [FMC Nov. 20, 2025 court update](https://www.fmc.gov/articles/u-s-court-of-appeals-issues-decision-in-case-on-demurrage-and-detention-billing-practices/) | §541.4 proper-billed-party rule was set aside Sept. 23, 2025; other Part 541 rules remain. | Stale 2024 recipient rule does not support new paid entitlement. Repository's existing `production/fmc_tariff_ledger/audit_dd_invoice.py` already excludes §541.4, so **reject duplicative build**. |
| [FreightForensic pricing](https://www.freightforensic.com/pricing.html) | Self-advertised 20%–30% contingency, no upfront audit. | Independent fee receipt, adoption or our share. |
| [RecoverAudit pricing](https://recover-audit.com/pricing) | Self-advertised 20% contingency and first 10 invoices free. | Independently achieved recoveries or a comparable service level. |
| [FreightAudit Pilot pricing](https://www.demurrageaudit.com/pricing) | Self-advertised 35% no-upfront **ocean D&D** recovery. | A like-for-like all-mode freight quote or confirmed buyer demand. |
| [RETALLY business model](https://github.com/P00NSMASHER/github-value-hunt-ledger/blob/main/freight/BUSINESS_MODEL.md) | Working default 30% of uniquely attributable actually recovered money; not an upfront charge. | An executed customer agreement or actual revenue. |

**Commercial falsifier:** A 30% contingency/free-audit price alone is **not differentiation**: public operators already advertise 20%–35% and no upfront. This is vendor-price evidence, not observed actual sales or quality. Public FMC assistance is a free alternative for some disputes. Focus private freight on an **evidenced incremental error found beyond the existing audit + actual subsequent credited/recovered dollars**. No further generic audit-polish build is justified before buyer records.

## Reproducible fictional economics, not receipts

Assume exactly **2 analyst hours at $45/hour + $10 direct costs = $100** per audit; excludes acquisition, taxes, legal, data security, disputes and follow-through. Fees are calculated only against hypothetical **attributable, net-of-reversal** customer recovery, never the identified error, the claim filed, a government settlement, or carrier payments to another business.

| Hypothetical rate | Minimum customer fee-eligible recovery to model $100 gross fee | $1,000 gross fee | $100 contribution after $100 cost | $1,000 contribution after $100 cost |
| --- | ---: | ---: | ---: | ---: |
| 20% advertised comparator | $500.00 | $5,000.00 | $1,000.00 | $5,500.00 |
| 30% RETALLY working rate | **$333.34** | **$3,333.34** | **$666.67** | **$3,666.67** |
| 35% ocean-only advertised comparator | $285.72 | $2,857.15 | $571.43 | $3,142.86 |

At 30%, a totally fictitious $1,000 flagged error with **no actual customer recovery** produces $0 hypothetical fee and **-$100 contribution**. If the customer received $666.67 of newly attributable recovery, the *fictional* $200 fee minus $100 cost would contribute $100, **but no such customer, case, contract, or fee was observed**. An incumbent-known or later-reversed $666.67 credit can imply **$0 fee**, not $200.

## Tangible artifact and rejection gates

- [Strict Decimal model](private_freight_cash_gate_031.py): rejects invalid/negative/NaN/subcent amount, attribution greater than net-of-reversal customer credit, or credits exceeding hypothetically identified error. It never labels a modeled or boolean-asserted receipt as actual owner cash.
- [26 adversarial local tests](test_private_freight_cash_gate_031.py): **26/26 passed in a local Python 3 execution**; required CI wrapper in `tests/` checks the same locally validated suite through the normal repository governance. Hosted CI must independently pass at the exact head before a final release claim.
- Separate offline [13-case market/model sensitivity dataset](https://github.com/P00NSMASHER/github-value-hunt-ledger/issues/863) is described in the ledger, not claimed as real invoices. The Markdown source table is the reusable market evidence dataset.

**Status:** PRIVATE FREIGHT PRIORITY UNCHANGED / FIRST-$100 COMMERCIAL PROOF **NOT VALIDATED**; generic free-audit + 30% pricing **NO LONGER A DISTINCTIVE WEDGE**. Verified customer/owner receipts $0; verified collectible fees $0; qualified paying customers 0; permissioned real comparisons 0. FMC's ~$11.4m historical mediations, government penalties, fees competitors advertise, and *modeled customer receipts* are **not owner collectible revenue**.

**Next cheapest falsifier:** Subject to *fresh explicit user permission*, independently inspect a qualified private shipper's **frozen 10–20 invoice/contract/shipment/settlement packets**, with incumbent decisions sequestered, actual labor observed, and client-authorized attribution/real credit proof. Before permission: only read-only landing/offer evidence, no customer outreach or external action. If no incremental recoveries or review labor dominates fee, stop. Do not change integrator priorities without that proof.
