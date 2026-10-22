# RETALLY — primary-source freight recovery evidence addendum (2026-10-19)

**Use: research-only. No RETALLY recovery, actual client testing, or commercial invoice-use rights are established by these records.** Primary-source URLs below point to public government decisions and creditor claim records; no underlying PDF bytes, third-party invoice rows, customer details, or rate tables are copied into this repository. Do not present these as customer results.

## Evidence classification

- **Historical positive control / adjudicated offset:** a published federal audit decision identifies a paid freight charge, a stated controlling rate/classification or rating error, a government deduction from carrier amounts otherwise payable, and the decision upholding that action. The decision is official historical *narrative evidence* of a successful administrative offset, **not** a complete portable invoice+rate+bank benchmark or proof the RETALLY engine can find it.
- **Historical partial positive / offset without complete amount base:** an official decision states a deduction, but the original invoice total or full per-shipment allocation is absent. Useful for workflow design only.
- **Negative control / noncash disposition:** a filed creditor claim decreases because a legal liability transfers between entities, or an invoice's open balance changes with no traced credit/payment; these must never be called overcharges, refunds, cash recovered, or RETALLY savings.
- **Production/independent validation (not achieved):** rights-cleared original invoice and underlying carrier record, BOL/PRO, effective rate/tariff/contract, independent shipment classification/weight and blind adjudication, plus payment/credit/offset evidence from an authoritative ledger. Isolate labels from development and measure actual RETALLY accuracy.

## Source A — strongest complete decision narrative: GAO B-223311 (August 3, 1987)

**Original authority:** https://www.gao.gov/products/b-223311-0

- Government Bill of Lading **R-0544179**; Navy, Yellow Freight System; July 1983 shipment (2,890 pounds, 34 cartons).
- Original billed **and collected** class-100 freight: **$727.53**, supported in the decision by **NMFC 156600 sub 6** and **Rocky Mountain Motor Tariff Bureau ICC 521-C**.
- Carrier later issued a supplemental bill and was **paid another $4,217.63** using class 400, NMFC 41015 sub 1, on a competing "air cargo containers" description.
- GSA challenged that additional charge; after the carrier refused a refund, GSA **deducted $4,217.63 from amounts otherwise due the carrier**. GAO **sustained** the deduction using the bill-of-lading commodity description and producer evidence. Nominal aggregate collected before deduction is $4,945.16 (= $727.53 + $4,217.63).
- **Source strength:** specific shipment ID, disputed rating, rate authority reference, amount paid, agency's collection mechanism, final decision. **Limit:** original bill, tender, full governing historical tariff and financial offset ledger are referenced, not exposed as a portable joined record. GAO reports the offset; no separate bank statement has been examined.

## Source B — paid -> corrected -> deducted sequence: GAO B-160344 (July 18, 1967)

**Original authority:** https://www.gao.gov/products/b-160344

- Government BOL **B-5378637**, carrier **Georgia Highway Express** bill **141**, dated 1962/63. Carrier **paid $275.17** in March 1963, class 400, $18.53 per 100 lb, 1,485 lb, NMFC 14440.
- Government **DD Form 1352** correction changed the commodity description to NMFC **12400**, class 200, $9.38 per 100 lb: allowed charge **$139.29**.
- The decision explicitly states **$135.88** overcharge (= $275.17 − $139.29), **deducted December 1965** after refusal to refund; the carrier's reclaim was disallowed, and GAO upheld the settlement.
- **Source strength:** independently stated payment, corrected rate, original/corrected classifications, adjustment amount and deduction date. **Limit:** the original bill, full tariff and DD Form 1352 images, offset ledger and supporting technical reports are not embedded in the published decision. Other shipments in the opinion are not separately labeled.

## Source C — independent carrier challenge and photo-backed classification: GAO B-189100 (December 27, 1977)

**Original authority:** https://www.gao.gov/products/b-189100

- Government BOL **A-6018184**; **Yellow Freight** collected **$3,567.18**; GSA issued an overcharge notice for **$2,634.38** and, after no refund, **collected it by deduction**.
- Initially disputed NMFC **41050** container classification versus **41060**. The source states further shipper photographic/report evidence established the corrected classification and GAO upheld GSA's settlement.
- **Source strength:** paid amount, erroneous classification reason, shipment BOL, explicit noncash government offset and adjudicated carrier objection. **Limit:** no original carrier bill, photograph, tariff pages or independent Treasury offset ledger in the public text. $932.80 is a *computed remainder*, not independently sourced per-line invoice data.

## Source D — routing/rate offset with incomplete invoice base: GAO B-143048 (September 1, 1960)

**Original authority:** https://www.gao.gov/products/b-143048

- Carrier **Cooper-Jarrett**, bill **1714**, bills of lading **AF-5072627 and AF-5072670** (two shipments), charged $10.69/100 lb, versus a $7.65/100 lb available-rate basis in **Rocky Mountain Motor Tariff Bureau U.S. Government Quotation 43-D, item 6980**.
- The decision says **$130.30** of overcharge was **administratively deducted** after refund refusal; carrier challenge rejected.
- **Limit:** no complete original paid bill amount or per-shipment distribution. **Never convert the joint $130.30 to two independent invoice-level labels.** This case is a *partial* historical control, not suitable for the strict full-delta numeric assessor.

## Negative control — GlobalTranz, Walker & Zanger, Artivo

- Public [GlobalTranz original proof of claim 10002 and broker invoice/statement attachments](https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/10247) files **$25,954.47** against debtor Walker & Zanger, LLC.
- [Public later claims register](https://document.epiq11.com/document/getdocumentbycode?docId=4596109&projectCode=MCX&source=DM) registers **$1,496.52** for the same creditor, debtor and claim identifier, a difference of **$24,457.95**.
- The existing PR #487 [court research](GLOBALTRANZ_PUBLIC_RECONCILIATION_RESEARCH.md) identifies [March 20 Docket 593, PDF page 27](https://document.epiq11.com/document/getdocumentsbydocket/?docketId=1216147&projectCode=MCX&docketNumber=593&source=DM) and [signed May 29 Docket 623, PDF page 7](https://document.epiq11.com/document/getdocumentsbydocket/?docketId=1227468&projectCode=MCX&docketNumber=623&source=DM), documenting **$24,457.95 transferred to Artivo in connection with the sale**. The [August 26, 2025 buyer closing announcement](https://transomcap.com/news/artivo-surfaces-backed-by-transom-capital-completes-acquisition-of-walker-zanger-and-anthology-brands-from-mosaic-companies/) confirms the acquisition closed, *not* payment to GlobalTranz.
- **Independent-read boundary, October 19:** the filed proof-of-claim and federal GAO full decision text were publicly accessible during this review; the Epiq direct signed-order/objection document links did **not** reopen in the current public-web interface. The exact **Artivo** explanation is retained from PR #487's documented prior source-PDF review, **not presented as newly, independently reopened docket pages**. A claim-value arithmetic check or outside acquisition announcement alone cannot prove that claim-specific schedule's content.
- No original controlling freight rate agreement, carrier-specific reweigh certificates, payment/credit settlement, or independent freight-overcharge judgment was established for the claim. **The $24,457.95 is a noncash transfer, not savings/recovery.**

## What was and was not validated

| Evidence needed | These sources provide | Gaps |
|---|---|---|
| Creditor original invoices | GlobalTranz filed broker invoice attachments with statement | Still no complete original *underlying-carrier* invoices or authorized reusable benchmark |
| Applicable freight rates | Specific tariff/rating **citations in GAO legal decisions** | Full historical controlling tariff tables and contemporary customer-specific contracts |
| Actual paid amounts | Government decisions expressly state paid/collected charges | Independent original payment ledger and bank/offset records for blind reconciliation |
| Error explanation | GAO adjudications give specific classification/routing disputes | Independent linked adjudication with source images and modern customer-rate terms |
| Recovery or credit | GAO expressly records **government deductions** and sustains them | Original offset voucher/cash ledger, separate commercial executed credits |
| RETALLY performance | **None** | No live authorized invoices, frozen independent labels, recall/precision/false-positive measurement |

**Go/no-go:** negative-control claim logic can be tested with synthetic metadata, and historical GAO decision patterns can inform *synthetic-only* historical-offset safeguard tests. Neither proves RETALLY's commercial freight-audit accuracy. The pure function `assess_historical_offset` validates case-reference and exact paid-minus-allowed metadata **without fetching GAO content**; its labels are `SOURCE_REFERENCED_HISTORICAL_OFFSET` or `REVIEW_REQUIRED`, never a RETALLY recovered-dollar credit.

## Zero-cost next evidence targets

1. Identify source-scanned government bills of lading, GSA overcharge notices and original deduction vouchers linked by **the exact BOL/decision references above**, via unrestricted U.S. government archives and free published agency exhibits. Never synthesize missing documents.
2. Search official court exhibits for **original carrier invoice + agreed rate + executed credit or proof of offset** attached together. Track each exhibit's page, filer, date, legal entity, unit of account, and provenance before permitting any calculation.
3. Pursue separate original XPO/R&L carrier claims only as *hypotheses*: require matching legal debtor, identical shipment PRO/BOL, billed identity and payment allocation; do not count two creditors as a duplicate merely because the carrier name occurs on a broker invoice.
4. Assess document rights before retention/import, keep source documents out of repository, and require independent frozen labels and authorized real-world replay prior to any claim of tested RETALLY recovery software.

**Boundaries:** free public access only; no outreach, payments, paid docket access, invented rows, direct customer uploads, production importer, main-branch changes or promotion of historical recoveries to RETALLY results.
