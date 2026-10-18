# RETALLY Lab 14 — Original Crowley/GSA Court and Payment Lineage
**18 October 2026 · Original U.S. federal court + GSA budget source research · DRAFT · no customer authority**

## Why the same $29.6 million must not be counted twice

Three **first-party** publications describe different stages of an actual historical federal transportation-auditing dispute. They are not RETALLY's customer invoices, carrier credit memos, vendor bank statements or income.

| Source / original primary document | Exactly documented evidence state | Treatment |
|---|---|---|
| [2023 U.S. District Court memorandum opinion (govinfo, Docket 21-cv-02298, document 79), PDF page 17](https://www.govinfo.gov/content/pkg/USCOURTS-dcd-1_21-cv-02298/pdf/USCOURTS-dcd-1_21-cv-02298-2.pdf) | Quotes GSA's April 21, 2023 **promise** to refund approximately **$29.6 million** previously withheld under Crowley DFTS I audits | **Promise in 2023 letter, not an independent cash receipt.** |
| [GSA FY2025 Congressional Justification, Transportation Audits, printed P-2/P-5](https://www.gsa.gov/system/files/GSA%20FY%202025%20Congressional%20Justification.pdf) | GSA reports making **$29.6 million payment** to a DoD transportation vendor in **fiscal 2023** to correct notices of overcharge subsequently found erroneous; approximately **$20.7 million** from receipts and **$8.9 million** from suspense | **Official publisher statement of FY2023 payment made**, no bank/Treasury payment posting independently inspected. It refers to the **same underlying DFTS repayment as the earlier promise**, not a second $29.6M. |
| [2025 D.C. Circuit Court of Appeals (No. 23-5183), July 18, 2025](https://media.cadc.uscourts.gov/opinions/docs/2025/07/23-5183-2126136.pdf) | Reversed the lower court on **§ 3726(b) GSA audit authority over Crowley's non-carrier bills**, remanded; separately describes Crowley's **$11.8 million damages claim in the Court of Federal Claims** | **No dollar damages were awarded in this appeal**, and no payment/satisfaction of the parallel claim was adjudicated here. Do not claim an October 2026 docket disposition without fresh original source. |

The 2023 district court also quotes GSA's April 21 letter **promising $35,840.43** in a refund on a **distinct Ocean USC 9 contract**. The source does *not* independently verify that Ocean-specific promise was paid. It is not silently added to the DFTS $29.6 million payment or called a RETALLY recovery.

**Critical duplicate guard:** The $29.6 million appears as an earlier **2023 promise** and a later **publisher-reported FY2023 payment**. Summing them to $59.2 million is false; mixing the separate $35,840.43 promise or $11.8 million parallel damages claim into a received-cash figure is also false.

## Legal and contract authority

The 2025 D.C. Circuit majority interpreted **31 U.S.C. § 3726(b)** as limiting GSA's audit authority to bills presented by carriers/freight forwarders. It determined **Crowley**, acting as a freight coordination intermediary for the DFTS contract, was neither within that meaning. It reversed the particular lower court's broader audit-scope interpretation and remanded. A dissent disagreed on mootness.

This is **case-specific U.S. government statutory authority**, not a judicial grant empowering a private freight-recovery business to seize carrier balances, automatically challenge customers' bills, contact carriers without consent, or recover funds. RETALLY still requires legitimate customer authorization, the current executed carrier agreement, correct party and shipment classification, original invoice/tariff, shipment/proof-of-service records, and independent legal/financial review.

The appellate opinion discusses a separate Court of Federal Claims matter (No. 21-1405), which sought **$11.8 million** in damages. The opinion did not award that sum, so the original-source custody level is **LITIGATED_MONEY_CLAIM_PENDING_AS_OF_2025_OPINION**. Later case outcomes and current 2026 docket events were not completely independently checked; status after that observation remains **UNKNOWN**, not conclusively unpaid or satisfied.

## Source custody and testing

Original publisher URLs and exact docket, distinct contract scope, document dates, money amounts in cents and two-stage payment identity are recorded in `freight/fixtures/public_federal_crowley_gsa_2023_2025_original_court_timeline.json`. Validator `freight/public_crowley_court_money_lineage_v1.py` and negative tests enforce:
- Three exact original federal sources and four exact dated source events with explicit event types and nonclaims.
- One DFTS 2023 promise + one FY2023 publisher-reported payment are **not duplicate independent receipts**; the reported money is approximately $29.6M, not an independently verified bank amount to the cent.
- A *different* Ocean USC 9 refund is **only promised** for $35,840.43; the $11.8M parallel claim is **not** an appellate award.
- An appeal on audit jurisdiction grants **no private carrier-offset authority**, and a legal holding is not a carrier/customer refund.
- Original PDFs were read as authoritative publisher text but were **not independently downloaded and hashed in full**, and no original remittance, invoice, claims-court final 2026 docket or actual RETALLY recovery was authenticated.
- Changes to source domain, money state, amounts, court holding, source-publisher date or unrelated customer invoices **fail closed**.

Command: `PYTHONPATH=. python -m unittest -v freight.test_public_crowley_court_money_lineage_v1`.

Research receipt intentionally does not add these case events to the **307 separate** original freight records and observations, the **7 earlier GAO decisions**, **one FMC order**, **one original Census statistical example**, **one GSA FY2023 reported correction payment**, or **two separate SEC-filed historical rate contracts**. The source-report categories are different and **not directly additive in money**.

**Production/commercial NO-GO:** No user or customer invoices, contract authority, independently verified RETALLY recoveries or bank deposits. Original 26 historical findings OPEN_UNVERIFIED, 18 human first-customer gates unmet. All changes stay in a stacked, unmerged source-only research draft with no new paid service, schedule, carrier outreach, protected-main release or live customer-intake change.
