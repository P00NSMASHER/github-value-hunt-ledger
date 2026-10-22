# RETALLY — Sungold original trial-exhibit retrieval and final bank-settlement check

**October 19, 2026, Eastern. Decision: NO ORIGINAL PUBLIC EXHIBIT FILES OR SETTLED CUSTOMER REFUND OBTAINED.** No organization or person contacted. No emails, FOIA/court requests, CAPTCHA bypass, accounts logged into, payment, public bank-record upload, or authorized-customer impersonation.

## Verified case identity and trial evidence IDs

**Case**: Sungold Trade Pvt Ltd v Chevisance Shipping Pvt Ltd, CS (Comm) 32/2026, Delhi District West Commercial Court 04, CNR **DLWT-01-014066-2025**. **Original bill of lading AMC1912992**. Court judgment Sept 17, 2026 is readable at https://indiankanoon.org/doc/161666818/; independent court filing index at https://delhidistrictcourts.nic.in/viewdocuments/RWUxTjEvVmN0TXJPNHhDamVuSmRvVWRsR3F2NWVIcHpqcnFGQU4vdDNNMWx6c1BLend5ajlZVmJtTi84dEwvK0VET2ZTNkE0QXczWHBFTkd0L2NURmg3SnJldFg0T21SNHc5T0RScHNvWFVjdWJMdXlZTEQvaGVIMHMxcWdPaFVZUTJUQ3A0cFNsT3FYR2JYYTZidlB3PT0_EQUALS_ confirms original case registration.

Exact exhibits admitted at trial according to the judicial opinion (not original exhibits downloaded):
- **Ex.PW2/1** carrier's Aug 30 2022 3-page booking confirmation; booking party Chevisance, shipper Sungold.
- **Ex.PW2/2 / Ex.PW1/9** carrier's Oct 10 2022 3-page equipment DETENTION tax invoice, **INR 689,695.85**.
- **Ex.PW2/3 / Ex.PW1/17** carrier's Dec 8 2022 3-page export credit note **INEMH841112, INR 619,339.26** issued to *Chevisance*.
- **Ex.PW1/12** original ICICI bank statement admitted to show payer Sungold originally paid detention to Chevisance.

The publicly readable **court judgment is not itself the four original admitted financial/shipment exhibits**. The court adjudicated Chevisance's duty to pass on the carrier credit, not that it actually repaid Sungold or that the original carrier price violated its applicable daily detention tariff.

## New genuine read-only source-page inspection (October 19)

[Independent public case-page probe, GitHub Actions 39345433077](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39345433077) ran only a bounded HTTPS GET to the *exact* publicly readable Indian Kanoon case URL and inspected its original **88,658-byte HTML** in memory (SHA-256 `2e21f3ccfee7236f3536e36e0ebe499fe97f74c67e2e6332147132835386b62a`).

The page contains interactive controls **"Get in PDF," "Print it!," "Download Court Copy"** and several GET/POST HTML forms. The only relevant *actual anchor HREFs* captured after safe host filtering linked to the publisher's Prism analysis pages `/prism/` and `/prism/case-recast/161666818/`. **No direct, publicly linked Ex.PW1/12, Ex.PW2/1, Ex.PW2/2 or Ex.PW2/3 PDF was present.** Neither a "Download Court Copy" button nor a POST form is a permission-free attached trial exhibit. No form submission or paid/premium action was attempted; the source page's HTML was discarded after inspection.

[Source reproducer](../research/sungold_court_link_probe.py) and [seven offline safety tests](../test_sungold_court_link_probe.py) preserve this result without ever logging the parties' private details or downloading bank statements. The CI job passed; a green CI result does **not** imply a recovered court exhibit.

## Independent final settled customer refund: still not substantiated

- The September 17 judgment awarded **INR 619,339.26** principal plus simple 9% annual interest from Dec 30, 2025 through realization. It found a carrier credit to **Chevisance**, not a bank payment to **Sungold**.
- [Third-party corporate litigation index](https://www.thecompanycheck.com/company/sungold-trade-private-limited/U51109DL2009PTC195240) reports its **one indexed district court commercial suit "disposed" as of Oct 3 2026**. *Disposed* is the normal post-judgment case status, **not** execution of the judgment, debtor payment or customer bank receipt. The index does not independently prove an execution petition never existed and may omit later actions.
- Exact public searches for **CNR**, both company names, **Ex.PW2/2 / Ex.PW2/3**, **AMC1912992**, **INEMH841112**, post-judgment "execution," "satisfaction," and "bank/NEFT payment" found **no separately source-verifiable transaction** carrying the customer as beneficiary.
- A final remittance might be privately recorded, later filed, delayed, appealed or not paid; this report **does not claim the customer never got paid**. It only establishes that a settlement is **not presently independently verified**.

## Practical access boundary — no fake retrieval

The original trial exhibit PDFs, bank account statements and any later beneficiary-bank settlement are **not in the public judgment HTML**, original publicly indexed court e-filing list, or referenced public URLs. The central eCourts case-status portal has an interactive CAPTCHA and party-specific record access may be required for case attachments or certified file copies. User's authorization to **download** permits direct retrieval of available original documents; it does not produce missing URLs or authorize circumvention, third-party bank logins, user impersonation, outreach or court filing. All those remain prohibited under the user's standing instructions.

**Public court-app cross-check:** [Official eCourts Services FAQ](https://services.ecourts.gov.in/App/appfaq.html) says public users can check case status free of charge without registration, and can download available **court orders/judgments**. It does **not** promise public access to bank statements or admitted *trial exhibit copies*. [Official eCourts web case search](https://services.ecourts.gov.in/ecourtindia_v6/) requires a CAPTCHA; no automated CAPTCHA interaction attempted. [Delhi District Courts e-filing guidance](https://delhicourts.nic.in/efiling) says lawyers register by matching a filed Vakalatnama; no impersonation, access request, or third-party client data access was attempted. A free court case lookup and a certified exhibit-file acquisition are distinct capabilities.

**Exact documentary closure inputs (not obtained):** four original court exhibits above with source-byte SHA-256/issuer verification, verified shipment-specific CMA CGM export DETENTION tariff/equipment/free-time amendment mapping, independent proof of a cleared Chevisance→Sungold transfer or actual applied credit after judgment. An intermediary's issued credit and a court's final award are **not** the customer's bank-cleared recovery.

**Admission state remains `RESEARCH_HOLD`; verified RETALLY cash recoveries `0`; no commercial accuracy claim.** No original financial source document has been uploaded or published in GitHub.
