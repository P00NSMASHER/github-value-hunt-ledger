# RETALLY Research Lab 14 — Mission 26: BLS trucking industry price adjustment

**DRAFT / INTERNAL RESEARCH. October 12, 2026.** Stacked on [Mission 25 PR #402](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/402). Research Lab 14 remains one of the original fourteen labs; all eighteen independent real-customer data-owner approvals remain unmet. No production merge, deployment, outside contact, private data ingestion, marketing or scheduled task change is authorized.

## Question

Mission 25 established 2017–2024 **nominal U.S. trucking employer-establishment revenues** from original Census SAS/AIES sources. Nominal revenue includes the effect of selling prices. What happens if these amounts are adjusted by their own BLS industry **producer output price indices**, with explicit limits on what this estimates?

The [BLS PPI program](https://www.bls.gov/ppi/overview.htm) measures prices received by domestic producers; [BLS price-index concepts](https://www.bls.gov/opub/hom/ppi/concepts.htm) explain that industry PPIs measure net output prices. These **do not directly observe buyer freight invoices or client-specific contract-rate mistakes**.

The official [BLS API](https://www.bls.gov/developers/api_signature.htm) permits read-only retrieval of up to ten years of monthly source observations using a bounded POST request. The source series used here are:

- [PCU484121484121](https://fred.stlouisfed.org/series/PCU484121484121): BLS original 2017–2024 **NAICS 484121** long-distance general-freight truckload producer index, not seasonally adjusted, December 2003 = 100.
- [PCU484122484122](https://fred.stlouisfed.org/series/PCU484122484122): BLS original 2017–2024 **NAICS 484122** long-distance general-freight less-than-truckload producer index, not seasonally adjusted, December 2003 = 100.

The first successful read-only publisher API probe returned **96 monthly observations per series, 192 in total, exactly twelve months in each reference year**. No observation in these eight years carried a provisional/preliminary flag. The original request also asked for parent **PCU484484** and BLS v1 explicitly returned **Series does not exist** for that identifier. FRED may display an indexed aggregate, but Mission 26 does not substitute a FRED webpage or a child index as an authenticated original API source. **Parent NAICS 484 price-adjusted growth is deliberately unavailable**.

## Analytical method — price-adjusted revenue proxy, not official real output

For each accepted industry and year:

1. Use the published monthly BLS industry PPI levels for **M01–M12 only**. Require exactly twelve distinct, final monthly observations. Calculate their equally-weighted **arithmetic mean**, preserving original decimal source precision.
2. Use the matching Census employer-industry nominal revenue for 2017–2024 that was authenticated in Mission 25. 2017–2021 come from the revised SAS; 2022–2024 come from the linked AIES historical release.
3. Create an **illustrative revenue at 2017 industry PPI level**: published nominal Census revenue for year Y multiplied by (industry annual-mean PPI 2017 / industry annual-mean PPI Y).
4. Compare the resulting 2017–2024 price-adjusted *proxy* with the nominal revenue change and producer-price-index change.

Illustrative 2017–2024 estimated output-price adjustment:

| Industry | Census nominal 2017–2024 revenue change | BLS producer output PPI trend | Illustrative PPI-adjusted revenue proxy change |
| --- | ---: | ---: | ---: |
| Long-distance truckload 484121 | **+43.48%** | Derived from original BLS monthly series | **+2.82%** |
| Long-distance LTL 484122 | **+40.93%** | Derived from original BLS monthly series | **−1.89%** |
| All trucking parent 484 | +38.65% nominal revenue (Census) | **Original BLS v1 aggregate series not verified** | **NOT CALCULATED** |

These adjusted percentages are **NOT official Census/BLS real output, shipped freight tonnage, number of jobs or actual freight demand**. They are approximations requiring caution because Census and PPI populations/industry service mix can differ, time-varying composition and quality changes are not fully represented, monthly averaging is not revenue weighted, and PPI observations can be revised. No causal, statistical-significance or net margin conclusion is claimed.

The source family and purpose are deliberately separate from the entirely unresolved questions of customer-paid LTL invoice values, governing tariff/contract terms, auditable overcharge prevalence, adjudicated refunds or realistic addressable freight recovery value. Nothing in the Census/PPI economic data independently satisfies any of the eighteen genuine customer pilot controls.

## Source and engineering evidence

- Frozen public monthly source snapshot: freight/research/BLS_PPI_TRUCKING_2017_2024_20261012.json. Contains **two BLS series × eight years × 12 months**, original exact published decimal values, series IDs, source API payload, date/measurement/source limitations and explicit parent 484 hold.
- Engine: freight/research_bls_ppi_bridge.py. Only uses original API **https://api.bls.gov/publicAPI/v1/timeseries/data/** with two allowlisted published industry series. Strict monthly year/count/ID/format/final-footnote and observed-value guards, no BLS API key or paid account, SHA-pinned original evidence catalog, and Decimal arithmetic with source-preserving annual means. Inaccessible API becomes **BLOCKED**, but changed publisher values **FAIL**; the latter cannot be converted into an ordinary network hold. Writes read-only bls_ppi_adjustment.json and bls_ppi_adjustment.html.
- Adversarial tests: freight/test_research_bls_ppi_bridge.py. Reject missing/extra/repeated months, original data revisions, unauthorized parent aggregate substitution, out-of-range years, changed series IDs, preliminary/flagged values, illegal source provenance, spoofed invoice market/revenue claims, and unsafe HTML.
- Original Lab 14 director/Control Center: a price-adjustment research panel with explicit original source status, upper-level source audit and non-commercial negative probes. Existing lab count and human pilot controls are preserved.
- GitHub Actions: .github/workflows/retally-bls-ppi-price-bridge.yml is **PR or explicit manual dispatch only**. It runs offline adversarial/regression tests and original Lab 14, then a bounded independent two-series BLS source POST and evidence receipt validation. Saves only internal JSON/HTML reports, never BLS raw responses/customer files. No schedule, deployment or payment.

Reproduce from repository root, Python 3.11+:

    PYTHONPATH=. python -m pytest -q freight/test_research_bls_ppi_bridge.py
    PYTHONPATH=. python -m freight.research_bls_ppi_bridge --offline --as-of-date 2026-10-12 --out /tmp/retally-ppi-offline
    PYTHONPATH=. python -m freight.research_bls_ppi_bridge --fetch-original --as-of-date 2026-10-12 --out /tmp/retally-ppi-original
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-control

**DO NOT MERGE OR DEPLOY, CONTACT BUYERS/CARRIERS, ADD MONITORING TASKS, STORE CUSTOMER INVOICES, MAKE REFUNDS OR PUBLISH RETALLY RECOVERY-OPPORTUNITY CLAIMS.**
