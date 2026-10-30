# Golden Goose #032: procurement deadline provenance (2026-10-30)

**Decision:** CaptureBrief-adjacent evidence-integrity WATCH, *not* a new commercial priority. Standalone bid-alert/check product NO-GO for the first $100 absent buyer evidence. Unclaimed research only, existing issue #863, no worker lease, no integrator promotion, no new platform, no protected-main edits, no outreach, no customer records.

## Primary and secondary evidence

1. [Sound Transit, official procurement policy](https://www.soundtransit.org/get-to-know-us/doing-business-with-us/procurement-contracts-agreements): agency names its Biddingo procurement portal as authoritative location of current postings and addenda; registered vendors may receive automatic solicitation/amendment notices. No portal registration was performed.
2. [RP 0157-26 public third-party mirror](https://www.lightrfp.com/marketplace/bid/SOUND_TRANSIT-41787728/orca-on-call-transit-fare-collection-and-payment-industry-consulting-services): the **headline reads Nov. 4, 2026, 3 p.m. Pacific**, while **embedded older solicitation text/structured snapshot reads Oct. 21, 2026, 3 p.m. Pacific**; another embedded snapshot reads Nov. 4. **14 calendar days** separate these date claims. This may be ordinary supersession/version drift, *not* a proven incumbent mistake or authoritative tender closing date. All three fields are from **one syndicated source**.
3. [Official Sound Transit Biddingo tender link](https://www.biddingo.com/soundtransit/bid/1/41195253/41787728) was followed, but live deadline content and amendment PDFs did not render in available read-only public access. Current official date, actual deadline amendment history, tender availability and bidder rights are therefore **UNKNOWN**. Do not bid using either unconfirmed date.
4. Commercial substitutes: [DemandStar first-party supplier pricing](https://network.demandstar.com/pricing-suppliers/) markets one-agency notifications free, wider subscriptions from $60/year per county, and $5 out-of-coverage document packages. [Govly first-party pricing](https://www.govly.com/pricing) markets recent solicitation search free and higher-tier offerings. These are vendor claims and do *not* validate our future buyers, pricing or competitor accuracy.

## Tangible reproducible test

The source-linked JSON fixture manually transcribes the **single real mirror** and its unavailable official endpoint. No scraping, paid software, registration or private data. The Python negative-control comparator never labels a tender open/closed or selects a bidding deadline: a mismatch yields **CONFLICT_REVIEW**, agreement yields **UNCONFIRMED_SINGLE_DATE**, an unrendered official link yields **SOURCE_INSUFFICIENT**. Both outcomes require authoritative human review.

To reproduce offline: `python -m unittest discover -s research/golden_goose/deadline_conflict_032 -p 'test_deadline_conflict_gate.py' -v`. The 13 tests challenge date validity, same-day minute changes, fake official claims, missing provenance, timezone, duplicates and fabricated monetization. A Technology Intelligence CI wrapper invokes these tests on each PR. This research benchmark does not amend the CaptureBrief production engine.

## Adversarial unit economics (illustrative ONLY)

Imagined **$49** per manual check; **20 min × $45/hour + $5 overhead = $20 cost; $29 contribution** before taxes/acquisition/liability. Four hypothetical sales -> $116 contribution; 35 -> $1,015. If effort reaches **60 minutes**, cost $50 -> **-$1 contribution per sale**. No real review labor observed; no paying customer; **$0 owner cash, $0 verified collectible revenue**. Contract values, potential avoided bid failures, seller pricing, settlement funds and market sizes are *not* owner receivables.

**Falsifier/next experiment:** obtain lawfully accessible original agency RFP plus all amendment versions and verify the actual latest due date by an independently reviewed source. Sample >=10 other agency tenders with frozen official amendments; quantify true stale-date detection precision, analyst time and differentiated value relative to free official notifications/competitors. Only with express permission evaluate buyer willingness to pay. Otherwise stop this niche and maintain the integrator's Freight F1 -> AP fallback priorities.

No customer outreach, bidder enrollment, bid filing, subscriptions, money transfer, production change, worker claim, new issue or PR merge. Draft review only.
