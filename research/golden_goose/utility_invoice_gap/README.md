# Municipal utility invoice continuity | Golden Goose candidate 005

**Status: WATCH, research-only, not sold or externally validated. Realized user revenue: $0.**

## Market signal and asymmetric adversary
The City of Buffalo's Comptroller reported an actual $1M+ refund for streetlight billing on nonexistent fixtures in 2017. In contrast, *April 17, 2026* reporting described a ~$105,000 **back-bill liability** for Hudson's 891 LED streetlights after a billing interruption. A naive “every invoice mismatch is a refund” engine would reverse the economic direction of the second case.

Official Buffalo: https://buffalocomptrollerny.gov/169/National-Grid-Refunds-Buffalo-1-Million
Hudson reporting: https://www.timesunion.com/hudsonvalley/news/article/hudson-national-grid-streetlight-billing-fiasco-22210542.php

**Opportunity hypothesis:** A narrow, read-only, municipal *missing-invoice and account-transition control* could flag silent utility billing gaps before a surprise back-bill. Incumbents already offer full streetlight forensic audit (Troy & Banks) and automated bill collection (Huckleberry). This may be an inexpensive *control*, but commercial differentiation and demand are **unproven**.

Competition: https://www.troybanks.com/services/streetlight-audit/ ; https://huckleberryservices.com/platform/utility-bill-management ; https://deaudits.com/pricing/

## Prototype and reproducibility
Run in a local Node 20+ environment (no dependencies, network or credentials):

`node --test research/golden_goose/utility_invoice_gap/invoice_gap.test.mjs`

The module takes a declared monthly service interval and posted/draft/void bill records. It waits a **synthetic, configurable 45-day grace period** before returning `MISSING_INVOICE_REVIEW`. Zero posted, void-only, duplicate, malformed or multiple-posted records remain **REVIEW** rather than automatically asserting a credit, double billing, or unpaid debt. It does not parse a real customer invoice, establish legal responsibility or compute true expected charges. Unsupported partial-month service boundaries fail closed.

No money-bearing field is projected: `recoverable_cents` and `potential_liability_cents` are always **null**, while `realized_revenue_cents` is always **0**. The only legitimate economic values in `case_evidence_2026-10-28.json` are historical City of Buffalo refunds and the 2026 reported Hudson back-bill, neither attributable to this project.

## Falsification and commercialization gate
**20 in-process V8 synthetic assertions** passed at research branch creation; independent GitHub CI, buyer-authorized data, customer acquisition, comparative baseline and recurring revenue are all **UNVERIFIED**. If the repository's `node --test` passes, that only replicates unit logic. Next test: on a rights-clean authenticated set of 12–24 account-months, measure accurate missing-bill detection vs existing AP controls; separately validate municipality procurement and actual buyer interest. Reject this candidate if incumbent systems already provide reliable account-complete alerts at lower total cost. Do not contact any organization or upload external data without express approval.

Do not promote to portfolio MASTER or modify existing hunting claims. Research references: Golden Goose issue #863 and existing utility audit candidate in `OPPORTUNITIES.md`.
