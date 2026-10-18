# RETALLY — GlobalTranz public invoice reconciliation research

## RESOLVED: court-ordered liability transfer, not cash recovery (2026-10-18)

**The exact $24,457.95 claim discrepancy is explained in the signed bankruptcy court order.** [Docket #623, May 29, 2026, PDF page 7](https://document.epiq11.com/document/getdocumentsbydocket/?docketId=1227468&projectCode=MCX&docketNumber=623&source=DM) names **GlobalTranz Enterprises, LLC**, legal debtor **Walker & Zanger, LLC**, proof of claim **10002**, originally **$25,954.47**, modified **$1,496.52**. The operative explanation states that **$24,457.95 of the claim was transferred to Artivo in connection with the sale of Walker & Zanger**. [Docket #593, March 20, 2026, PDF page 27](https://document.epiq11.com/document/getdocumentsbydocket/?docketId=1216147&projectCode=MCX&docketNumber=593&source=DM) independently documents the same claim-specific schedule and explanation (same bankruptcy proceeding, not independent commercial payment evidence).

**Arithmetic:** $25,954.47 original claim − $24,457.95 transferred liability = **$1,496.52 retained claim**, unexplained face-value difference **$0.00**. The court records explain liability allocation after an asset sale, **not an invalid freight invoice, customer credit, cash refund, actual settlement, or RETALLY-generated recovery**. Do not use the transferred amount as a recovered-dollar example or freight billing accuracy label. No private or paid docket access was needed. Original PDF bytes remain outside this repository.

**Research only. No customer data imported, commercial reuse license inferred, overcharge adjudicated, settlement confirmed, or recovery established.**

## Traceable public sources

- [Original GlobalTranz proof of claim and invoice/statement attachments](https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/10247), claim 10002, July 2025. Filed amount: **$25,954.47**.
- [Alphabetical claims register, July 28, 2026](https://document.epiq11.com/document/getdocumentbycode?docId=4596108&projectCode=MCX&source=DM), shows claim 10002 at **$1,496.52**.
- [Numerical view of same claims register](https://document.epiq11.com/document/getdocumentbycode?docId=4596109&projectCode=MCX&source=DM), confirms the register value but is **not independent verification** of a payment or adjudication.

The **$24,457.95** difference is now **fully explained by the court's liability-transfer schedule** (see RESOLVED section). Nothing in the court record establishes that this transfer was a freight overcharge, refund, cash payment, or customer recovery.

Additional public case lead: [court-filed June 2026 certificate of service](https://document.epiq11.com/document/getdocumentbycode?docId=4581915&projectCode=MCX&source=DM) identifies the May 29 **Docket 623**, a sustained second omnibus claims objection concerning no-liability, reduced-amount, and reclassified claims. **Update: the signed order's page 7 specifically includes GlobalTranz claim 10002**, attributing the reduction to a $24,457.95 transfer to Artivo—not to a freight correction or cash payment. Further inquiry is needed only for actual payment/credit proof, not to explain this face-value reduction.

The public filing's statement pages (PDF pages 115–117, one-indexed) report **102 account-statement entries**. A second analyst-side integer/decimal recalculation of the 46+46+10 indexed amount rows, including two joined page-break lines, reproduced original charges of **$26,026.61** and open balances of **$25,954.47**, exactly matching the filed claim. The sole $72.14 face-to-open change needs a credit/payment/adjustment trail. These 102 source rows have **not** been ingested or independently replayed by the RETALLY comparator, and this text-extraction check is not a full page-image verification. Do not publish underlying third-party invoice rows to GitHub.

Two adjustment pairs can be traced beyond suffix matching to matching **PRO and customer BOL** identifiers in the public pages: an XPO $861.09 original plus $56.44 reweigh adjustment, and an ABF $1,718.04 original plus $29.88 reweigh adjustment. These are valid document cross-references, not evidence of incorrect charges or independent carrier weight certificates. A third adjustment lacks its base within the indexed statement. Counting invoice pages as separate shipments is unsafe. These are **broker-issued invoices**, not verified originals from every underlying carrier.

## Research-only comparator

The new module freight/research/statement_reconciliation.py accepts only caller-supplied structured metadata. It checks invoice face vs statement original, statement totals, canonical duplicate references, explicit base/adjustment linkage **requiring matching PRO and BOL identifiers**, unknown parents, changed open balances and contradictory external claim snapshots. It never derives recovered cash, an overcharge, source reuse rights, or shipment-family counts. The optional `assess_claim_liability_transfer` safeguard checks matching claim identity, original-minus-transfer arithmetic, receiving-entity identification, and a referenced official public court-order URL. **A URL check is not automated verification of court-document contents.** Its output labels the result as a **source-referenced liability transfer**, explicitly assigns **zero verified recovered cash and zero verified overcharge**, and requires review if its constraints fail.

Run the 31 deterministic **synthetic-only** tests:

    python -m unittest freight.test_globaltranz_reconciliation -v

Existing repository-wide Freight and release CI must run on the PR and all normal branch-protection gates remain intact. This is not a production invoice importer, raw PDF extraction path, or licensed external benchmark.

## Research and release holds

- Verify actual source records and all invoice/statement line counts by independently inspecting the complete public document in a rights-compliant environment.
- **Closed:** original objection Docket 593 and signed order Docket 623 explain the exact $24,457.95 reduction as a liability transfer to Artivo; do not seek a payment explanation for that amount as if it were cash recovery.
- Confirm buyer/document authority before processing original third-party documents commercially; public availability alone is insufficient.
- For a freight error: separately obtain controlling effective rate terms, underlying carrier invoice, BOL/PRO, independent classification/weight evidence, prior auditor results and payment/credit proof.
- Maintain independent adjudication and blind frozen validation; apply existing release and customer-data security controls.
- No customer outreach, payments, private-data extraction, new scheduled actions or changes to protected main were made.

## Claim-specific litigation trail (verified public court evidence; 2026-10-18)

**Follow-up now resolved:** The signed order and original objection contain the exact claim-specific dollar disposition (see RESOLVED section). This remains **no evidence of freight overbilling or payment**.

- **March 20, 2026 — Docket 593:** Trust filed a *second omnibus substantive objection* covering no-liability, reduced-amount and reclassified claims. [March 30 service certificate, Docket 595](https://document.epiq11.com/document/getdocumentbycode?docId=4566977&projectCode=MCX&source=DM) includes **GlobalTranz Enterprises LLC on the dedicated second-objection service lists**.
- **May 28, 2026 — Docket 619:** Certification of counsel regarding the second omnibus objection; documented in the [Epiq Docket 625 certificate](https://document.epiq11.com/document/getdocumentbycode?docId=4581183&projectCode=MCX&source=DM).
- **May 29, 2026 — Docket 623:** Court sustained the second omnibus substantive objection, as verified by its [June 3 Docket 626 certificate of service](https://document.epiq11.com/document/getdocumentbycode?docId=4581915&projectCode=MCX&source=DM). Docket 626 explicitly says **Exhibit C and Exhibit F received only the second omnibus order**. GlobalTranz is listed on Exhibit C (PDF page 9) and Exhibit F (PDF page 16), strongly tying it to the sustained objection. The attached signed order's PDF page 7 **does** identify the exact claim-specific reduction, revised amount and Artivo transfer explanation.
- **July 28, 2026:** Public [numerical claims register](https://document.epiq11.com/document/getdocumentbycode?docId=4596109&projectCode=MCX&source=DM) identifies GlobalTranz proof of claim **10002** as **$1,496.52 unsecured** with the original July 17, 2025 filing date and no explanatory comment.

**Claim-disposition documents recovered:** Docket 593 (PDF page 27) and signed Docket 623 (PDF page 7) both name proof of claim 10002 and a $24,457.95 Artivo liability transfer. This **closes the claim-value discrepancy**. Still missing: creditor-specific bank/settlement records (if a cash-payment claim is to be made), applicable rate authority, and independently adjudicated freight errors. The transfer itself must never be promoted into cash recovered.

The missing schedules were recovered by read-only Epiq public docket navigation using a temporary zero-spend GitHub Actions diagnostic on an isolated research PR. The runner accessed the official public PDFs transiently, without persisting source documents in the repository. The actual court explanation is a **liability transfer to Artivo**, not a candidate freight recovery. No paid PACER access, private files, outreach, or permanent scheduled workflow was used.

## Procedural cross-check: revised objection and withdrawn freight claim

[May 28, 2026 hearing agenda, Docket 617](https://document.epiq11.com/document/getdocumentbycode?docId=4580551&projectCode=MCX&source=DM), pages 3–4, confirms that Docket 605 (April 29) **partially withdrew and re-noticed** the substantive second omnibus objection before the court's May 29 order. Four responses appear: GalaxyDecor #10025 and Uline #1 were excluded pending resolution; LVG Ceramic #10166 acknowledged that its commercial relationship was fully satisfied; **Total Quality Logistics #10192** was **withdrawn from objection**. GlobalTranz #10002 is **not named among these four agenda responses**; omission is not proof it made no other response or that it was included in any specific schedule. The signed Docket 623 schedule now establishes the GlobalTranz claim's precise reduction and the Artivo liability-transfer explanation.

[June 3, 2026 order-service certificate, Docket 626](https://document.epiq11.com/document/getdocumentbycode?docId=4581915&projectCode=MCX&source=DM), page 2 says **Exhibit C and Exhibit F received only the second omnibus order (Docket 623)**, and GlobalTranz is included in both (PDF pages 9 and 16). This is direct evidence of *service of the order*, **not** a claim-amount ruling or cash receipt. The signed Docket 623 PDF was subsequently retrieved and confirms GlobalTranz on PDF page 7, including the exact reduction and transfer explanation.

**No promotion:** The $24,457.95 reduction now has a **court-documented noncash liability-transfer explanation**. Do not attribute it to RETALLY savings, freight-rating error, carrier concession, payment, or bank settlement.

## Original invoice chronology and post-confirmation financial reporting

- The [GlobalTranz proof-of-claim statement](https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/10247) lists **102 statement entries dated November 8, 2024 through July 7, 2025** (PDF pages 115–117, one-indexed). The petition was filed **July 8, 2025**. Thus, treating the $24,457.95 reduction as an automatic exclusion of *postpetition statement entries* is not supported by the actual list. Invoice dates alone do not settle whether particular shipping services or accounting obligations have a different priority.
- [Docket 637, filed June 24, 2026](https://document.epiq11.com/document/getdocumentsbydocket/?docketId=1231443&docketNumber=637&projectCode=MCX&source=DM), W & Z Oldco/Walker & Zanger post-confirmation quarterly report **as of March 31, 2026**, reports **$0 cumulative total cash and noncash transfers** (PDF page 2), and **$0 distributions to general unsecured claimants** (PDF page 7). These totals are *debtor-reported* and do not establish that the GlobalTranz creditor was or was not separately paid outside the reported estate distribution path, nor do they cover later periods.
- The docket records [Docket 657, filed August 31, 2026](https://www.inforuptcy.com/browse-filings/delaware-bankruptcy-court/1%3A25-bk-11296/bankruptcy-case-mosaic-companies-llc), a **quarter ending June 30, 2026 post-confirmation report for Walker & Zanger**, but underlying financial tables have not been retrieved and cannot be presumed to be zero.

**Claim-specific order exhibits obtained**, supporting the exact amount and reason. Proof still required for **separate** cash/payment/recovery allegations: actual creditor/estate payment/credit events; for freight-error benchmarks: effective contract/rates, underlying carrier source, shipment evidence, independent truth. No claim-to-cash attribution or freight overcharge promotion.

## Same-debtor independent carrier claims — potential cross-payee duplicate exposure (2026-10-18)

The [July 28, 2026 numerical claims register, Docket 648](https://document.epiq11.com/document/getdocumentbycode?docId=4596109&projectCode=MCX&source=DM) separately lists:

- **GlobalTranz Enterprises, LLC**, claim **10002**, Walker & Zanger, LLC: **$1,496.52** registered unsecured amount, with no explanatory comment.
- **XPO Logistics Freight, Inc.**, claim **10005**, Walker & Zanger, LLC: **$2,762.66** unsecured (same debtor).
- **R&L Carriers, Inc.**, claim **10053**, Walker & Zanger, LLC: **$11,932.47** unsecured (same debtor). Distinct R&L claim **10054** relates to *Surfaces Southeast, LLC*; **do not group different legal debtors**.
- **Southeastern Freight Lines** claims **10037/10049** relate to Mosaic Companies/Surfaces Southeast Holdco, not the same Walker & Zanger legal debtor, and #10049 amends #10037. Again, do not count as overlaps with 10002 without authoritative debtor and shipment links.

Some publicly cited GlobalTranz broker invoices name XPO or R&L as underlying carriers. This provides a worthwhile **two-creditor / one-shipment hypothesis** for a future authorized invoice identity test: compare carrier-originated proof-of-claim invoices against the broker's billed invoice, original PRO/BOL/customer entity, service date, and payment allocation. **The register alone proves no invoice overlap, duplicate debt, erroneous claim, recovery, or freight billing mistake.** No XPO/R&L original claim attachments were fetched or reproduced.

As of March 31, 2026, [W & Z Oldco's own post-confirmation report, Docket 637](https://document.epiq11.com/document/getdocumentsbydocket/?docketId=1231443&docketNumber=637&projectCode=MCX&source=DM) reports **$0 in general unsecured distributions**, but the filing also notes the effective-date transfer of valid claims and assets to the separate liquidating trust. Therefore this **does not exclude independent trust-level or later creditor payments**. The creditor-specific disbursement record remains unavailable.

## Claim-identity comparison gate (2026-10-18)

The research comparator now requires each optional external claim snapshot to carry a **legal debtor reference, creditor reference, and claim identifier**. It normalizes case/whitespace only for these keys and compares monetary claim snapshots **only when all three keys agree across sources**. Missing or differing identities yield `CLAIM_IDENTITY_UNVERIFIED` / `CROSS_CLAIM_COMPARISON_BLOCKED`, **not** a supposed recovery or discrepancy.

Five new synthetic negative/positive regression tests cover cross-debtor, cross-creditor, different claim numbers, missing identifiers, and consistent normalized identifiers. This is a research safeguard, not a determination that any XPO/R&L and GlobalTranz invoice represents the same shipment or liability. A valid identity comparison alone does not prove the underlying rate, credit or payment. Normal PR gates must pass before any promotion.
