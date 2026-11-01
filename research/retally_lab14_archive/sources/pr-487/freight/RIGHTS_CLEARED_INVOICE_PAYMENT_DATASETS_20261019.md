# RETALLY — genuine licensed invoice-to-payment dataset discovery (2026-10-19)

**Result:** Several **actual, publicly published, free, explicitly licensed** invoice-to-payment or invoice-to-disbursement datasets are now identified. At least one (London Borough of Barnet) reports individual original supplier invoice references, gross values, and **actual finance payment dates**, under the UK Open Government Licence v3. This **closes the rights/availability gap for testing invoice-to-payment ledger reconciliation**, **not** the harder end-to-end original-carrier-invoice + rate-contract + source-bank-credit + independently adjudicated freight-overcharge validation gap.

All external financial source rows remain at publisher URLs; no invoice rows, original PDF/images, contact data, restricted/third-party exhibit files or buyer records are committed to this branch. The findings are **publisher metadata and descriptions**, not an independently executed bulk record import or ETL replay. Do not claim source rows were benchmarked by RETALLY or any customer amount recovered.

## Ranked usable datasets

### A. Barnet Council — original-reference invoice -> actual payment ledger (highest quality direct match)

**Publisher:** London Borough of Barnet, original https://open.barnet.gov.uk/dataset/financial-invoices-late-payments-2g58n

**License:** **UK Open Government Licence v3** displayed explicitly on *original publisher page* (the downstream data.gov.uk catalog currently says "No Licence Provided"; use publisher-specific primary license evidence while noting metadata conflict). License terms: https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/ ; attribution required, third-party rights excluded as usual.

**Actual records:** supplier, supplier postal address, invoice date, **supplier invoice reference**, **gross invoice amount**, scheduled due date, clearance date and **actual finance payment date**. Downloadable XLSX periods 2023-24, Apr 2024–May 2025, Jun–Nov 2025, and Dec 2025–May 2026. **This is real issuer-described invoice-to-payment ledger evidence** (for **late invoices**, not a population-wide or random cross-section). Strictly read record source fields and date/amount conformance before declaring an individual row complete. Avoid unnecessarily ingesting supplier addresses.

**Allowed claim:** free, OGL-licensed real invoice-reference/amount-to-paid-date **process reconciliation benchmark**. **Not** an original invoice image, freight contract, proof money arrived in recipient's bank, or evidence a freight overcharge was corrected.

**Concrete no-cost acquisition:** download one published XLSX directly from the original publisher portal. Retain attribution and version; select fields {supplier, invoice_ref, invoice_date, gross_amount, actual_payment_date, cleared_date}. Validate that refs and amounts/date are present, reject duplicate composite IDs and unknown currencies, then freeze a source-hash-linked subset separate from the source. Do not use result rows in a public repository.

### B. Angus Council — invoice **and credit notes** with paid dates (best adjustment trail)

**Publisher:** Angus Council Open Data, official dataset https://opendata.angus.gov.uk/dataset/invoice-and-credit-notes-over-f500 ; example original resource https://opendata.angus.gov.uk/dataset/invoice-and-credit-notes-over-f500/resource/ba7346ac-15a9-42f0-ab44-778189efb5f4

**License:** resource metadata explicitly declares **UK Open Government Licence (OGL)** (source metadata is first-party).
**Original source columns:** `Supplier Name`, `SUPP_OWN_REF`, `Payment Date`, `Gross Amount`, `VAT Amount`; invoice and credit notes **above £500**. Published semiannually. The resource metadata itself warns that **the online datastore does not contain all rows of the source XLSX** — use publisher full downloadable XLSX rather than treating API preview as complete.

**Allowed claim:** licensed real supplier-reference + gross amount + payment-date **ledger examples**, plus credit-note/correction events. **Not** invoice/credit pairing without shared authoritative IDs, proof of bank clearance, adjudicated credit amount, verified carrier tariff, or confirmed refund. Values below £500 are absent by design.

### C. USAC E-Rate — requested invoice lines vs decisions and authorized disbursements

**Publisher:** Universal Service Administrative Company, official https://opendata.usac.org/E-Rate/E-Rate-Invoices-and-Authorized-Disbursements-FCC-F/jpiu-tj8h (view ID `jpiu-tj8h`).

**License:** **Public Domain** explicitly declared on the original dataset page.
**Scale at inspection:** approximately **3.42 million invoice-level lines**, 37 columns, updated October 15, 2026; invoice ID, invoice line ID, total invoice amount requested, total requested invoice line amount, total approved line amount, invoice and approval dates, and reimbursement decision codes/explanations (especially useful for *real authoritative reductions*). First-party data glossary: https://opendata.usac.org/api/views/jpiu-tj8h/files/a0c7521c-bcd0-4de5-8b9c-482cea24432e?download=true&filename=E-rate+Invoices+and+Authorized+Disbursements+%28FCC+Form+472_474%29+Data+Glossary.pdf

**Critical distinction from glossary:** approved line amount is **authorized to be paid**, and line completion precedes receipt into recipient bank by several business days. Thus **authorized disbursement is not confirmed bank settlement**. Do not treat every requested-versus-approved delta as an overcharge: denials, eligibility, program discounts and reductions have distinct legal/business meanings.

**Allowed claim:** explicitly rights-cleared real invoice-to-**authorized**-payment and official reduction-reason benchmark for commercial-quality matching/exception tests. Nonfreight telecom and school procurement, not an LTL carrier bill/rate or proof that funds arrived.

### D. BPI Challenge 2019 — large-scale genuine purchase-to-pay event chain

**Publisher:** Eindhoven University of Technology / 4TU.ResearchData, https://figshare.com/articles/dataset/BPI_Challenge_2019/12715853
**License:** **CC BY 4.0**, explicitly on publisher record; attribution required.
**Scale:** 251,734 purchasing items, 1,595,923 events; real multinational procurement with PO, goods receipt, invoice-receipt and `Clear Invoice` events, including logistical service spend.

**Critical limits:** company identity and monetary amounts were anonymized/linearly transformed by publisher, amounts are **not literal paid currency**, `Clear Invoice` is an ERP clearing event (not third-party bank proof), and multiple receipts or invoices can correspond to one item. No original carrier invoice images, contemporaneous effective freight contracts, or independent overcharge labels. A conference-published analysis reports road logistics nonconformances but these are **not adjudicated freight overcharges**.

**Allowed claim:** license-clean scale/stress tests of P2P matching, split shipments, duplicate detection, sequence integrity and match-error triage. No validated freight recovery dollars.

### E. Los Angeles city ledger joins — publicly licensed metadata, missing original amounts in direct-ID table

**Publisher:** Los Angeles Open Data Portal, https://data.lacity.org/A-Well-Run-City/Invoices-and-Purchase-Orders-for-City-Goods-and-Su/5ru3-n8sy/about
**License:** **Public Domain** shown by publisher.
**Data columns:** `VENDOR_ID`, `PO_ID`, `INVOICE_ID`, `CHECK_NO`, `RECEIPT_DATE`, `INVOICE_DATE`, `PAYMENT_DATE`. Historic through May 2014.
**Missing:** source invoice **amount**, original invoice document, carrier rate. Do not join a disjoint later LA expenditures dataset without independently verified shared IDs and period coverage. This is an identity+check date control, not complete full-dollar case.

### F. Cook County check register — exact freight payer/invoice/payment identifiers, **reuse-rights hold**

**Publisher:** Cook County Open Data, https://datacatalog.cookcountyil.gov/Finance-Operations/Cook-County-Check-Register/4h27-5s9x
**Scale:** ~435,000 payment/check records (public portal, updated Oct 6, 2026), with `check_number`, `check_date`, `vendor_number`, `vendor_name`, `check_amount`, `invoices_paid`. The publisher's public data view contains distinct **UPS FREIGHT** and **UPS SUPPLY CHAIN SOLUTIONS** payment rows with original invoice references, paid check amounts, payee identity, and June 30, 2026 check issue dates; these are **real freight-sector invoice-to-check-issuance leads**, not hypothetical freight transactions.

**Rights:** original check-register page does **not** show an explicit item-specific license in accessible metadata. Cook County's Open Data policy aspires to license-free publication, but its general Terms of Use warns against republishing copyrighted images/third-party material. Consequently, mark **commercial reuse of whole records not independently cleared** pending primary item-specific license/terms verification. Public reference/use for research and factual citation is different from bulk commercial redistribution.

**Financial limit:** check **issuance** is not independently established bank clearance; one check can pay **multiple invoices**, so do not assign its entire amount to each invoice. No carrier invoice image, NMFC/classification proof, contract tariff, BOL, carrier reweigh certificate, or adjudicated overcharge labels found.

## Freight claim adjudication — relevant but not a reusable invoice file

Federal Maritime Commission official proceeding **24-13**, *Access One Transport v COSCO*, https://www2.fmc.gov/readingroom/proceeding/24-13/ , contains a publicly adjudicated detention invoice/payment/cancellation analysis and final monetary reparations **order**. The government-authored decision provides legal case evidence. It **does not** confer a data-use license on separately authored confidential private-party invoices, and an award does **not** prove COSCO actually remitted a post-order payment. Treat as **historical case-level positive/negative controls**, not original invoice-image source nor RETALLY client result.

## Admission decision / remaining gap

| Purpose | Cleared available evidence | Can declare ready? |
| --- | --- | --- |
| Real-world invoice reference, amount and actual paid-date reconciliation | Barnet OGL v3 (subject to source row checks) | **Dataset identified; raw row import/replay not executed** |
| Real-world invoice plus credit-note/payment-date correction ledger | Angus OGL (full XLSX; partial online datastore warning) | **Dataset identified; raw row import/replay not executed** |
| Requested invoice vs authoritative reduction code/approved disbursement | USAC public domain | **Dataset identified; authorized is not settled** |
| Real P2P high-volume events + logistics classification | BPI Challenge CC BY 4.0 | **Dataset identified; no literal amounts/bank settlement** |
| Real freight payee + invoice reference + check issue | Cook County | **Rights hold + original invoices/rates missing** |
| **Full freight invoice -> effective contract/rate -> shipment -> independently classified error -> executed credit/bank receipt** | **None found complete, rights-cleared, and independently joined** | **NO** |
| RETALLY commercial recovery accuracy / recovered dollars | No customer-authorized blind replay | **NO** |

Next feasible free step: take a **publisher-hosted complete Barnet XLSX** or Angus XLSX into a nonpublic, temporary evaluation environment, source-hash it, strip names/addresses except stable local surrogate, validate invoice references and paid dates, reconcile actual rows while preserving invoice-to-check/payment many-to-one and credits. For actual freight valuation, pursue separately authorized original carrier invoices/rate authority and bank/credit evidence; never synthesize missing originals or infer monetary success from external organizations.

**Safety:** no spending, outreach, original third-party PDFs, direct financial records, commercial promotion, paid subscriptions, live customer data, or protected-main changes occurred in this dataset discovery.
