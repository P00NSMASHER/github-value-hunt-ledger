# RETALLY Priority 2 — source-bound freight evidence and conservative rating

**Classification:** Synthetic/approved-public source-only software improvement.
**No customer pilot, freight recovery, real payment, verified contractual rights,
independent true-positive/true-negative label, or performance claim authorized.**

Source head for implementation: `a14d227b5d9fd235fb82456904125df5d366bca9`
(October 22, 2026; exact final PR SHA is recorded by GitHub).

## Improvement coverage (prioritized items 18–28)

| Item | Scope of integrated code and acceptance | Boundary |
|---|---|---|
| 18. Original PDF extraction | Existing `freight/original_pdf_extraction.py` source-pins two official historical PDFs and parses 100 GlobalTranz and 10 ArcBest faces. New `priority2_pipeline.review_frozen_pdf_source` invokes that exact parser, re-verifies its immutable invoice/page manifest, and emits a review-only aggregate. Re-run via `retally-r2-documents.yml` in isolated hosted Python with pinned PyMuPDF. | **No universal customer PDF/OCR engine.** New carrier templates require independent rights and source verification, secure document custody, explicit parser QA and approval. |
| 19. Source-linked extraction | Every original line/adjustment/face is tied to an approved PDF SHA, page number, field witnesses and hashed signed-net arithmetic. Missing or conflicting tokens/witnesses/duplicate invoice faces fail closed. | Original document provenance is not independent shipment, bank or commercial evidence. |
| 20. Contract/source authority | `priority2_evidence.review_freight_rate` invokes the actual rating engine only with a uniquely scoped and effective, compiled, verified rate object. It separately flags buyer-contract rights/authenticity as unverified. | Uploaded `verified_controlling_authority=True` is **not** legal contract execution/consent. No validated payable recovery. |
| 21. Competing rate versions | Strict evidence route holds **all** overlapping rate authorities even when different priorities could previously select one. Explicitly rejected/disputed tariff digests are not used to produce variance. | Genuine supersession requires independent signed amendments and legal/commercial review—not synthetic `priority` metadata alone. |
| 22. Shipment fields | `witness_shipment_source` binds typed canonical shipment facts to bounded separate source bytes and enumerated fields; mismatch or absent evidence is held. No implicit substitution of rated for actual weight, shipment for invoice issue date, or missing bill-of-lading data. | SHA + claimed source kind is **not authentication** of the issuer or source rights; rating remains REVIEW. |
| 23. Rating model | Retains native six-mode rating (LTL, parcel, TL, intermodal, air, ocean) and existing supported fuel/accessorial/fixed/unit rules. New strict wrapper records **provisional-only** expected and variance when uniquely evidenced. Unmapped PDF charge tokens cannot be silently treated as contracted line types. | Unsupported contract language, fuel/surcharge schedules and missing line labels are holds, not asserted coverage. |
| 24. Safe invoice/payment joins | Existing `scoped_reconciliation` isolates buyer, business unit, counterparty, exact remittance reference and currency; new `reconcile_invoice_evidence` binds all row-level match/hold receipts to original input hashes. | Same-publisher declaration match never proves a bank payment. |
| 25. Large bounded many-to-one | Synthetic census reproduces **273 unique invoices and 217 remittance groups**, including 39 multi-invoice groups. Every group is processed within explicit bounds; oversized groups route to UNKNOWN rather than force matching. | Very large or ambiguous groups require reviewed partitioning, not unbounded combinatorial search or silent data loss. |
| 26. Explicit unknown population | No-reference, wrong-currency, no counterpart, date/amount mismatch, ambiguity and oversized groups preserve individual `UNKNOWN` entries and both independent denominators. Input/order hash and source counts reverified. | Unknown does not count as negative, carrier error, fraud, recovered cash or a successful payment. |
| 27. False-positive defenses | Adversarial synthetic example based on GAO B-221594 preserves overturned/rejected tender as disputed authority, not a low-rate collectible freight error. No external claim attached to another unrelated invoice. | Historical ruling is a **precedent**, not independent truth for GlobalTranz or ArcBest. |
| 28. Independent accuracy | Retains `sealed_real_accuracy` with independent freeze/hold, source completeness and abstention denominators. A new 110-case synthetic source-census regression confirms missing real adjudication remains **110 UNKNOWN / precision NULL / recall NULL**. Integrated PDF receipt reports zero real labels, zero verified bank payments, zero actual recovery. | Without authenticated original invoice + governing rate + bank payment + blinded independent adjudication, **real precision, recall and freight accuracy cannot be estimated**. |

## Existing authentic research census — not rebranded as detection truth

At the October 20 archived laboratory checkpoint:
- **GlobalTranz:** 100 invoice faces, 387 charge components, 93 invoices with typed discounts. Arithmetic is exact, **but source-only**; vendor tariffs, actual independent weights and bank settlements were not authenticated.
- **ArcBest:** 10 original invoice faces, missing independently extracted charge lines, invoice issue dates, or shipment proof. Unrated and UNKNOWN.
- **Pennine Care accounting:** 273 deduplicated source-declared invoice records, 217 source-declared remittance groups. Matching within that publisher's own records is **general accounting reconciliation only**; no independent bank or freight accuracy.
- Complete independently adjudicated economic freight truth: **0**. The 110 original invoice identities remain unscored UNKNOWN.

Original PDFs, any customer invoices, financial line-level contents, private identifiers and third-party credentials **must not be committed, included in this public PR, logged by CI, or posted to task prompts**.

## Correctness requirements / test matrix

- Original-document parsing remains isolated; `review_frozen_pdf_source` accepts only the two exact frozen official source SHA-256 values and old page/case census. Changes fail closed. **An in-memory batch without verified original PDF bytes is MANIFEST_ONLY: `face_amounts_verified=0`.** Actual original-byte verification requires re-parsing the supplied exact frozen PDF bytes and comparing the complete extracted batch, before any source-verification count can be positive.
- New tests: `freight/test_priority2_evidence.py`, `freight/test_priority2_pipeline.py`. Native reference parser tests: `freight/test_original_pdf_extraction_r2.py`.
- Hosted source fetch is restricted to existing approved public source URLs; no external carrier, customer or finance endpoint contacts.
- All scenario labels and currencies are synthetic unless explicitly independently sourced.
- One-cent invoice mismatch, changed PDF witness, duplicate face, invalid metadata, cross-vendor shared reference, overdue or disputed tariff, group overflow, unverified rate, or absent shipment evidence must yield a safe hold/error.
- Source-provisional rate cents remain separate from validated overcharge cents; validated economic amount, real settlement and billable fee remain zero or unavailable.
- All 110 unrelated real original invoices remain UNKNOWN in the independent accuracy ledger until actual external blinded evidence is supplied.

## Required next external evidence, **not** created by this engineering change

1. An authorized customer's legally permitted original invoices and source ownership/scope.
2. Authenticated bill-of-lading/actual shipment facts, effective executed customer-specific carrier terms and amendments.
3. Independent bank-cleared settlement sources (not payment-status labels from invoice publishers).
4. Genuine independent reviewers and adjudication of a complete frozen positive/negative holdout, with preserved model blindness.
5. Approved secure private customer environment, privacy/access controls and applicable commercial contract/release permission.

**Customer launch stays NO-GO** until the separate existing product and commercial gates are satisfied. A passing synthetic suite or public court-exhibit source replay is not a verified real customer outcome.
