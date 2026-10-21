# RETALLY four-release engineering acceptance ledger

**Scope:** Implementation candidates produced in ChatGPT using connected GitHub, October 19, 2026 (America/New_York). All four changes are DRAFT PRs and must be independently reviewed before protected-main merge. Customer launch and external accuracy claims remain on hold.

## Source-controlled implementation

| Release | Pull request | Substantive delivery | Release state |
|---|---|---|---|
| R1 Financial Integrity | [#510](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/510) | Backward-compatible original invoice schema v2 with source-bound signed discounts; exact-cent payment/credit/refund/reversal ledger with invoice hash binding; buyer+BU+supplier+currency+reference partitioned reconciliation; fail-closed customer claim gate | DRAFT, review required |
| R2 Document Intelligence | [#511](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/511) | Source-pinned, page-witnessed GlobalTranz/ArcBest original PDF extraction and exact discount arithmetic; incomplete independent facts remain explicit holds | DRAFT, review required |
| R3 Independent Accuracy | [#512](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/512) | Separately frozen model/truth hashes, reviewer/timestamp integrity, unknown labels preserved, abstention-aware precision/recall/FPR with Wilson 95% intervals | DRAFT, independent source labels missing |
| R4 Reliability | [#513](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/513) | Exact-money property tests, synthetic 10K/100K replay, deterministic ordering, aggregate-only nonpublic evidence dashboard and mandatory release holds | DRAFT, review required |

**Stacked merge order:** #510 onto main, #511 after #510, #512 after #511, #513 after #512. Independently inspect each PR and confirm the merged base contains all prior commits. No auto-merge label or deployment is authorized by this ledger.

## Evidence-based tests and reproducibility

The preceding independent *research* candidate [PR #506](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/506) tested the unchanged GlobalTranz 120-page and ArcBest 74-page PDFs plus five Pennine Care publication CSVs. Its results are separate from these implementation PRs and require their own independent review.

- GlobalTranz: 100 invoice faces, 387 positive/negative charge tokens, 100 exact face sums, 93 invoices requiring typed negative discounts.
- ArcBest: 10 original face amounts; missing complete independently verified shipment/rate line items remain review only.
- Pennine: 314 monthly published disclosure rows, 273 unique economic invoice identities, 41 repeated disclosures, 217 declared payment references. Original unscoped kernel matched 195/273; strictly reference-scoped same-source replay matched 273/273. This proves only structural consistency, NOT independent cleared payments.
- Blinded freight benchmark: **0** fully independently labeled real positive/negative outcomes for the 110 original freight invoice identities; precision, recall and recovery classification accuracy are **not estimable**.
- R1 adversarial regression: v1 hashes unchanged, typed discount validation, over-discount, charge/adjustment collisions, exact source hash, reversal replay, forged invoice/payment binding, false claim attempts.
- R2 direct originals: pin SHA-256, tokenize positive/negative invoice amounts, require original total equality, reject tampered/unknown PDFs, no dummy tariff/bank/adjudication.
- R3: protect independent truth/model freeze hashes, disjoint roles, timestamps and cases; unresolved cases are not negatives; synthetic tests do not authorize accuracy claims.
- R4: randomized integer-cent invariants, 273 case test and 10K+100K purely synthetic invoice replay. [First R4 benchmark](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39357883026): median 0.553 seconds / ~18,084 records per second for 10K; 5.650 seconds / ~17,699 records per second for 100K; exact zero missing and zero cross-reference mismatch on these deterministic synthetic populations. Performance is a single GitHub runner snapshot, not an SLO guarantee.

## Engineering proof boundaries

- Original invoices, court documents and Pennine records are never uploaded into the public code repository. CI uses ephemeral source-pinned reads and outputs only aggregates.
- A verified-rate discrepancy is a **candidate**, not independently adjudicated and paid recovery. The R1 primitive refuses to mint validated or realized dollars even if it is handed self-declared bank and reviewer attributes. Customer proof uses the separate independent buyer pilot acceptance protocol.
- Source-provided payment status (including "fully paid") is **not** a second independent bank ledger.
- A historical government ruling with favorable arithmetic is not a label for a different invoice.
- Reconciliation is scoped by buyer, business unit, supplier, currency and reference. Large/ambiguous groups remain unmatched/reviewed. Synthetic matches do not prove real-world precision.
- Pure-CI source hash validation and noindex HTML are **not** replacements for deployed customer document sandboxing, encryption, signed external review, privacy compliance, or rights-clearance assessment.

## Remaining non-automatable customer acceptance gaps

1. Independent PR reviews and protected-main approvals, including reproducibility of the finance model, ingestion policy, performance and security controls.
2. Authorized customer-contract effective tariff/rate, independently verified shipment attributes, genuine paid/credited bank documents, and human-adjudicated positive **and** negative examples linked to the same shipment.
3. Original customer reuse-rights authorization and private encrypted original-document handling review before customer import.
4. Actual source-system independent confirmation of buyer payment receipts and any later customer refund/reversal.
5. Complete independent blinded study, separate customer pilot/release go/no-go, and actual production deployment authorization.

**Acceptance:** engineering candidates submitted; customer release and real-world accuracy claims held. A green GitHub Actions result is necessary but not sufficient for an independently validated customer-facing release.
