# RETALLY isolated real-document laboratory

**Status:** research only. This branch must not enable pilot release, commercial
proof, customer intake, recovery claims, contacting parties, or external
publication of original invoice content.

## Reproducible source material

- GlobalTranz / Walker & Zanger bankruptcy claim 10247: original 120-page PDF,
  invoice faces and original/current open-account statement. The statement is
  **not** a bank-cleared payment ledger.
- ArcBest / SDI bankruptcy claim 408: original 74-page PDF, ten identified
  original ABF freight invoices and supplementary shipment records.
- Pennine Care NHS Foundation Trust: original monthly April-August 2026
  spending-over-£25,000 CSVs, UK Open Government Licence. These include invoice
  IDs, payment numbers, statuses and amounts as reported by one publisher,
  **not** independent payment confirmations.
- Historical GAO freight rulings: research references. No ruling automatically
  supplies a matched original invoice, effective shipment-specific tariff,
  cleared payment, and complete binary adjudication label.

Source URLs and seven frozen original-file SHA-256 digests are fixed in
real_document_lab.py. Input byte drift fails closed before processing; a
changed source requires independent provenance review and an explicit baseline
change. Fetches enforce HTTPS origin and redirect allowlists, size limits,
strict UTF-8, and bounded PDF pages/text. The test job fetches these source
bytes only into an ephemeral GitHub-hosted runner. It does **not** store their
original bytes, invoice rows, per-invoice identities, or extracted text in Git,
Actions artifacts, or public step summaries.

The source-scoped Pennine accounting replay digest is also pinned to an exact
SHA-256 fingerprint observed independently on Windows and a GitHub-hosted Linux
run: `c599d67a0887fa84aacb4bc91af28d3b72dfbadf6a552bb64ee76947d45ff213`.
A source or reconciliation-algorithm change that alters this fingerprint must
be reviewed and explicitly re-baselined. The fingerprint binds a specific
source/kernel replay; it is **not** a cryptographic bank attestation or an
independent payment truth label.

## Real engine calls and evidence limits

1. Run freight.ingestion_gateway.ingest_bytes on **each original PDF**. The
   native production contract routes accepted PDF to
   DOCUMENT_EXTRACTION_REQUIRED and does not claim a native PDF invoice parser.
2. Use pymupdf as an explicitly **lab-only document text adapter** to extract
   invoice identifiers, face totals, service types and source pages. Cross-check
   against independently observed original-document spot checks. No OCR guesses
   or ungrounded fields.
3. Reconcile GlobalTranz original invoice face amounts against **original**
   statement amounts using RETALLY's recoveryworks.reconciliation_kernel
   engine. Keep current statement balances separate; do not infer
   amount-due/credit movements equal an actual payment.
4. Deduplicate Pennine disclosed economic invoice identities across five
   months. Feed the *unique real disclosed invoices* and **source-derived**
   grouped payment declarations through the **same actual RETALLY reconciliation
   engine**. Detect cross-reference incorrect joins, amount inconsistencies,
   inflated joins, cross-month repeated reporting, multiple legitimate invoices
   per remittance reference, missing payment reference and malformed amounts.
   This is a same-source structural financial benchmark, **not** bank clearing,
   independent settlement accuracy, verified duplicates or proven overcharges.
   A republished economic invoice must retain the same reported payment
   reference, date, currency and status; any conflict fails the entire replay
   before first-row deduplication or matching. Legitimate multiple invoices
   under one remittance stay distinct, and payment keys include the supplier
   so two unrelated suppliers cannot be merged by coincidentally equal numbers.
   The same supplier/invoice number with a different issue date or exact
   invoice amount is held for source adjudication, not silently counted as a
   second invoice; control-character or Unicode alias-form source identities
   are rejected before delimiter-based keys and derived transaction IDs.
   CSV header candidates must contain each required field exactly once.
   Original invoice, supplier and remittance cells are checked before
   whitespace stripping, so a trailing control character cannot vanish into
   the same hashed identity as the clean invoice.
   The laboratory also parses each original Pennine CSV through the separate
   public census adapter and compares the complete normalized row multisets
   (including integer pennies, references, dates, status and duplicate counts)
   in memory. It emits only aggregate pass/count metadata. Both adapters read
   the **same publisher bytes**: agreement detects parser drift and missing
   rows, not independent payment or settlement truth. Frozen source URL/SHA
   registries must agree between adapters.
5. A separate ArcBest smoke test may construct canonical records from the
   original document's printed postal codes, rated weight, shipment date and
   total. It explicitly marks the **shipment-date-as-invoice-date proxy**, the
   **rated-weight-as-actual-weight proxy**, and **face-total-as-charge proxy**.
   These records are inadmissible as freight accuracy evidence. The real rating
   engine must return REVIEW_REQUIRED with no expected rate or dollar finding.
   Missing source fields remain BLOCKED.
6. The blinded freight evaluator freezes a prediction-side unknown/review state
   and counts only complete, independently labeled positive/negative economic
   cases. Until an independent truth owner and reviewers have actually frozen
   their work, the report explicitly says blindness **NOT EXECUTED**, and
   metrics stay NULL. Eight historical GAO adjudication URLs are indexed as public
   reference sources, but none is silently attached to a different original
   invoice. Missing case linkage remains UNRESOLVED. Precision, recall,
   specificity and real detection accuracy stay **null** with no labels.
7. Compare unscoped vs source-reference-partitioned runs of the actual RETALLY
   reconciliation kernel. The native many-to-one global candidate window is
   bounded at 18; the lab's strictly partitioned replay retains that bounded
   kernel while only allowing matches within the same declared payment reference.
   Before kernel execution, the adapter verifies exact transaction-ID uniqueness,
   complete group-key coverage, source-key reference/date/currency binding,
   and an exact integer group bound between 1 and 18. A deliberately mislabeled
   transaction is **rejected** rather than matched through amount/date fallback
   and reported as having zero cross-reference errors. Synthetic single-field
   reference keys remain accepted only when equal to the actual transaction
   reference. Supplier identity in full keys is still sourced from the same
   publisher disclosure, not an independent bank identity confirmation.
   This measures structural consistency, not bank-cleared matching accuracy.
   Completeness is explicitly two-sided: the report counts matched and
   unmatched source-declared counterparts as well as invoices. An orphaned
   declaration, oversized/unmatched group, or empty population leaves
   `source_declaration_reconciliation_complete=false`, even if every invoice
   is matched. The controlled fault-injection suite requires this complete
   same-source baseline before testing mutations. Neither a matched
   declaration nor this completeness flag establishes independent bank clearing.
8. Run four **controlled negative tests** with the real published invoice
   population: plus-one-penny counterpart amount, incorrect payment reference,
   wrong currency, and duplicate grouped payment declaration. All must result
   in an unmatched or rejected assertion. These are laboratory-injected
   counterexamples, not demonstrated customer payment errors.
9. Retain source-published payment-status counts, null/malformed values,
   supplier-and-invoice economic identity variants and negative/zero amounts
   as explicit general-accounting data-quality diagnostics. Reject nonblank
   truncated CSV rows and nonblank rows missing both invoice and payment IDs
   instead of silently omitting them from the population.
10. Check independent GAO decision-narrative arithmetic in integer cents,
    including the **reversal** of an allegedly lower-rate collection. This
    is a historical precedent test, not an independent linked label or a
    RETALLY recovery.

11. Reconcile original GlobalTranz **freight, fuel and discount** line amounts
    against each face total. The production canonical `ChargeLine` prohibits
    negative discounts: 93/100 original invoices need separately modeled signed
    adjustments. The laboratory uses only the actual reconciliation kernel's
    signed-money parser for those discounts, and records schema incompatibility
    rather than implying production acceptance. See
    https://github.com/P00NSMASHER/github-value-hunt-ledger/issues/509.

## Run locally or in the read-only PR workflow

Use Python 3.11 and install pymupdf==1.26.5 in an isolated environment.

    python -m unittest -v freight.test_real_document_lab
    python -m freight.real_document_lab --output /tmp/retally-real-document-report.json

Output is aggregate metric metadata only. No raw invoice or buyer bytes are
persisted after the process ends. The Actions job is read-only, uses no secret,
does not upload artifacts, and cannot merge or deploy.

**Do not** promote the research-only signed-discount fallback to production
without an independently reviewed, bounded signed-credit/discount model.
Keep a freight-specific proof hold even when invoice arithmetic reconciles.

**Do not** put source PDFs/CSVs into the public repository. A production-ready
PDF extraction service, independent customer tariff/rates, payment/bank evidence,
actual independent blind adjudications, and governed commercial-rights clearance
remain separate acceptance gates.
