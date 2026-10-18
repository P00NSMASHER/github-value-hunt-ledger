# RETALLY Lab 14 — First-party public freight evidence (FAF6 + EIA)
**Research-only source tranche • 17 October 2026 • No customer or carrier access**

## What has been independently observed
The source landing pages and full **FAF6.0 State** ZIP were accessed directly
from the U.S. Department of Transportation / Bureau of Transportation Statistics
(BTS) official publication endpoint, and the EIA diesel table from the U.S.
Energy Information Administration. BTS FAF6 was released in 2026 using 2022 as
its benchmark year. All values in this snapshot are historical observations or
model estimates, not live quotes or real freight invoice charges.

**BTS official source:** https://www.bts.gov/faf

**FAF6.0 State original ZIP:** https://faf.ornl.gov/faf6/data/Download_Files/ZIP/FAF6.0_State.zip

**FAF6 DOI:** https://doi.org/10.21949/fhgm-g335

**FAF6 field definitions:** https://faf.ornl.gov/faf6/data/FAF6_Metadata.xlsx

**BTS FAQ on limitations:** https://www.bts.gov/faf/faqs

**Census state FIPS codes:** https://www.census.gov/library/reference/code-lists/ansi/ansi-codes-for-states.html

**EIA weekly retail on-highway diesel table:**
https://www.eia.gov/dnav/pet/PET_PRI_GND_A_EPD2D_PTE_DPGAL_W.htm

## First original download and integrity
- ZIP SHA-256: `50c6a8bb857b94998a634306234b805af6a114f7ce76ef0b02f34660d01a3e0d`
- Original ZIP bytes: **6,823,123**.
- Internal `FAF6.0_State.csv` SHA-256:
  `e6ff7d1a48a3bc0181435230df508da9b5587a5a009f341e925a31d4a6055d55`
- Internal CSV bytes: **22,948,261**, **599,529 data rows**, 11 named
  original source columns. Source ZIP also includes `FAF6_Metadata.xlsx`.
- Frozen bounded extract: **78 original CSV data records** for state FIPS
  24 (Maryland) and 42 (Pennsylvania), `dms_mode=1` (truck),
  `trade_type=1` (domestic only); **39 distinct SCTG commodities per
  direction**. The extract carries seven unmodified original column names.
- All numeric quantities are stored as exact six-place decimal strings.
  Aggregation uses decimal arithmetic, not float rounding or interpolation.

### Descriptive observed MD ↔ PA truck-mode commodity flows

| Direction | Original commodity records | 2022 thousand short tons | 2022 million constant dollars of **goods value** |
|---|---:|---:|---:|
| Maryland → Pennsylvania | 39 | 9,294.353721 | 17,053.202765 |
| Pennsylvania → Maryland | 39 | 22,583.687532 | 22,012.297371 |

**Interpretation:** These are **state-to-state modeled commodity flows**.
The numbers are neither observed individual trucks nor invoiced freight
charges, nor a tariff, historical shipment-level variance, lane quotation,
specific carrier market share, recoverable loss, 2026 shipment total,
measured cost of trucking, or verified demand from a prospect.

### EIA historical fuel-price snapshot

The official EIA weekly table, in U.S. dollars per gallon **including
taxes**, shows for the week of **12 October 2026**:
- U.S. on-highway diesel: **$6.179/gal**.
- East Coast (PADD1): **$5.908/gal**.
- Central Atlantic (PADD1B): **$6.471/gal**.

The committed source excerpt retains six published weekly dates,
7 September through 12 October 2026, for each of those three official
regions (18 observation rows). This is an EIA retail price **context
benchmark**; a real carrier fuel surcharge is governed by the applicable
dated carrier/customer contract or tariff. It cannot be inferred merely
from the EIA retail pump average.

## Reproduction and original-source acceptance
The two small frozen source excerpts are **direct originals**, not AI
fabrications. Their restricted column sets and exact row and aggregate
values are checked by:

```bash
PYTHONPATH=. python -m unittest freight.test_public_faf6_eia_v1
PYTHONPATH=. python -m freight.public_faf6_eia_v1
```

For independently replaying the full original BTS ZIP, download it from
the **official** URL above, then run a bounded, **offline** check:

```bash
PYTHONPATH=. python -m freight.public_faf6_eia_v1 \
  --official-zip /path/to/FAF6.0_State.zip
```

The validator checks original ZIP byte length and SHA-256, internal CSV
byte length, CRC and SHA-256, exact original schema and **599,529 source
rows**, then re-extracts and compares all **78 exact original records**.
A revised government archive is **not** silently substituted under the
2022 pinned receipt. Publication revisions must be manually versioned
and re-reviewed, with new source hashes.

The fixture tests intentionally corrupt the mode, commodity identity,
row values, weekly EIA observation, date, and CSV schema and verify that
false evidence fails closed. They also prohibit injection of invoice columns,
misattributed customer charges, automatic recoveries, or research-as-contract
claims. No network, API key, payment, prospect outreach or scheduled task
is required to run the tests.

## What this does not close
1. **No real customer-invoice truth.** Need an actual prospect-approved
   invoice sample, original carrier agreement/tariff effective on that date,
   shipments/payments and independently verified reviewer evidence.
2. **No verified recovery performance.** Do not publish savings,
   breach, fuel-overcharge, recovery rate, false-positive rate or accuracy
   marketing claims based on public flow estimates.
3. **No live data freshness claim.** FAF6 represents 2022 modeled flows,
   EIA observations stop at 12 October 2026 in this frozen tranche.
4. **No historical finding closure.** RETALLY's **26 original historical
   defects remain OPEN_UNVERIFIED**. All **18 independent human first-customer
   approval gates remain unmet**.
5. **No production change.** This draft is stacked on unmerged Lab 14
   research integration PR #476. Do not deploy into public customer intake
   or hosted RecoveryOS, contact carriers or prospective customers, incur
   vendor fees, change automations, or treat government data as permission
   to collect confidential freight records.

## Next lawful data source progression
- Reconcile BTS FAF6 original geography, units, mode and SCTG codebooks
  before broader multi-state coverage.
- Add date-specific EIA and carrier-published fuel-surcharge **authority**
  as separate source families; contractual applicability must remain
  UNVERIFIED without the customer's actual carrier agreement.
- Independently sample original public procurement or regulatory records
  with explicit re-use rights and event times; label any reported payment
  amounts as government/public procurement evidence, not RETALLY recoveries.
- Actual invoice-level second-look validation must wait for named,
  authorized owner-reviewed customer records and separate hosted
  data-protection controls.

**Release state: RESEARCH_PUBLIC_SOURCE_SNAPSHOT_VERIFIED.**
Commercial claims, financial operations and recovery case outputs: **NO-GO**.
