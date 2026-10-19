# RETALLY Lab 14 — Original GAO reports of actual historical freight collections

**Source-only research | 18 October 2026 | DRAFT | no customer or production operations**

## Why this is stronger than another published surcharge or awarded judgment

Unlike a fuel-surcharge schedule or an administrative order instructing a respondent to pay,
these **original federal GAO decisions expressly report that public agencies
or carriers had already executed a deduction/setoff or refund** during their
historical accounting. This is the strongest *reported collection event*
category in this bounded public research set. It still does **not** establish
an independently authenticated bank or Treasury posting, permanent final
balance, current contract authority, or a RETALLY customer recovery.

Original first-party cases, each checked against its publisher page:

| GAO case / official report | Government-reported earlier bill payment | **Collection described by GAO** | Still pending / possible later adjustment |
|---|---:|---|---|
| [B-148465](https://www.gao.gov/products/b-148465), 1962 | $546.88 | **$61.22 offset against other carrier payables**, after no voluntary refund | GAO upheld settlement; original BOL not independently retrieved |
| [B-148981](https://www.gao.gov/products/b-148981), 1962 | $1,755.00 | **$134.44 explicitly carrier-refunded** after an invoice audit | Carrier later made additional claims that GAO rejected; only one clearly identified shipment used |
| [B-152324](https://www.gao.gov/products/b-152324-0), 1964 | $1,835.25 | **$514.50 voluntarily refunded**, then another **$740.27 deducted** (same shipment) | Remaining described allowable charge: $580.48 |
| [A-14046](https://www.gao.gov/products/14046), 1926 | $889.63 across three rail shipments | **$83.58 already deducted** | **Additional $44.17** still described as due and to be deducted/refunded; NOT already collected |
| [B-166167](https://www.gao.gov/products/b-166167), 1969 | $4,231.77 | **$3,016.32 setoff collected**, according to GAO | GAO was **authorizing a $1,050.83 refund back to the carrier**; proof of execution not inspected; no final net inferred |
| [B-146511](https://www.gao.gov/products/b-146511-2), 1965 | $152.05 | **$20.74 recovered by deduction** in 1951, GAO says | Later supplemental claim narrative also cites **$20.70 and $20.76**; those alternate figures are NOT added as separate collections |
| [B-197658](https://www.gao.gov/assets/b-197658.pdf), 1980 | $7,820.42 | **$1,109.67 carrier-refunded, then $540.12 recovered by setoff**, total $1,649.79 | Three bills of lading represented one shipment under the GAO decision; allowable charge $6,170.63; independently inspected bank/Treasury posting absent |

These are **seven distinct agency decision records** and **nine separately
described collection events** (three voluntary refunds and six applied
government deductions). The nine events are *not* a national recovery
statistic. Cases were selected because their original public record describes
a historical collection action, not through representative freight-invoice
sampling. No dollar total from these cases should be marketed as validated
current savings or RETALLY revenue.

## The evidentiary hierarchy

1. **Public carrier or EIA rate:** published schedule/index only; applicability and actual billing unknown.
2. **Source-supported audit finding or award:** an amount may be due, but no transfer or offset was necessarily made.
3. **Agency's original administrative decision REPORTS a carrier refund or executed offset:** authentic publisher assertion of historical collection; **separate bank, Treasury, account statement and original source documents still not inspected**. This is the level the seven GAO cases support.
4. **Authenticated proof of remitted/posted payment, contemporaneous freight bill, applicable historical tariff and a final case disposition:** stronger corroboration, **none obtained for these selected cases**.
5. **Verified RETALLY client recovery:** requires customer authority, original charge, agreement, payment/credit evidence and owner-controlled fee/case accounting. **None obtained**.

The previous third-party FMC 2030(I) `$9,654.51` reparations notice
is **category 2**: an adjudicated award/order, not payment.
The original GAO records are a stronger **category 3** collection narrative
but remain far below categories 4 and 5. An administrative source saying
a deduction was made is not independent confirmation from the separate
Treasury disbursement or the recipient's bank.

## Arithmetic, unit and duplicate safeguards

All amounts are frozen as **integer historical U.S. cents**, not current-value
dollars or assumed 2026 prices. Case `B-152324` reconciles:
`$1,835.25 - $514.50 - $740.27 = $580.48`.
Original 1980 GAO decision `B-197658` independently documents
one 107,129-pound lot of steel posts, physically carried using three
bills of lading; original charges paid **$7,820.42**, correct
truckload charges **$6,170.63**, assessed overcharge **$1,649.79**.
The carrier **refunded $1,109.67**, then the government **recovered the
remaining $540.12 by setoff**. This is one source-identified *shipment*
with two different collection events—not two recoveries to two different
customers. The government PDF's index-accessible full text was inspected,
but its binary bytes have **not** been independently downloaded/hashed,
and no actual external bank/Treasury posting was examined.

Case `A-14046` reconciles the later assessment:
`$83.58 deducted + $44.17 still due = $127.75`.
Neither the missing `$44.17` nor the `$1,050.83` reimbursement to the
carrier has been counted as a completed transaction.

`B-146511` has three different dollar expressions in the GAO narrative.
The transaction-specific original overcharge **$20.74** is kept separate
from the conflicting supplemental-claim variants `$20.70` and
`$20.76`. Those variants are **not additional collections or additional
case claims independently proved**.

The code in `freight/public_gao_historical_collection_v1.py` uses
exact, publisher-bound case IDs, URL slugs, publication dates, source
amounts and allowed collection types to verify the small facts ledger.
`freight/test_public_gao_historical_collection_v1.py` runs adversarial
altered money, double-counted collection, forged source, fabricated invoice,
false RETALLY recovery, unpaid amount, future deduction and changed
refund-to-carrier negative tests. CI:
`PYTHONPATH=. python -m unittest -v freight.test_public_gao_historical_collection_v1`.

## What remains unverified

- No original actual invoice/GBL image, private carrier contract, payment
  voucher image or independent Treasury bank record was downloaded or
  reconciled for these GAO cases; public descriptions of them appear in
  the source decisions.
- No independent check of all appeals, refunds *of earlier government offsets*,
  subsequent legal changes or final as-of-current accounting. In particular,
  `B-166167` explicitly contemplated restitution to the carrier.
- Government statutory deduction authority and military/rail tariff
  rules **do not automatically apply to a private RETALLY customer**,
  nor do decades-old quotations prove a current rate.
- No external customer identity, client money, current-rate contract,
  invoice-level error, actually received RETALLY recovery, independent
  customer pilot approval or marketing-performance permission is present.
- RETALLY Lab 14's 26 historical original findings remain
  **OPEN_UNVERIFIED**; the 18 human first-customer gate requirements
  remain unmet. No new financial product is activated by this research.

**Disposition: ORIGINAL_GAO_AGENCY_COLLECTION_ACCOUNTS_VERIFIED_AS_PUBLISHED;
INDEPENDENT_BANK_VERIFICATION_MISSING; NO RETALLY CASH OR RECOVERY CLAIM.**


## Contemporary false-positive repayment — GSA's own financial report

The U.S. General Services Administration's **FY 2025 Congressional
Justification, Transportation Audit Contracts and Contract
Administration**, printed pages P-2 through P-5, reports that **in FY
2023 the program made a voluntary $29.6 million payment back to a
Defense Department vendor** following contracting-officer decisions
that earlier Notices of Overcharge were erroneous.

Original first-party source:
https://www.gsa.gov/system/files/GSA%20FY%202025%20Congressional%20Justification.pdf

The report's financial narrative allocates approximately **$20.7 million
from the receipt account** and **$8.9 million from the suspense
account** to that payment, summing to the $29.6 million the agency
reported. The report separately says litigation **could require up
to another $11.8 million** paid to that vendor; this amount is
*contingent/unresolved*, **not a second confirmed payment**.

Independent related public case context:
[GAO B-421982](https://www.gao.gov/products/b-421982) describes
Crowley's defense transportation contract overcharge disputes.
The underlying contract's competent contracting officer reached
decisions contradicting GSA's audit rate interpretation. Those
statutory/contractual boundaries are **specific to that federal
procurement setting** and cannot be generalized to RETALLY's
potential private business customers.

`freight/fixtures/public_gsa_2025_transport_audit_erroneous_nocs_payment.json`
freezes only the original GSA source, amount, fiscal year, payment
**direction** and uncertainty. The offline checker and tests in
`freight/public_gsa_false_positive_payment_v1.py` strictly reject:
- calling the **government-to-vendor refund** money recovered **by RETALLY**;
- treating the possible **$11.8 million additional liability** as already paid;
- claiming underlying invoice/contract image review, a personally inspected
  bank posting or independently hashed complete original GSA PDF;
- silently mixing this corrective repayment with older GAO
  government-reported overcharge collections and the FMC unpaid award.

**Critical conclusion:** A notice or deduction can turn out to be
erroneous; collection is not permanent until contractual authority,
independent review, repayment/reversal and final financial custody
are established. Claiming financial success too early exposes the
customer to additional legal and accounting risk. The GSA document
is first-party official publisher evidence of an accounting payment
reported by the agency, NOT a direct bank/Treasury transfer receipt
inspected by RETALLY.

As separately documented in GSA's FY2026 congressional justification,
GSA was beginning to wind down its centralized Transportation
Audits program after changing/delegating agency authority in 2025.
These historical GAO/GSA cases **do not establish today's legal
scope or a private company's power to offset carrier balances**.

No real RETALLY client/customer freight invoice, actual carrier
settlement, real customer recovery or recoverable-performance figure
has been acquired or validated.


## Additional adverse GAO collection decision: offset applied, but legally disallowed (1979)

**Original independent U.S. GAO publication:**
[Review of GSA Setoff Action Against Carrier — B-192974 (March 29, 1979)](https://www.gao.gov/products/b-192974)
([four-page Comptroller General PDF](https://www.gao.gov/assets/b-192974.pdf)).

This case is a deliberate counterexample to the mistaken claim that **any
executed deduction equals a valid or permanently retained overcharge
recovery**.

Braswell Motor Freight filed for bankruptcy in December 1976, followed
by confirmation of its arrangement in July 1977. GSA later attempted
to collect older transportation overcharge claims by deducting sums
the government separately owed the carrier:

| Event explicitly distinguished by GAO | Historical amount | Source determination |
|---|---:|---|
| Pre-petition carrier payables set off against pre-petition claims | **$2,147.59** | Properly offset, per this specific original decision |
| Post-petition carrier payables set off against pre-petition claims | **$5,141.05** | Offset previously executed **but improper**, lacking debt mutuality |
| Additional asserted pre-petition overcharge claims not filed/proved in the bankruptcy | **$7,473.08** | Discharged/uncollectible under the case facts, **not cash recovered** |
| Separate proof of claim filed in the bankruptcy | **$1,430.24** | A filed claim, **not evidence of payment** |

GAO concluded that GSA should allow Yellow Freight's $5,141.05
reimbursement claim **if otherwise correct**. That is a legal outcome
or direction, not independently inspected bank proof that the
government actually **paid** the carrier. The filing/offset/claim
categories are not automatically additive: the agency's additional
overcharge claims, filed proof, and pre- versus post-petition
bills payable represent distinct underlying accounting buckets.
Arithmetic must not manufacture a false final balance.

`freight/fixtures/public_gao_b192974_wrongful_setoff_1979.json`
and `freight/public_gao_setoff_reversal_v1.py` pin the GAO source,
historical bankruptcy dates, legally upheld $2,147.59 and disallowed
$5,141.05, absence of independently confirmed repayment, no private
customer legal authority and no RETALLY cash. The dedicated negative
tests fail on changed money, forged repayment, reversed legal finding,
fictional invoices, or current-day setoff authorization.

**Critical distinction:** This is an **additional adverse original
decision**, not an eighth positive GAO collection case, and not an
extra source row in the 307 BTS/EIA/carrier/Census/STB observations.
Its direct source evidence provides a strong reason for conservative
contract/authority/custody controls. The 1979 Bankruptcy Act rules
are **not** assumed to be a statement of current bankruptcy law or
binding on prospective private commercial clients.

**Evidence tier: PUBLISHED_GAO_SETTLEMENT_REVERSAL_OR_DISALLOWANCE;
PAYMENT_BACK_UNVERIFIED; FINAL_NET_RECOVERY_UNVERIFIED.**


## Original government transport-audit fund account: FY2023 ACTUAL vs later PLANS

The same official
[GSA FY2025 Congressional Justification](https://www.gsa.gov/system/files/GSA%20FY%202025%20Congressional%20Justification.pdf),
**Permanent Budget Authority, printed page P-5** (PDF page 294 if counted
from page 1), reports actual and planned **special fund** accounting
in **thousands of dollars**:

| Official government accounting row | FY2023 actual | FY2024 plan | FY2025 plan |
|---|---:|---:|---:|
| Special Fund Receipts | **$12,354 thousand** | $4,168 thousand | $12,506 thousand |
| Transfer to Suspense Fund to Pay Transportation Service Provider | **($20,674 thousand)** | Not shown | Not shown |
| Annual appropriated obligations | **$10,960 thousand** | $9,728 thousand | $11,565 thousand |

**Crucial limitations:** A 2023 receipt-account inflow is a distinct fund
accounting line, not documentary evidence of any one freight customer
having been overcharged. FY2024 and FY2025 rows are **budget plans**, not
actual receipts. The $20.674 million transfer draws from a fund with
prior-year balances; do not subtract it from $12.354 million in **same-year
receipts** and misinterpret the result as the program's return on
investment or recoverable cash.

The original GSA note also says the vendor payment was approximately
$29.6 million, funded by about $20.7 million from the receipts account
and $8.9 million from the suspense account. The precise table transfer
$20.674 million rounds to **$20.7 million at the one-decimal-million
narrative precision**. The approximate narrative is not a bank voucher
or a cents-accurate transferred sum.

`freight/fixtures/public_gsa_transport_audit_fund_FY2025_report.json`
preserves seven original accounting numbers with separate fiscal year,
reported ACTUAL/PLAN status, original unit `USD THOUSANDS`, precise
negative transfer direction and public source page. The isolated offline
validator and negative tests in
`freight/public_gsa_transport_audit_fund_v1.py` reject:
- presenting FY2024 or FY2025 plans as realized receipts;
- changing reported amount, year, transfer sign, currency units, or source;
- claiming the payment to the vendor was customer money recovered;
- confusing the fund with a verified individual customer invoice,
  independently authenticated Treasury/bank posting or available
  RETALLY fee-based recovery performance.

This source is an extension of the **same GSA report already used for
the FY2023 $29.6 million corrective vendor payment**, not a new customer
case or one of the seven GAO positive collections. It adds **seven fund
accounting line items** kept outside the 307 bounded BTS/EIA/CFS/STB
freight market data observations and outside real customer recoveries.


## Later authoritative case-status update: D.C. Circuit Crowley decision (July 2025)

**Direct original appellate opinion:**
[Crowley Government Services, Inc. v. GSA, No. 23-5183, July 18, 2025]
(https://media.cadc.uscourts.gov/opinions/docs/2025/07/23-5183-2126136.pdf),
U.S. Court of Appeals for the D.C. Circuit (56 pages including dissent).

This opinion is **more recent than GSA's FY2025 budget discussion of
FY2023 events**. A majority held that the particular audit power in
31 U.S.C. § 3726(b) concerned bills submitted by carriers and freight
forwarders, and that **Crowley acted as an intermediary—not a carrier
under the DFTS I agreement at issue**. It reversed the lower
court's broader GSA-audit-scope ruling and remanded for further
proceedings.

The official opinion also describes more than **50,000 Notices of
Overcharge** alleging **about $37 million** from 2018 through
August 2021 and later states that the accumulated notice count
exceeded 100,000. These are historical **agency allegations**, not
original customer invoices RETALLY obtained, independently audited
transportation charges, actual bank transfers or validated recovered
savings. It notes **three contracting-officer decisions** that
rejected the contested GSA notice interpretations.

The court separately referenced a **$11.8 million damages demand**
in a Court of Federal Claims action in the course of assessing its
own jurisdiction and whether the appeal remained a live dispute.
**The D.C. Circuit did not award Crowley $11.8 million or prove
any corresponding bank payment.** A claim's precise post-July-2025
financial disposition or its status today in October 2026 has
not been independently confirmed here.

The source is frozen in
`freight/fixtures/public_cadc_crowley_2025_transport_audit_authority.json`
and separately checked by `freight/public_crowley_appeal_scope_v1.py`
and its negative tests. The checks reject altering the case
scope, converting $37 million of **allegations** into proven
errors, converting the $11.8 million **demand** into a judgment
or payment, inferring a current private commercial setoff
right, or asserting original bank/PDF byte proof not obtained.

This is **one separately counted original federal court decision**,
not a new GAO source-case collection, new customer invoice,
government receipts-account row, or 308th bounded public freight
sample record. It does not add verified RETALLY revenue or
change the original 26 historical/18 human approval holds.

**Decision tier: ORIGINAL_2025_APPELLATE_AUTHORITY;
PAYMENT_CLAIM_NOT_ADJUDICATED_IN_THIS_APPEAL;
NO_PRIVATE_CUSTOMER_RECOVERY_AUTHORITY.**


## Independent contract-interpretation counterexample — GAO B-261127 (1996)

**First-party original publication:** [Matter of Canupp Trucking,
B-261127, February 15, 1996](https://www.gao.gov/products/b-261127).
This is a separately counted **adverse rate-dispute decision**, not an
eighth positive historic GAO collection, another customer invoice,
or another of the 307 original market/survey observations.

The government alleged that Canupp's `Note 12` pickup/delivery pricing
should use the entire **one Government Bill of Lading (GBL)** as the
unit of shipment. But the specific MTMC/NAVMTO tender **600029** had
no definition incorporated for that particular Note, and **qualified
government staff affirmatively advised the carrier, before billing,
to use each Transportation Control Number (TCN)**. The carrier then
used that interpretation, it reported, on 1,062 GBLs and remained
uncontested for over three years. GAO found the **TCN-based Note 12
charges valid** under that contract, though it **denied additional
Note 14 terminal-service charges** as duplicative.

### A GAO-published *actual billed-charge example* that did not produce an overcharge

| Original published component for GBL `C-8,141,261` | Amount |
|---|---:|
| 63 TCNs charged $25.00 minimum | $1,575.00 |
| Two further TCN charges | $28.50 + $55.90 |
| **Carrier's reported Note 12 charges** | **$1,659.40** |
| Government's proposed *one GBL* rate, 14,320 pounds × $2.00/cwt | $286.40 |
| **Mathematical difference if government's interpretation applied** | **$1,373.00** |
| GAO-sustained recoverable **Note 12 overcharge** | **$0.00** |

This is a publisher-documented bill-line arithmetic example, **not**
a downloaded carrier invoice image or customer-supplied signed tariff
copy. No independent bank payment, issued credit memo, actual customer
contract or current private rate authority was obtained.

The original decision independently references the *opposite*
[GAO B-197658 (1980) Yellow Freight decision](https://www.gao.gov/assets/b-197658.pdf),
which **upheld a government $1,649.79 refund and setoff** where a single
steel-post lot was tendered simultaneously despite three individual
carrier bills of lading. The **specific tender definition and
authorized prior course of billing differ** between these two cases.
Neither a blanket `one BOL means one shipment` rule nor a rule
that all split BOLs may be combined would fit both outcomes.

**Software protection added:** A new isolated, typed original-source
validator `freight/public_gao_b261127_contract_counterexample.py`
recomputes all the 1996 components in integer cents, compares that
decision to the older, existing GAO B-197658 source validator, and
requires **zero** recoverable Note 12 overcharge in the 1996 case.
Its adversarial tests reject changed charges, counts, source URLs,
fake contract evidence, fabricated carrier refunds, ignored
prebilling government approval or claims that the $1,373.00
difference is RETALLY savings.

The consolidated original research report now separately classifies
**seven historical GAO government-reported collection decisions**,
**one 1979 later-disallowed setoff** and **one 1996 mathematically
disputed but expressly carrier-upheld tariff interpretation**, plus
independent GSA budget, Court of Appeals, Census, FMC and public
market-source material. None establishes an independently authorized
commercial recovery claim, a customer refund, retained client cash,
or a present-day legal precedent automatically governing private shippers.

**Operational gate:** For a real RETALLY audit, obtain and authenticate
the *effective customer contract, incorporated tariff and amendments,
prior authorized billing interpretations, relevant shipment/tender
facts and paid invoice* before computing a recoverable difference;
then require a separate post-dispute credit/payment receipt. These
historical GAO documents do not supply that customer authority.
