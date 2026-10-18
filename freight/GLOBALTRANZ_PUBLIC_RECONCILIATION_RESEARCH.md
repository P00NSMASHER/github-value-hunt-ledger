# RETALLY — GlobalTranz public invoice reconciliation research

**Research only. No customer data imported, commercial reuse license inferred, overcharge adjudicated, settlement confirmed, or recovery established.**

## Traceable public sources

- [Original GlobalTranz proof of claim and invoice/statement attachments](https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/10247), claim 10002, July 2025. Filed amount: **$25,954.47**.
- [Alphabetical claims register, July 28, 2026](https://document.epiq11.com/document/getdocumentbycode?docId=4596108&projectCode=MCX&source=DM), shows claim 10002 at **$1,496.52**.
- [Numerical view of same claims register](https://document.epiq11.com/document/getdocumentbycode?docId=4596109&projectCode=MCX&source=DM), confirms the register value but is **not independent verification** of a payment or adjudication.

The **$24,457.95** difference between the filed claim and later register remains unexplained. Nothing in these documents establishes that the difference is a customer credit, freight overcharge, refund, recovery, payment, or claim allowance event.

Additional public case lead: [court-filed June 2026 certificate of service](https://document.epiq11.com/document/getdocumentbycode?docId=4581915&projectCode=MCX&source=DM) identifies the May 29 **Docket 623**, a sustained second omnibus claims objection concerning no-liability, reduced-amount, and reclassified claims. **No source inspected proves GlobalTranz claim 10002 was included.** The order/schedule, claim amendment trail, and actual cash ledger must be checked before attributing any delta to that order.

The public filing's statement pages (PDF pages 115–117, one-indexed) report **102 account-statement entries**. A second analyst-side integer/decimal recalculation of the 46+46+10 indexed amount rows, including two joined page-break lines, reproduced original charges of **$26,026.61** and open balances of **$25,954.47**, exactly matching the filed claim. The sole $72.14 face-to-open change needs a credit/payment/adjustment trail. These 102 source rows have **not** been ingested or independently replayed by the RETALLY comparator, and this text-extraction check is not a full page-image verification. Do not publish underlying third-party invoice rows to GitHub.

Two adjustment pairs can be traced beyond suffix matching to matching **PRO and customer BOL** identifiers in the public pages: an XPO $861.09 original plus $56.44 reweigh adjustment, and an ABF $1,718.04 original plus $29.88 reweigh adjustment. These are valid document cross-references, not evidence of incorrect charges or independent carrier weight certificates. A third adjustment lacks its base within the indexed statement. Counting invoice pages as separate shipments is unsafe. These are **broker-issued invoices**, not verified originals from every underlying carrier.

## Research-only comparator

The new module freight/research/statement_reconciliation.py accepts only caller-supplied structured metadata. It checks invoice face vs statement original, statement totals, canonical duplicate references, explicit base/adjustment linkage **requiring matching PRO and BOL identifiers**, unknown parents, changed open balances and contradictory external claim snapshots. It never derives recovered cash, an overcharge, source reuse rights, or shipment-family counts.

Run the 20 deterministic **synthetic-only** tests:

    python -m unittest freight.test_globaltranz_reconciliation -v

Existing repository-wide Freight and release CI must run on the PR and all normal branch-protection gates remain intact. This is not a production invoice importer, raw PDF extraction path, or licensed external benchmark.

## Research and release holds

- Verify actual source records and all invoice/statement line counts by independently inspecting the complete public document in a rights-compliant environment.
- Obtain claim amendment/objection/order/settlement ledger explaining the exact later register amount.
- Confirm buyer/document authority before processing original third-party documents commercially; public availability alone is insufficient.
- For a freight error: separately obtain controlling effective rate terms, underlying carrier invoice, BOL/PRO, independent classification/weight evidence, prior auditor results and payment/credit proof.
- Maintain independent adjudication and blind frozen validation; apply existing release and customer-data security controls.
- No customer outreach, payments, private-data extraction, new scheduled actions or changes to protected main were made.

## Claim-specific litigation trail (verified public court evidence; 2026-10-18)

**This is a materially stronger procedural link, not yet a verified dollar-level disposition or proof of freight overbilling.**

- **March 20, 2026 — Docket 593:** Trust filed a *second omnibus substantive objection* covering no-liability, reduced-amount and reclassified claims. [March 30 service certificate, Docket 595](https://document.epiq11.com/document/getdocumentbycode?docId=4566977&projectCode=MCX&source=DM) includes **GlobalTranz Enterprises LLC on the dedicated second-objection service lists**.
- **May 28, 2026 — Docket 619:** Certification of counsel regarding the second omnibus objection; documented in the [Epiq Docket 625 certificate](https://document.epiq11.com/document/getdocumentbycode?docId=4581183&projectCode=MCX&source=DM).
- **May 29, 2026 — Docket 623:** Court sustained the second omnibus substantive objection, as verified by its [June 3 Docket 626 certificate of service](https://document.epiq11.com/document/getdocumentbycode?docId=4581915&projectCode=MCX&source=DM). Docket 626 explicitly says **Exhibit C and Exhibit F received only the second omnibus order**. GlobalTranz is listed on Exhibit C (PDF page 9) and Exhibit F (PDF page 16), strongly tying it to the sustained objection. This does not identify the exact claim schedule or confirm the category/revised amount for GlobalTranz.
- **July 28, 2026:** Public [numerical claims register](https://document.epiq11.com/document/getdocumentbycode?docId=4596109&projectCode=MCX&source=DM) identifies GlobalTranz proof of claim **10002** as **$1,496.52 unsecured** with the original July 17, 2025 filing date and no explanatory comment.

**Still missing, do not infer:** Complete Docket 593 objection schedules, the clean/amended exhibit to Docket 619 and signed Docket 623 order schedules identifying proof of claim 10002, plus any payment/distribution/credit posting. At present the defensible finding is **court objections and a later lower registered claim**, not a confirmed $24,457.95 freight billing correction, creditor refund, or cash recovery.

Public search was unable to retrieve the claim-specific schedules. The Epiq public docket website requires dynamic browser navigation; no paid PACER access, private case materials, or outreach were used. The two categorical possibilities—substantive reduction/partial disallowance versus a separate amendment/reconciliation—remain open pending the operative schedule. A court-imposed claim reduction is not a RETALLY-generated recovery even if the reduction is eventually confirmed.

## Procedural cross-check: revised objection and withdrawn freight claim

[May 28, 2026 hearing agenda, Docket 617](https://document.epiq11.com/document/getdocumentbycode?docId=4580551&projectCode=MCX&source=DM), pages 3–4, confirms that Docket 605 (April 29) **partially withdrew and re-noticed** the substantive second omnibus objection before the court's May 29 order. Four responses appear: GalaxyDecor #10025 and Uline #1 were excluded pending resolution; LVG Ceramic #10166 acknowledged that its commercial relationship was fully satisfied; **Total Quality Logistics #10192** was **withdrawn from objection**. GlobalTranz #10002 is **not named among these four agenda responses**; omission is not proof it made no other response or that it was included in any specific schedule. The final operative schedule is still required to identify whether the GlobalTranz claim was reduced, reclassified, or treated on another basis.

[June 3, 2026 order-service certificate, Docket 626](https://document.epiq11.com/document/getdocumentbycode?docId=4581915&projectCode=MCX&source=DM), page 2 says **Exhibit C and Exhibit F received only the second omnibus order (Docket 623)**, and GlobalTranz is included in both (PDF pages 9 and 16). This is direct evidence of *service of the order*, **not** a claim-amount ruling or cash receipt. It cannot replace the signed court order's claim-specific schedules.

**No promotion:** The July 28 register's $1,496.52 entry plus the original $25,954.47 proof yields a $24,457.95 *face-value difference*. No original-cause or financial-cash explanation has been independently established. Do not attribute the difference to RETALLY savings, freight-rating error, carrier concession, payment or bank settlement.

## Original invoice chronology and post-confirmation financial reporting

- The [GlobalTranz proof-of-claim statement](https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/10247) lists **102 statement entries dated November 8, 2024 through July 7, 2025** (PDF pages 115–117, one-indexed). The petition was filed **July 8, 2025**. Thus, treating the $24,457.95 reduction as an automatic exclusion of *postpetition statement entries* is not supported by the actual list. Invoice dates alone do not settle whether particular shipping services or accounting obligations have a different priority.
- [Docket 637, filed June 24, 2026](https://document.epiq11.com/document/getdocumentsbydocket/?docketId=1231443&docketNumber=637&projectCode=MCX&source=DM), W & Z Oldco/Walker & Zanger post-confirmation quarterly report **as of March 31, 2026**, reports **$0 cumulative total cash and noncash transfers** (PDF page 2), and **$0 distributions to general unsecured claimants** (PDF page 7). These totals are *debtor-reported* and do not establish that the GlobalTranz creditor was or was not separately paid outside the reported estate distribution path, nor do they cover later periods.
- The docket records [Docket 657, filed August 31, 2026](https://www.inforuptcy.com/browse-filings/delaware-bankruptcy-court/1%3A25-bk-11296/bankruptcy-case-mosaic-companies-llc), a **quarter ending June 30, 2026 post-confirmation report for Walker & Zanger**, but underlying financial tables have not been retrieved and cannot be presumed to be zero.

**Proof still required**: operative claim-specific order exhibits in 593/605/619/623, amount basis and date, actual creditor/estate payment/credit records. No claim-to-cash attribution, customer recovery, or freight overcharge benchmark promotion.
