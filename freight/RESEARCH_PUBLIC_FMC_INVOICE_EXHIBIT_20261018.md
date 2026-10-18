# RETALLY Lab 14 — First reproduced invoice in a public FMC filing (Docket 17-05)

**Source-only research • 2026-10-18 • Separate from all RETALLY customers**

## Provenance / status

Official original public Federal Maritime Commission Reading Room PDF:
https://www2.fmc.gov/readingroom/docs/17-05/17-05_Cmpl_sup_rcd.pdf/

The original **113-page** public supplemental filing is styled:
*CMI Distribution, Inc.'s Response to the Presiding Judge's August 16, 2017
Order to Supplement the Record*, docket **17-05**. It contains photographic
reproductions of original Service by Air documents as litigant-filed exhibits.
The publicly indexed PDF text for zero-based page **19** describes an invoice
issued by Service by Air to CMI; the adjacent page **20** contains an overlapping
invoice rendering with inconsistent OCR total glyphs.

**Critical:** This is not an independently verified carrier-issued original
record obtained directly from the carrier. The pages were *filed by a party
to litigation*, and an actual separately authenticated original PDF, original
carrier billing ledger, bank record and contemporaneous private contract have
NOT been obtained. Direct image inspection was unavailable in this research
tool run; only the publisher-indexed OCR has been reviewed. Do not claim
source-image authentication or that page 20 is a second invoice.

## Four source-OCR charge candidates (one document, not two transactions)

| Charge label in reproduced invoice | Candidate OCR amount |
|---|---:|
| Air freight | $5,400.00 |
| Import duty/tax | $1,712.93 |
| Container stripping | $1,123.00 |
| Appointment delivery | $950.00 |
| **Arithmetic sum** | **$9,185.93** |

The *first* indexed page transcribes total **$9,185.93**, which is exactly
the sum of the four lines. The adjacent second reproduction contains OCR
noise in the total. **This corroborates arithmetic internal consistency,
not perfect source-image recognition, actual payment, rate validity, or loss.**
The published complaint also alleges that the related container actually
moved by **ocean** despite an "Air Freight" line label. Those are
**litigant allegations**, not established court findings for the selected
charge; a mislabeled accessorial or demurrage item remains plausible until
contract, ship route, carrier data and original charge basis are verified.

The filing alleges numerous other air/ocean or detention discrepancies,
including distinct figures and additional freight bills. They are
**not assumed to concern this same selected invoice**. Do not combine
charges across invoices, treat multiple image reproductions as multiple
paid bills, or infer aggregate losses.

## Data-integrity system

Strict fixture:
`freight/fixtures/public_fmc_17_05_invoice_image_candidate_20261018.json`

Offline source validator:
`freight/public_fmc_invoice_exhibit_candidate_v1.py`

Adversarial tests:
`freight/test_public_fmc_invoice_exhibit_candidate_v1.py`

Run `PYTHONPATH=. python -m unittest -v
freight.test_public_fmc_invoice_exhibit_candidate_v1`.

Tests and CI pin the original docket/URL, 113-page context, page indices,
four charge names and cent-exact totals. They reject extra fabricated
invoices, false paid/bank proofs, invented private contracts, re-labeling
the disputed ocean/air assertion as adjudicated fraud, changed monetary
figures or suppression of known OCR ambiguity.

**Outcome:** `PUBLISHED_LITIGANT_INVOICE_REPRODUCTION_CANDIDATE`;
`REAL_ORIGINAL_CARRIER_INVOICE_INDEPENDENTLY_AUTHENTICATED = FALSE`;
`INVOICE_OVERCHARGE_PROVEN = FALSE`;
`RETALLY_RECOVERED_CENTS = 0`;
`PRODUCTION_USE = NO-GO`.

This is additional source-document **quality** evidence, not an extra
Census/STB population observation, not one of the existing seven GAO
government-reported collection cases, and not an actual RETALLY
client invoice. No hosted feature, payment or carrier contact was added.
