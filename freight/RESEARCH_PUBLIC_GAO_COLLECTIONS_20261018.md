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

These are **six distinct agency decision records** and **seven separately
described collection events** (two voluntary refunds and five applied
government deductions). The seven events are *not* a national recovery
statistic. Cases were selected because their original public record describes
a historical collection action, not through representative freight-invoice
sampling. No dollar total from these cases should be marketed as validated
current savings or RETALLY revenue.

## The evidentiary hierarchy

1. **Public carrier or EIA rate:** published schedule/index only; applicability and actual billing unknown.
2. **Source-supported audit finding or award:** an amount may be due, but no transfer or offset was necessarily made.
3. **Agency's original administrative decision REPORTS a carrier refund or executed offset:** authentic publisher assertion of historical collection; **separate bank, Treasury, account statement and original source documents still not inspected**. This is the level the six GAO cases support.
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
