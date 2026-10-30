# RETALLY — complete independent freight-recovery evidence chain
**October 19, 2026. Admission decision: NOT CLOSED; strict real-world freight accuracy/recovery release hold.**

## New high-value primary-source finding: GSA TAMS contains required case-level audit fields

The **United States Government Transportation Audits Management System (TAMS)** is the most promising concentrated source for all major freight evidence categories. This is not a new invented dataset or confirmation that public API access exists.

- [41 CFR 102-118.425](https://www.ecfr.gov/current/title-41/subtitle-C/chapter-102/subchapter-D/part-102-118/section-102-118.425) explicitly requires transportation documents sent to GSA to annotate **original TSP invoice number**, **amount billed**, **agency**, **document reference number**, **date approved for payment**, **amount/date actually paid**, **payment location**, **payment voucher number**, **complete contract/tender/tariff authority with section number**, and a **copy of any statement of difference**. It also includes the carrier SCAC and TIN (sensitive fields that must be removed before any reusable public data product).
- [41 CFR 102-118.305](https://www.ecfr.gov/current/title-41/subtitle-C/chapter-102/subchapter-D/part-102-118/section-102-118.305) specifies comparable paid-record requirements; [GSA's current transportation audit handbook](https://www.gsa.gov/policy-regulations/policy/transportation-management-policy/transportation-handbook-freight-household-goods-and-small-parcel) instructs auditors to use invoices, shipment BOL and original effective tenders, identify overpayments and settle adjustments.
- [41 CFR 102-118.540](https://www.ecfr.gov/current/title-41/subtitle-C/chapter-102/subchapter-D/part-102-118/section-102-118.540) states GSA Transportation Audits has governmentwide data including **carrier rates, paid carrier invoices and billings**.
- A [GSA Notice of Overcharge, Form 7925](https://www.gsa.gov/system/files/2023-10/GSA7925-23.pdf) provides an **example of required overcharge fields, not actual paid/refunded freight evidence**. Do not use a blank form as a positive case.
- **Unresolved:** TAMS is a government business audit system, not demonstrated public-download/open-license corpus; no authorization, redacted case extract, source-byte manifest, independently cleared bank/processor settlement, or deidentified final adjudicated per-invoice labels were retrieved. Regulatory mandates establish what agencies maintain, **not what outsiders may access or commercially reuse**.

**Most effective next acquisition** without inventing records: an authorized *redacted* GSA case-file export, paired by carrier invoice + BOL + DRN, including original carrier bill, effective tender/contract, paid voucher+Treasury settlement identifier, signed statement of difference, final GSA/GAO disposition, and independently cleared refund or offset voucher. Request explicit **scope of reuse** and exclude TIN, bank account details, employee names, customer identifiers and nonpublic tariffs. A governmental release may require a public-record request and license/FOIA exemption review. **No requests submitted and no claimant contact.** The user's prior no-outreach boundary remains in force.

## Near-complete historical original records: adjudicated government vouchers

[GAO March 12, 1924, 3 Comp. Gen. 618](https://www.gao.gov/products/403440) cites an *original carrier bill*, source bill of lading **WQ-A-897831**, **$114** freight charges (19c per 100 pounds on 60,000 pounds), original pay voucher **4746** in May 1921, correct intrastate charge **$20**, and independently ordered/deducted **$94** against carrier bill 6573-B by voucher **2584** in April 1923. The GAO adjudication rejects the carrier's request to reverse the reduction. This provides:
- **high-value historical source-level adjudicated positive offset narrative**;
- specified case shipment, tariff-rate theory, paid voucher and offset voucher number;
- **NOT the original signed/scanned carrier bill, original tariff/rate schedule as in effect, copies of the actual disbursement vouchers, a Treasury clearance/ACH statement, or a commercial grant for the third-party bill**.

The GAO decision is government-authored/public-domain **narrative evidence**. Referenced original carrier documents do not become public-domain commercial training material merely by being mentioned in a public opinion. An offset reported in an adjudicative decision is not independent *bank clearing* and cannot be credited as a RETALLY recovery.

[GAO B-121220 (1964)](https://www.gao.gov/products/b-121220-0) directly explains why governments historically require **receipted freight bills or certified original carrier invoices and repayment vouchers** to prove the government bore the freight charge and could recover overcharges. That guidance reinforces the source-level payment rule, not a completed benchmark.

## New primary-source invoice attachments in FMC litigation — rights, bank and outcome hold

- Federal Maritime Commission Docket **24-01**, *Visual Comfort v. COSCO*. [FMC public original docket](https://www2.fmc.gov/readingroom/proceeding/24-01/) and the [46-page public-version appendix of carrier invoices](https://www2.fmc.gov/readingroom/docs/24-01/%2877%29%2024-01%20Appendix%20for%20Complainant%27s%20Reply%20Brief%20%28PUBLIC%20VERSION%29.pdf/) include real carrier-issued invoice images, linked BOL/container data, invoice charges, rate breakdowns and tariff references. **The reproduced private-party invoices themselves bear CONFIDENTIAL stamps.** The document is publicly served as a "PUBLIC VERSION" of a court exhibit, but **that does not confer permission to repackage the private carriers' invoice image or confidential commercial terms into a commercial training dataset**.
- Separate [FMC Docket 24-01 adjudication index](https://www2.fmc.gov/readingroom/proceeding/24-01/) lists April 28, 2025 initial decision #103 and May 29 notice-not-to-review #104. A separate complainant in [24-09](https://www2.fmc.gov/readingroom/proceeding/24-09/) characterized 24-01 as lacking invoice-specific proof; **do not import any invoice as an adjudicated overcharge merely because it was disputed in a complaint**.
- **Still needed for this candidate:** exact invoice-specific final error label, original governing *effective* service contract/rate (as distinct from invoice's stated rate), independent fully settled bank/PayCargo remittance, executed refund/offset voucher and commercial use permission from applicable rights holders. Those requirements are not met by a stamped invoice or docket's public visibility.
- FMC Docket **2021(I)**, Bridgewell v ZIM [original decision](https://www2.fmc.gov/readingroom/docs/2021%28I%29/%2805%29%202021%28I%29%20Initial%20Decision.pdf/) refers to freight payments through **PayCargo** and a **confidential service contract** but **dismissed the claim and denied reparations**. It is a useful *negative control for paid charge versus proved wrongful charge*, not a successful recovery. An allegation/request for $49,400 is not a refund or RETALLY success. The decision itself says the final outcome was dismissal.
- FMC Docket **2022(I)**, Bridgewell v another carrier [original initial decision](https://www2.fmc.gov/readingroom/docs/2022%28I%29/%2801%29%202022%28I%29%20Initial%20Decision.pdf/), distinguishes specific paid demurrage receipts adequately documenting charges from records missing legally required rate/free-time fields, and separately holds some claimed payments unproved. This supplies **adjudicated true-negative and potential positive labels for legal invoice-completeness**, not a bank-backed confirmed refund; exact final status and reuse rights require review.

**Rights handling:** do not commit privately authored invoice contents, scanned exhibits or third-party payment/contract source bytes to this public repository. Never imply confidential-public exhibits are OGL/CC licensed.

## Independent real-world validation status

| Mandatory independently source-verified component | Best discovered trail | Admission decision |
| --- | --- | --- |
| Original carrier-issued invoice (as issued; specific line) | FMC 24-01 scanned private-party exhibit; GlobalTranz broker claim attachment | **FOUND as public research references, commercial reuse rights UNVERIFIED** |
| Controlling rate/tariff version effective on service date | GAO rate/tariff citation; TAMS regulatory requirement; FMC invoice mentions tariff | **NOT separately source-cleared AND matched** |
| Independent **original payment bank/processor clearing** | GSA/TAMS required actual payment and voucher metadata; FMC PayCargo testimony; Pennine OGL ledger "Fully paid" | **NO original bank clearing documentation linked to one original freight invoice** |
| Independent invoice-specific valid error/overcharge finding | GAO adjudicated voucher offset; several FMC adjudications | **YES as historical narrative for some distinct cases, NOT linked to above complete documents** |
| Independent executed recovery/refund payment/offset clearing | GAO reports historical administrative offset with voucher identifiers | **NO separately obtained original Treasury/bank clearing against the same invoice** |
| All source document reuse rights + provenance digests | Original government decision URLs; separate explicitly licensed Pennine supplier ledger | **NO unified freight-case commercial rights grant** |
| Blind frozen independent labels; direct RETALLY replay and independently audited metrics | Synthetic test harness and research gate only | **NOT PERFORMED on fully cleared real carrier cases** |

## Engineering control implemented (synthetic only)

`freight/research/complete_case_gate.py` and `freight/test_complete_case_gate.py` add 22 deterministic examples verifying that *no case* is admitted for blind replay without distinct source pointers, source hashes, original carrier invoice, effective rate, BOL/POD, original bank settlement, separate adjudication and actual recovery/offset clearing, independent verification, explicit rights, invoice/shipment linkage and blind labels. Even a synthetically complete case returns **READY_FOR_INDEPENDENT_BLIND_REPLAY**, **not** verified RETALLY accuracy or recovered cash. This does not itself fetch/validate source documents.

A future record must also pass privacy, signed-buyer authority, retention, exact-rate calculation, source authenticity and the existing protected-main independent CI/release process; positive observed error labels alone never prove RETALLY found them.

## Immediate zero-spend path to a genuinely complete case

1. **Use TAMS/GSA as the exact target** for an independently redacted complete postpayment transportation audit case set; verify public availability and reuse terms first. Missing source records cannot be substituted with the blank Form 7925.
2. **Use FMC public dockets for source locator metadata only**. A privately authored invoice marked confidential is rights-held even if a judge quotes or a docket posts it. Reject claims unless independently adjudicated with invoice-specific findings.
3. **Preserve negative controls**: GlobalTranz–Artivo $24,457.95 liability-transfer accounting reduction and Bridgewell–ZIM dismissed $49,400 claimed refund are not refunds or recoverable invoices.
4. **Independent replay after authorization:** record per-file content hashes, carrier invoices, rate version, BOL/PRO, bank/processor clearing evidence, final adjudicator decisions, post-recovery bank/offset clearing. Blind-freeze verified labels before running RETALLY; independently measure precision, recall, false positives, expected dollars and actually recovered dollars.
5. Do not contact GSA, carriers, claimants, customers or regulators, spend money, merge an unreviewed PR, or enable a customer financial parser to circumvent the controlled-pilot manual-only environment.

**Hard finding:** A full, rights-cleared, independently bank-settled, adjudicated *same-invoice* freight recovery case has **NOT** been independently obtained. This is a source/access and permission blocker, not an arithmetic defect. No historical third-party recovery belongs to RETALLY.
