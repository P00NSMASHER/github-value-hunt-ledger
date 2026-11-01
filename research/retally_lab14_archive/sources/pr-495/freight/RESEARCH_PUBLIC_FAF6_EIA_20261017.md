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


## Second original-source layer: publicly posted carrier fuel schedules

Eleven exact public numerical observations were added after independently
viewing **carrier-owned** pages, preserving original effective dates,
service scope and the original source URL on every row.

| Carrier-owned original | Bounded records | Confirmed effective date / posted percentage |
|---|---:|---|
| FedEx Freight U.S. LTL | 6 | Oct 14–20, 2026: **57.50%**; based on EIA national Oct 12 **$6.179/gal** |
| UPS U.S. Domestic Ground | 4 | Sep 28, 2026: **30.25%** (last rate in this frozen excerpt, NOT a claim it applied on Oct 17) |
| Union Pacific U.S. Domestic Intermodal | 1 | Oct 12–18, 2026: **58.0%** (official Oct 6 announcement PR2026-66) |

Primary sources:
- FedEx Freight:
  https://www.fedexfreight.com/en-us/support-resources/tariffs-rates-information/fuel-surcharges
- FedEx previous weeks:
  https://www.fedexfreight.com/fragments/fuel-surcharge-table
- UPS Fuel Surcharges:
  https://www.ups.com/us/en/support/shipping-support/shipping-costs-rates/fuel-surcharges
- Union Pacific direct announcement:
  https://www.up.com/announcements/intermodal/2026/PR2026-66

**FedEx EIA cross-publisher validation:** Six dated FedEx Freight LTL weekly
rates (Sep 9, 16, 23, 30 and Oct 7, 14) include the national U.S. EIA
diesel index observed on the **preceding Monday**. All six originally
published index values match the independently frozen six EIA national
weekly observations by exact `Decimal` equality. For UPS and Union
Pacific we retain the official percent only and do **not** infer an EIA
index date that was not established by the specific published excerpt.

Code: `freight/public_carrier_schedules_v1.py` and its independent
adversarial tests `freight/test_public_carrier_schedules_v1.py`.
The result is **dated PUBLIC_CARRIER_REFERENCE_ONLY**. It is not a
customer-specific surcharge schedule or recovery entitlement:
- FedEx expressly states the **customer agreement is the final authority**
  and Item 570 determines the applicable linehaul and fuel-consuming
  service charge basis. UPS states the specific posted schedule effective
  on the shipment date applies and describes relevant service exclusions.
- A public fuel surcharge is a published percentage, not the surcharge
  actually billed, the customer's tariff exception, base rate,
  contractual discounts, qualifying accessorial charges or payment truth.
- Vendor schedule pages can change, and this excerpt is intentionally
  bounded; do not infer a missing week or use a prior observation as a
  current customer quote.
- No rights to republish entire proprietary guides or access private
  carrier portals are asserted; we preserve a few factual numbers and
  source URLs for internal research.

### Target design for a real second-look audit

GSA's original transportation invoice audit guidance recommends checking
the **actual invoice**, the **bill of lading**, applicable **rates/charges**,
and whether contracted services were performed:
https://www.gsa.gov/policy-regulations/policy/transportation-management-policy/transportation-invoice-audit

This is a useful *evaluation standard*, not evidence a real customer
overpayment exists. RETALLY still has no independently authorized
customer invoice, customer-specific agreement/rate authority, payment
or credit memo, carrier-approved adjustment, or actual recovered funds.

The public excerpt now comprises **78 original modeled FAF6 rows + 18
EIA retail observations + 11 dated public carrier facts** across three
independent publisher families (BTS, EIA and carriers). None is a
customer invoice or a claim that RETALLY found another auditor's missed
overcharge.


## New actual shipment-record source: Census 2022 CFS PUMS (bounded original prefix)

Direct federal ZIP:
https://www2.census.gov/programs-surveys/cfs/datasets/2022/cfs_2022_pums.zip

Data/guide:
https://www.census.gov/data/datasets/2022/econ/cfs/historical-datasets.html

The original federal endpoint returned **206 Partial Content** for requested
byte ranges. Its ZIP central directory identifies a single source member,
`cfs_2022_pums.csv`, **2,824,487,751 uncompressed bytes**,
677,530,492 compressed member bytes, and original ZIP total **677,530,696
bytes** (CRC32 0x3a9fd854). The file starts with 18 native fields including
`SHIPMT_ID`, shipment origin/destination, sector, SCTG, mode, goods value,
weight, distance, temperature/export/hazmat categories and `WGT_FACTOR`.

The first 131,072 original ZIP bytes were accessed directly by byte range;
their SHA-256 is
`d9f78acc810c1290712f87dc082debef801e8d0ef360cfb0521ea289b84b309f`.
From that compressed prefix, the **first 100 complete original data records**
were extracted with original column spellings and exact values, without
inventing or extrapolating observations. The bounded deterministic file-prefix fixture is
`freight/fixtures/public_census_cfs2022_pums_first100.csv`. Its provenance
and precise archive metadata are in the adjacent JSON manifest.

These records are **real Census public-use anonymized shipment microdata,
not actual invoices**. The Census guide explicitly says it assigned
SHIPMT_ID after **randomly sorting the complete PUMS records**.
Nevertheless, RETALLY's first-100-prefix extract is not a separately designed,
weighted, representative population estimator, and its
`WGT_FACTOR` values must not be casually extrapolated to produce national
totals. The full 677MB archive has NOT yet been downloaded or SHA-256
verified, so no full-file integrity, national flow estimates, or other
sampling claims are made.

Run the offline source-prefix integrity check:
`PYTHONPATH=. python -m unittest freight.test_public_cfs2022_prefix_v1`.
It rejects changed schema, record count, row sequence, and unsupported
negative shipping values or sampling weights. **No confidential customer
files, contracts, payment evidence, recovery claims or public marketing
numbers** were added.


## Next original-source candidate: STB public-use railroad waybills

Official Surface Transportation Board:
https://www.stb.gov/reports-data/waybill/

The STB publicly describes a **Public Use Waybill File** generated from a
confidential railroad Waybill Sample File. Its original documentation warns
that the freight revenue field **may be masked** and may not equal the actual
waybill revenue. This is promising for rail shipment research, but the sample
must be version-frozen, source-field meanings established and reported
revenues kept separate from any real invoice or recovery claim.

**Status: SOURCE DISCOVERED, NOT INGESTED OR VERIFIED.** No waybill
microdata has been downloaded, no tariffs or shipper agreements verified and
no freight revenues or rates inferred. Next source step is a bounded original
STB publication/file plus schema/field-level integrity test, preserving masking
rules and avoiding exposure of any restricted confidential sample.


### STB download triage (additional source-check warning)

A HEAD request to the publisher's linked `PublicUseWaybillSample2024.zip`
returned HTTP 200, byte-range support, and 68,197,449 bytes; its first
ZIP member is `BEA_001_to_109.jpg` (JPEG document imagery), **not an
immediately ingestible structured waybill row**. No rail revenue fields
were extracted or validated. Treat this download as DOCUMENT / SCAN
PENDING rather than a clean data source; locate and inspect a documented
data-bearing member and verify its field dictionary before any import.
STB explicitly warns that public-waybill revenue may be masked and not
actual waybill revenue. Do not use it for customer recovery calculations.


### Subsequent STB triage: actual public-use fixed-width records found

The initial STB archive warning described only the first ZIP member.
An independent central-directory inspection subsequently identified **seven**
members, including the actual `PublicUseWaybillSample2024.txt`:
**539,561,337 uncompressed bytes** (66,413,233 compressed, CRC32
`3048824b`, ZIP member local offset `1783486`). The overall official ZIP
is 68,197,449 bytes. The public text data begins with **fixed-width
247-character ASCII records** separated by CRLF, not a CSV.

An original 262,144-byte range starting at the ZIP member was downloaded
directly from the STB source (range SHA-256
`51bdff79ade49491bcd5d3ef670a079a1d263372ef9dffb24ee8086a57b68059`).
The first **100 original records** were frozen as
`freight/fixtures/public_stb_2024_waybill_first100_fixedwidth.txt`,
24,900 bytes including line endings, SHA-256
`007a598863ba5e7a6b2a8e09b2f75c0ccabcb9588df7c582a2445c7d9967e1d4`.
`freight/public_stb_waybill_prefix_v1.py` and corresponding regression
tests verify the exact source bytes, fixed-width record layout, and reject
deliberate mutations.

**This supersedes the earlier “not immediately tabular” triage, but
does not certify decoded rail fields.** The 2024 STB guide must be independently
used to establish exact field boundaries, masks, redactions, sampling weights
and units before analyzing any values. In particular, published rail revenue
may be masked and must never be labeled as an authentic amount billed or
paid by a customer. This 100-row prefix is also not a representative
rail shipment sample; neither the full archive nor the entire text member
has been downloaded or CRC/hash verified.

Current combined bounded authentic public-source observations:
78 BTS FAF6 flow rows, 18 EIA price values, 11 historical carrier posted rates,
100 Census CFS public-use shipment records, and 100 STB public-use rail
waybill rows (original fixed-width bytes only). There are **zero**
independently verified customer invoices and **zero** verified recoveries.


### Verified fixed-width positions from the original STB 2024 guide

Primary official reference: https://www.stb.gov/wp-content/uploads/2024-STB-Waybill-Reference-Guide.pdf

**Table 4-6 (page 103, publication pagination)** documents all 247
fixed-width positions, including Waybill Date (1–6), Carloads (11–14),
STCC Commodity Code (36–40), Billed Weight (41–47), Actual Weight
(48–54), Origin BEA (104–106) and Destination BEA (126–128).
`freight/public_stb_waybill_prefix_v1.py` now checks these exact
original field positions on each of the 100 records without decoding
or making claims about the **potentially masked freight revenue**
positions 55–63.

**Waybill-date and accounting-period distinction (verified against the
original STB 2024 reference guide, Table 4-6 / Table 4-7):**

The six-digit waybill date (columns 1–6, `mmddyy`) is when the
originating railroad prepared the document. The separate four-digit
accounting period (columns 7–10, `mmyy`) is the month/year the study
waybill entered the railroad's revenue-accounting system.

The frozen first 100 records therefore contain 100 accounting periods in
**2024**, despite waybill-document dates from 2018 (14 records), 2020
(1 record), 2021 (20 records), and 2022 (65 records). The first original
record's `041118` waybill date means **April 11, 2018**, whereas its
`0324` accounting period means **March 2024**. This is a genuine
two-field distinction—not grounds to rewrite the 2018 date to 2024 or
to call the ZIP mislabeled.

**Remaining uncertainty:** The precise business process that led these
older waybills to be entered in 2024 accounts is not established by
the first 100 rows or the guide. No chronology or date distribution is
asserted for the entire published file. Source tests now independently
parse both fields, enforce valid dates and the 2024 accounting-year
histogram, and reject inconsistent accounting chronology. An accounting
year is not evidence of a 2024 shipment movement, customer invoice,
freight revenue charged, or recoverable overpayment.


### Census 2022 PUMS sampling and disclosure controls — verified against the original guide

Official source: [2022 CFS Public Use Microdata Sample Data Users Guide]
(https://www2.census.gov/programs-surveys/cfs/datasets/2022/cfs_2022_pums_users_guide.pdf),
issued January 2026, pages 2–4; original methodological source:
https://www.census.gov/programs-surveys/cfs/technical-documentation/methodology.html.

**What the genuine source supports:** The complete Census PUMS is documented
as **37,576,546** anonymized shipment records collected from approximately
50,000 responding establishments. Its shipped-goods value is in **dollars**,
shipping weight in **pounds**, and geographic distance in **great-circle
miles**. None is a freight carrier invoice charge or the rate actually
invoiced for a particular movement.

- Census `WGT_FACTOR` is a *survey shipment tabulation factor*, combining
  selection/design weights, subsampling, disclosure avoidance noise and
  poststratification; it is rounded to **one decimal** and top-coded at
  **3,588,000**. A few genuine records may have factors **under 1**, so a
  valid factor is positive—not necessarily >= 1.
- The published PUMS also truncates shipment goods value above
  **$30,000,000**, topcodes other large fields, rounds quantities, collapses
  some detailed geographic and commodity identifiers and adds privacy noise.
  It therefore cannot serve as a verified original invoice or identical
  replacement for confidential survey truth.
- Census explicitly cautions that PUMS estimates may differ substantially
  from its published CFS statistics and recommends the **published CFS
  tables whenever an official estimate is already available**.
- The publisher randomly ordered the original PUMS before assigning
  SHIPMT_ID, but RETALLY's deterministic first-100-row excerpt is **not
  a separately designed, variance-qualified representative estimator**,
  even with the full survey factors present. Population-shipment, total goods value,
  tonnage, carrier spend, average lane cost, variance, confidence intervals
  and recoverable amounts are **prohibited for that prefix**.
- The offline source checker now enforces the original 100-row SHA-256,
  one-decimal positive finite weight factors, published top-coded maximum
  factor and the pinned Census guide/non-extrapolation policy. Independent
  negative tests try forging the metadata to enable extrapolation and
  rehashing an impossibly large weighting factor; both must fail.
- **Still needed for genuinely statistical analysis:** complete 2022 PUMS
  file download and integrity validation; domain/industry coverage and
  geographies checked against official codebook; defensible weighted
  calculations; and separate replication/variance controls. Nothing in
  this document claims those gates have been satisfied.

These restrictions are **separate** from the 26 still-unverified historical
findings and 18 unmet human pilot approvals. Original customers, invoices,
payments, contract rates and real recoveries remain absent.


### Census-published Maryland weighted-goods-value demonstration (not derived from our 100 rows)

The original 2022 CFS PUMS Data Users Guide **printed page 7**
provides a fully worked, original-publisher Maryland-origin example:
`ORIG_STATE = 24` contains **612,317 source records** in the complete PUMS.
Census reports the weighted sum of merchandise/commodity values
`Σ(WGT_FACTOR × SHIPMT_VALUE) = $198,598,788,295`, with modeled
coefficient of variation **9.74%**.

The official example's CV uses the generalized variance function for a
total-value estimate:
`exp(a + b·ln(n) + c·[ln(n)]²)`, with `n = 612317`,
`a = 3.905`, `b = 0.011`, and `c = -0.010`. RETALLY independently
recomputes **9.74%** from these published constants; it **does not**
claim to have downloaded or recomputed the full PUMS weighted sum.
The exact frozen printed source values and prohibitions are stored in
`freight/fixtures/public_cfs2022_official_maryland_example.json`
and validated by
`freight/public_cfs2022_official_example_v1.py` with independent
negative tests.

**Do not conflate domains:** This guide demonstration covers Maryland-
origin shipments to **all** destinations and all modes in CFS-covered
establishments. The previously frozen BTS FAF6 Maryland-to-Pennsylvania
truck-only goods-value flow covers an entirely different model and
origin/destination/mode scope. Neither figure is customer transportation
spend, a tariff, a recoverable loss, or a refund.

This verified guide example is useful for testing population estimation
methodology with original published numbers and variance; **it does
not justify applying survey weights to RETALLY's 100-row extract**.


### Authentic federal adjudicated overcharge-related dispute: an award is not recovered cash

As a new, **separately labeled legal/evidence source** (not a shipment
benchmark), RETALLY examined the official Federal Maritime Commission
**Docket 2030(I)** publication. The agency's **April 28, 2026 Notice Not
to Review** records that its March 27 small-claims initial decision became
*administratively final*. The FMC ordered the respondent to pay **$8,668.79
in reparations** plus **$985.72 interest**, or **$9,654.51 total**,
by **May 13, 2026**.

Official original publication:
https://www2.fmc.gov/readingroom/docs/2030%28I%29/%2815%29%202030%28I%29%20Notice%20Not%20to%20Review%20%28public%29.pdf

This is authentic first-party government **award/order evidence** about a
third-party dispute, not a RETALLY engagement, lender/bank statement,
original billed-rate tariff, or independently witnessed refund.
**No payment confirmation has been inspected**. An official payment
order establishes a legal obligation recorded in the notice; it does NOT
establish a successful cash transfer, actual satisfaction of the order,
the respondent's current compliance, or money recovered for RETALLY.

The frozen factual receipt
`freight/fixtures/public_fmc_2030i_reparations_final_notice_2026.json`
records the exact agency docket/date/source, separates reparations from
interest in *integer cents*, and explicitly keeps
`actual_money_recovered_cents=null` and
`retally_customer_recoveries_cents=0`. It notes that only the
publisher-indexed text was reviewed, not an independently hashed complete
original PDF or any bank settlement statement.

The offline guard and negative tests in
`freight/public_fmc_adjudication_v1.py` /
`freight/test_public_fmc_adjudication_v1.py`
reject attempts to change awarded cents, add invented invoice rows,
describe a payable judgment as paid, or claim the award as RETALLY
customer proceeds. This example must remain a **separate external
adjudication category**, not be mixed with BTS/EIA freight-flow rows
or used to imply RETALLY has independently recovered any money.
This is historical research, not legal advice on another person's case.

Separate external confirmation of *receipt of funds* is required before
any source may graduate from `ADJUDICATED_AWARD` to
`ACTUALLY_RECEIVED_RECOVERY`. No external outreach, payment handling,
litigation action or customer contact is performed.


### Unified read-only Lab 14 public-evidence census

The source-specific validators now feed a single **sanitized, deterministic
read-only report** that reconciles source categories *without claiming they
are statistically or legally equivalent*:

```bash
PYTHONPATH=. python -m unittest -v freight.test_public_original_research_control
PYTHONPATH=. python -m freight.public_original_research_control \
  --out /tmp/retally-lab14-original-sources
```

This creates `public_evidence_census.json` and `index.html` with only
category/count/trust-status facts. The report does not copy the original
raw shipper records, introduce a prospect identity, disclose a carrier
customer contract, or store any private account credentials.

It independently checks **307 bounded source records/observations**
(78 BTS FAF6, 18 EIA, 11 dated carrier reference rates, 100 Census
public-use shipment records, 100 STB public-use waybill records),
**one separate original Census-published statistical worked example**
and **one separate, administratively final FMC reparations order**.
The last two are separate *evidence classes* and **are not additional
shipment observations**.

The source census rejects changes to source counts, a falsely reported
2024 STB shipment-year histogram, attempts to multiply the first 100
Census rows into national totals, claimed customer freight charges,
and conversion of an FMC payment order into verified recovered cash.

**Acceptance is limited to this unmerged research draft.** The report's
SHA-256 digest is a reproducible *local content-integrity checksum*,
not an externally signed government or bank receipt. The original
26 historical findings and 18 independent human pilot requirements
remain open. The client-facing website and production financial systems
are not modified.


## New source tier: actual historical government-REPORTED collections

In an independently sourced supplemental GAO evidence tranche (see
`freight/RESEARCH_PUBLIC_GAO_COLLECTIONS_20261018.md`) seven original,
public, first-party U.S. Government Accountability Office decisions
**report** nine historical transportation overcharge collection events:
three carrier-refunded payments and six government-applied offsets.
These are **real agency-published collection accounts**—substantively
different from an outstanding award—but not independently inspected
Treasury bank postings or original invoice/contract scans.

These cases include a mixed original refund+setoff (`B-152324`),
an assessed remaining amount not yet deducted (`A-14046`), a later
carrier-reimbursement certificate not proven executed (`B-166167`),
and conflicting later supplemental-claim dollar representations
(`B-146511`). Every event is stored as an integer-cent and source
URL-bound assertion with negative tests prohibiting duplicate money,
pending-collection promotion and fabricated original invoice evidence.

**Do not inflate the source record tally:** the unchanged **307**
bounded BTS/EIA/carrier/Census/STB source records remain a separate
category. The **one** Census statistical worked example, **one** FMC
adjudicated award, and **six** GAO historical collection decisions are
different document/evidence categories. They cannot be pooled as
customer freight bills or used to calculate RETALLY's recovery rate.

The consolidated `freight/public_original_research_control.py`
report now exposes the original GAO cases as a distinct **government
collection narrative** tier with **zero** independent Treasury/bank
verifications and **zero** real RETALLY customer collections.
All original 26 historical defects and 18 independent human gates
remain open. Source-integrity CI must pass on the exact final draft head;
no private carrier documents, outbound contact, production change or
payment authority is implied.


### Original GSA FY2023 corrective vendor payment (separate from recoveries)

The first-party GSA FY2025 congressional justification reports it **paid
approximately $29.6 million back to a DoD transportation vendor** after
contracting-officer findings that earlier GSA overcharge notices were
wrong. A further potential **$11.8 million** was described as
unresolved, **not paid**. This is a real public government accounting
correction and is intentionally **a negative-control record**:
the amount represents GSA's own reported payment **to** a vendor
to correct erroneous collections, not actual customer freight overcharge
refunds or RETALLY revenue.

See `freight/RESEARCH_PUBLIC_GAO_COLLECTIONS_20261018.md` and
`freight/public_gsa_false_positive_payment_v1.py` for exact source
URL, accounting provenance, distinction from seven old GAO historical
collection decisions and the separate unpaid FMC award. The source
census treats it as a **standalone corrective government payment
statement**, and **does not** increase the **307** bounded public
freight research rows. The source has not independently verified
bank transaction/voucher bytes or private customer billing.
No source authorizes a current recovery claim, automatic setoff,
collection from carriers, extra schedules or public savings advertising.

**Additional primary PDF source (August 25, 1980):** Original GAO
decision [B-197658](https://www.gao.gov/assets/b-197658.pdf)
reports **$1,109.67 refunded by the freight carrier** and the
**$540.12 remaining shortfall later recovered by setoff** from an
$1,649.79 assessed overcharge. The federal statement's original
$7,820.42 amount paid minus the two separately evidenced
collections equals $6,170.63 allowed charges. The original PDF
page text was directly reviewed; **independent original PDF
SHA-256 and bank/Treasury posting verification remain missing**.
Do not treat the two events as two shipments or as a RETALLY recovery.


### Adverse source-ground-truth control: GAO B-192974 (1979)

GAO's original four-page decision
[Review of GSA Setoff Action Against Carrier](https://www.gao.gov/products/b-192974)
held that the government had **improperly deducted $5,141.05**
from post-bankruptcy-petition payables for an older alleged carrier
overcharge. A separately documented **$2,147.59** pre-petition
deduction was considered proper. The former amount had actually
been **set off** before GAO found it improper; the decision's
instruction to allow the successor carrier's claim if otherwise
correct does not prove it had been reimbursed.

This is **not** a newly confirmed recovered overcharge, customer
invoice or present-day rule governing private shipments. It is
a separate `GAO_SETTLEMENT_REVERSAL` evidence tier, deliberately
excluded from the seven original GAO historical positive collection
decision counts and the 307 non-equivalent public freight rows.
The negative validator, source artifact and exact case accounting
are in `freight/RESEARCH_PUBLIC_GAO_COLLECTIONS_20261018.md`.


### Another original GAO applied setoff later conceded improper

[GAO B-197184 (March 26, 1980)](https://www.gao.gov/assets/b-197184.pdf)
records GSA's earlier **$475.36 deduction** from Yellow Freight for
an alleged overcharge originally collected by a separate carrier.
GSA later **acknowledged the deduction was improper**, and GAO
dismissed the review as moot with only a conditional allowance
of the carrier's claim—**no actual reimbursing bank/Treasury payment
has been independently proven**.

The case is kept distinct from older GAO B-192974's **$5,141.05**
improper bankruptcy-related offset, and from the seven
historical *affirmative collection* decisions. It is a
second `GAO_APPLIED_OFFSET_LATER_DISALLOWED` negative source, not a
refund actually recovered by RETALLY, or even proof that the carrier
was subsequently made whole.

Its exact source URL, 1980 memorandum and conditional repayment
limits are documented in
`freight/RESEARCH_GAO_B197184_IMPROPER_SET_OFF_1980.md`.
The source census keeps all **307** frozen market/survey reference
rows separate from these original GAO legal histories.
