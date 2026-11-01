# RETALLY: EIA public diesel reference (2026-10-06)

**Scope: internal historical market reference only.** This is a frozen, manually transcribed subset of official U.S. Energy Information Administration (EIA) observations. It is **not** a live feed, customer rate schedule, recoverable overcharge, or fee-authorizing record.

## Publisher, publication, rights and integrity

- Original publisher: U.S. Energy Information Administration, *Gasoline and Diesel Fuel Update*, diesel fuel release dated **October 6, 2026**.
- Official reference: https://www.eia.gov/petroleum/gasdiesel/index.php
- Independent official historical series: https://www.eia.gov/dnav/pet/PET_PRI_GND_A_EPD2D_PTE_DPGAL_W.htm
- Public-sector data reuse: https://www.eia.gov/about/copyrights_reuse.php . EIA requests source acknowledgment with publication date. No EIA logo, brand endorsement, or third-party image is copied.
- Units: U.S. dollars per gallon, including taxes; EIA U.S. on-highway diesel retail survey.
- Survey weeks: September 21, September 28, October 5, 2026 (Mondays).
- Regions: United States, East Coast (PADD 1), Central Atlantic (PADD 1B).
- Source files: `freight/data/eia_on_highway_diesel_2026-10-06.csv`, `freight/retally_eia_reference.py`, and `freight/test_retally_eia_reference.py`.
- Pinned CSV SHA-256: `20c3e8cec1c7e13aa9e7d61bdfd95e3d1ee75913e932887efbcd2be946ce97b6`. This proves internal file identity, **not** that EIA digitally signed the file.

## Validation

```bash
PYTHONPATH=. python -m pytest -q freight/test_retally_eia_reference.py
```

The reader enforces exactly nine complete observations with three decimal places, valid Monday dates, precise source scope and digest identity. It rejects changed observations, duplicate/missing rows, unexpected regions/weeks, malformed CSV and unapproved lookup requests. All arithmetic uses `decimal.Decimal`; no floats are used to represent the prices.

Example (informational only):

```python
from freight.retally_eia_reference import reference_price

observed = reference_price("2026-10-05", "CENTRAL_ATLANTIC")
assert str(observed.price) == "6.485"
assert observed.role == "OBSERVED_PUBLIC_MARKET_REFERENCE_ONLY"
```

## Strict release boundary

EIA explicitly says it does **not** calculate, assess or regulate carrier fuel surcharges: https://www.eia.gov/tools/faqs/faq.php?id=2&t=5 . Each carrier and shipper establishes its own formula. Before a future authorized invoice audit, a human must establish the actual buyer-carrier agreement, effective surcharge tariff and index geography, pickup/billing week, any publication lag, rounding convention, rate authority, and buyer invoice evidence. Separate buyer approval, claim eligibility and independently verified customer settlement are required.

**This module has no carrier-specific contract fields, buyer records, claim-generation function, settlement interface or fee computation.** It cannot be used as proof that any customer was overcharged or that RETALLY earned revenue. It is not connected to hosted RecoveryOS payment paths or public website uploads.

## GitHub data reuse distinction

GitHub may host official publisher mirrors, third-party directories, research-derived benchmarks or synthetic demo files. A repo file or a code MIT license cannot establish dataset rights or operational authenticity. For example, `asu-trans-ai-lab/RAS2026-PSC` explicitly limits its rail traffic to research-derived competition demand, and `api-evangelist/bureau-of-transportation-statistics` hosts a third-party API listing, not BTS original data. Neither is imported into RETALLY. Primary government source is preferred.

**Release:** review-only source changes in PR #329; do not merge/deploy solely on these tests. PR #329 still requires independent reconciliation with newer main-branch website/inquiry changes and all other already documented legal, contact, confidential-data, and production financial gates.
