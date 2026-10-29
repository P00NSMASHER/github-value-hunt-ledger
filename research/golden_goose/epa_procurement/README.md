# Golden Goose: enforcement mandate → municipal bid prepublication probe

**2026-10-29 | Evidence state: CURATED_SOURCE_CHECK / NOT COMMERCIALLY VALIDATED | Verified revenue: $0.**

## Question
Can an EPA wastewater enforcement requirement point to a named municipal procurement well before the issuer publicly posts an RFP? Does connecting an **exact required deliverable** to a future solicitation add value beyond generic compliance data or a bid-alert list?

## Reviewed source-to-bid examples
1. **Guam / strong retrospective scope correspondence:** EPA publicly announced the Guam Waterworks settlement **Jan. 30, 2024** and specified a **Hagåtña secondary-treatment feasibility study/plan**. Guam Waterworks' official bids index lists **RFP-02-ENG-2025: Hagatna Wastewater Treatment Plant Secondary Treatment Feasibility Study**, issued **Nov. 25, 2025**. Difference: **665 days**. That RFP is closed; no purchase or award is implied. Sources: [EPA settlement description](https://www.epa.gov/enforcement/guam-waterworks-authority-clean-water-act-settlement-information-sheet), [GWA official procurement index](https://guamwaterworks.org/bids/).
2. **Navajo / second correspondence, weaker posting-date provenance:** EPA announced a proposed partial decree concerning new wastewater treatment plants for Chinle, Kayenta, and Tuba City on **Jan. 10, 2024**. NTUA's official RFP listing names **Tuba City Wastewater Treatment Plant Improvements Project**, bids due **Nov. 24, 2026**. An *independent third-party bid listing*, not an issuer-issued date stamp, states publication **Oct. 15, 2026**: 1,009 days after the EPA announcement. Classify **REVIEW_DATE_PROVENANCE**, not official-date-verified. Sources: [EPA announcement](https://www.epa.gov/newsreleases/navajo-tribal-utility-authority-agrees-100-million-wastewater-treatment-improvements-0), [NTUA issuer bids](https://www.ntua.com/rfp.html), [secondary publication metadata](https://www.noticeregistry.com/arizona/notice/bid-notice-fort-defiance-295904).

**Important distinction:** A visible earlier public regulatory clue is not proof of a unique lead, a causal relationship, availability for all contractors, or first-to-market advantage. EPA's **$400 million Guam** and **$100 million Navajo** figures are **multi-project compliance program estimates**, not this product's revenue, not necessarily tender values, and not available earnings.

## Adversarial checks
Data: [2026-10-29_sample.json](2026-10-29_sample.json); deterministic fail-closed prototype: [verify_sample.py](verify_sample.py); synthetic controls: [test_verify_sample.py](test_verify_sample.py).

- Curated cross product: **2 regulatory notices × 5 bid listings = 10 pairs**. Expected: **1 exact official-date source correspondence; 3 REVIEW; 6 NO_MATCH**.
- Same agency and facility but **wrong technical scope** (clarifier parts, plant rehabilitation) cannot promote automatically. Cross-utility and cross-facility matches rejected.
- Bid before EPA notice rejected, missing/malformed dates reviewed, spoofed EPA/issuer hostnames reviewed.
- A third-party publication date is *review only*, even when the current bid appears on the official issuer website.
- Local parallel Python fixture run (different full-size prototype) passed **18/18**, but **this PR's committed Python tests have not yet run in CI** and are not claimed independently verified.

## Market test and stop gates
Public products already sell the broad theme: [Klarifi](https://klarifi.io/) analyzes water permits/capital budgets; [Municipal Compliance Pipeline](https://municipalcompliancepipeline.com/) advertises wastewater enforcement lead intelligence for **$69–$99/month per state** (asking price only); [CivicSonar](https://civicsonar.ai/) markets municipal pre-RFP signals. **Generic compliance-to-sales-leads is not an uncontested niche; NO-GO on launching another generic dashboard.**

Provisional rubric A–F = **2+3+3+2+3+5 = 18/30**, well below the integrator's 24+/30 normal promotion threshold. No prospective predictive validation, willingness-to-pay evidence, enrolled customers or independently observed payments.

**Next cheapest falsifier:** Freeze 20 *consecutive*, not outcome-selected, new municipal enforcement notices before reading their future bids. Curate exact required scope and issuer identity; compare only later, time-stamped, first-party issuer RFPs over 12–24 months; log false positives/negatives and benchmark a free bid-alert baseline. Stop if no source-verified advantage over incumbents. A possible later $100 source-linked briefing is a pricing *hypothesis*, not income. Do not market, contact, bid, pay, enroll, submit, scrape gated material or publish a paid offer without approval and legal/terms review.

**Execution provenance:** one manually initiated, unclaimed Golden Goose research experiment. Not a scheduled hunter claim, not production deployment, not an independent benchmark, and not a main-branch promotion. Preserve existing integrator/worker guardrails.