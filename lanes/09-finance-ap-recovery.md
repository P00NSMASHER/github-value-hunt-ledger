# Finance / AP / Recovery

## Hunter instructions
Before searching, read this file plus ../MASTER.md, ../REJECTED.md, and ../COMBINATIONS.md.

Search public GitHub repositories for unusually valuable functioning software, data pipelines, algorithms, workflows, datasets, integrations, or product infrastructure relevant to this lane. Include obscure, abandoned, low-star, and no-license repositories in discovery. Respect license/copyright for reuse.

Do not collect, reproduce, preserve, or exploit exposed credentials, personal data, authentication material, or accidentally published confidential information. Skip/quarantine those items and continue searching for legitimate technical or commercial value.

## Finding template
### Repository name
- Repository:
- Commit / revision:
- Date discovered:
- What it contains:
- Why it matters:
- Commercial possibilities:
- Build-time savings:
- Evidence inspected:
- License / rights:
- Reuse classification:
- Scores:
  - Technical value:
  - Commercial value:
  - Rarity:
  - Completeness:
  - Build-time saved:
  - Data advantage:
  - High-ticket potential:
- Next action:

## Findings
### pengyulong/InvoiceAuditAgent
- Repository: https://github.com/pengyulong/InvoiceAuditAgent
- Commit / revision: b53902513902fab91ddd7143585d898cf0ce869b
- Date discovered: 2026-09-19
- What it contains: Contract/invoice audit project with Vue/FastAPI-oriented architecture, OCR/LLM design documents, frontend/backend/deploy folders, tests, and deployment documentation.
- Why it matters: The concept and repository structure overlap directly with contract-to-invoice cross-checking, but the README itself says core functionality is still incomplete, so this is more useful as a design reference than a ready engine.
- Commercial possibilities: Architecture/reference material for AP audit and contract/invoice matching; not currently a strong direct-reuse candidate.
- Build-time savings: Low-Medium until deeper code inspection proves the backend is more complete than the README status suggests.
- Evidence inspected: README.md marks core functionality, AI integration, tests, and deployment as pending; root contains backend/frontend/tests/docs/deployment material.
- License / rights: No repository license detected.
- Reuse classification: Inspect / learn / clean-room implementation only unless permission is established.
- Scores:
  - Technical value: Medium
  - Commercial value: Medium-High conceptually
  - Rarity: Low-Medium
  - Completeness: Low-Medium
  - Build-time saved: Low-Medium
  - Data advantage: Low
  - High-ticket potential: Medium
- Next action: Deprioritize unless backend inspection reveals functioning audit logic not reflected in the README; favor mature permissive components instead.

### leagames0221-sys/invoice-lens
- Repository: https://github.com/leagames0221-sys/invoice-lens
- Commit / revision: 4a9ce4123f8eba3308c2d414f449be68b7fbc05e
- Date discovered: 2026-09-19
- What it contains: Zero-star MIT-licensed Python AP-control pipeline that actually connects invoice PDF/template extraction, deterministic validation, exact/suspect duplicate detection, purchase-order/goods-receipt three-way matching, approval routing, double-entry journal generation, spend analysis, payment scheduling, anomaly signals, and append-only hash-chained audit persistence. The three-way matcher sums multiple goods receipts for split deliveries; exact duplicate invoices are removed from the downstream payable set; anomaly logic includes Benford first-digit analysis, just-under-approval-threshold signals, and same-vendor/same-day split detection.
- Why it matters: This is an unusually high functioning-software-to-attention ratio and provides much of the deterministic control layer needed for a pre-payment AP leakage/recovery product without making OCR or an LLM the source of truth. It is materially more complete than a document-extraction demo because upstream control results actually gate downstream approval, scheduling, accounting, and audit outputs.
- Commercial possibilities: Turn the generic controls into an evidence-backed AP leakage/recovery audit: ingest AP ledger + PO + receipt exports, identify duplicate/unsupported/mismatched payments and approval-pattern anomalies, rank money at risk, and sell a paid diagnostic plus recovery/shared-savings engagement. It also combines naturally with freight-invoice audit work as the generic AP-control layer around carrier invoices.
- Build-time savings: Approximately 6-10 weeks for the deterministic AP control/evaluation core; potentially 2-3 months when its end-to-end downstream workflow, audit persistence, demo scaffolding, and tests are counted.
- Evidence inspected: Repository metadata and commit history; README architecture/status; `src/invoice_lens/ap/pipeline.py`; `matching.py`; `dedup.py`; `fraud.py`; `store.py`; `pyproject.toml`; `LICENSE`; test search/results including `tests/test_ap.py` and `tests/test_store.py`. The inspected revision's latest commit documents 117 tests and roughly 84% measured coverage, while source inspection confirmed the core control flow rather than relying on that claim alone.
- License / rights: Core repository is MIT. Core runtime uses `pypdf` under BSD-3. The optional Yomitoku OCR dependency is identified by the project as CC BY-NC-SA 4.0/noncommercial, so it should be disabled/replaced in a commercial product rather than redistributed as part of the paid stack.
- Reuse classification: Directly reusable for the MIT/BSD core; exclude or replace the optional noncommercial OCR layer.
- Scores:
  - Technical value: 9/10
  - Commercial value: 9/10
  - Rarity: 10/10
  - Completeness: 8.5/10
  - Build-time saved: 9/10
  - Data advantage: 4/10
  - High-ticket potential: 9/10
- Next action: Extract the generic duplicate/three-way/approval/anomaly/audit modules into a Postgres-backed service, add money-at-risk and evidence fields, and benchmark on a deliberately synthetic customer-like AP/PO/GR export before any real customer data is introduced.

### CodeWithEugene/LedgerGate
- Repository: https://github.com/CodeWithEugene/LedgerGate
- Commit / revision: a030961a03282d05ba36b532e53337ee250b46aa
- Date discovered: 2026-09-19
- What it contains: Zero-star MIT-licensed finance-control project built around a small veto-only safety gate between an untrusted proposer and a sandbox ledger. The gate can preserve a proposed MATCH or downgrade it to ABSTAIN, but cannot create or rewrite an allocation. Its source independently checks empty allocations, duplicate feed references, non-positive receipts, allocation-total mismatch, unknown invoices, unsupported FX/currency mismatches, already-settled invoices, over-application, unexplained shortfalls, predated receipts, vendor mismatch, reference conflict, and amount ambiguity. The repository also contains an operator web UI/API, Docker deployment path, synthetic evaluation corpora, reproducible scorecards, and a substantial safety test suite.
- Why it matters: The reusable asset is not the benchmark score; it is the architecture for safely wrapping an AI/heuristic financial decision engine with an independently re-derived, monotone, human-auditable control. Tests explicitly exercise soundness, sufficiency, monotonicity, intervention behavior across proposers, and clause-cited vetoes. That pattern can reduce the risk of allowing an AP/freight recovery agent to make financially consequential automatic decisions.
- Commercial possibilities: Use the gate pattern as the final control layer for AP recovery, freight audit, or cash-application automation: a proposer identifies/matches a candidate; the deterministic gate rechecks invariants and either allows the action or routes it to human review with an explanation. This supports a stronger high-ticket pitch than 'AI automation' alone: automation with independently testable financial controls and an audit trail.
- Build-time savings: Approximately 4-8 weeks for the safety-control/evaluation harness and operator-review patterns, depending on how much of the existing web/API surface is retained.
- Evidence inspected: Repository metadata and commit history; README; `src/ledgergate/safety.py`; `tests/test_safety.py`; search results for web API/operator code; `Dockerfile.webapi`; `LICENSE`. Commit history also documents a deployed operator interface and a 171-test verification state, while source/test inspection confirmed the load-bearing gate invariants directly.
- License / rights: MIT.
- Reuse classification: Directly reusable.
- Scores:
  - Technical value: 9.5/10
  - Commercial value: 8.5/10
  - Rarity: 10/10
  - Completeness: 8.5/10
  - Build-time saved: 8/10
  - Data advantage: 3/10
  - High-ticket potential: 9/10
- Next action: Adapt the gate interface to AP/freight-recovery invariants and validate it against an independently authored holdout corpus; do not use the repository's synthetic benchmark scores as customer-facing safety claims.

### stateset/stateset-icommerce
- Repository: https://github.com/stateset/stateset-icommerce
- Commit / revision: 0ae4cf3c531f35d28a55f0211fc64413114d4bd1
- Date discovered: 2026-09-19
- What it contains: Low-attention, actively maintained Rust commerce engine with a substantial AP/PO/receiving substrate: supplier bill lifecycle, bill lines, approvals/disputes/cancellations, payments and allocations, payment runs, AP aging, purchase orders, receipts, SQLite/Postgres persistence, HTTP/OpenAPI routes, Python bindings, CLI/MCP surfaces, and permission-aware tools. Its core three-way matcher correlates bill lines to PO lines, aggregates receipt quantities across receipts, and aggregates billed quantity across all bill lines sharing a PO line so split-line overbilling cannot evade the quantity check; it also checks unit price and configurable relative tolerances.
- Why it matters: This can collapse months of durable AP-domain plumbing underneath a recovery/audit product. Instead of rebuilding money/state/payment/PO/receipt lifecycles and storage, a new product can concentrate engineering on recovery rules, evidence, customer integrations, and monetization. The actively maintained Postgres/HTTP layers make it materially more useful than a standalone matching function.
- Commercial possibilities: Use only the AP + purchase-order + receiving components as the durable transaction substrate for an AP/freight recovery SaaS, then layer invoice-lens-style controls/document evidence above it. The combination is especially attractive for buyers who need auditability and lifecycle state rather than a one-off spreadsheet report.
- Build-time savings: Approximately 3-6 months of AP/PO/receiving domain, persistence, API, and integration plumbing.
- Evidence inspected: Repository metadata and recent commits; root `LICENSE`; `crates/stateset-embedded/src/accounts_payable.rs`; `crates/stateset-core/src/models/accounts_payable.rs`; Python finance matching tests; search evidence for Rust financial-event/property tests; Postgres implementation paths; HTTP AP routes; OpenAPI/CLI/MCP tool inventories.
- License / rights: Root license permits use under either MIT or Apache-2.0 at the user's option. Preserve the applicable notices/terms for the chosen license; verify bundled third-party component licenses before redistribution.
- Reuse classification: Directly reusable under the selected permissive license.
- Scores:
  - Technical value: 9.5/10
  - Commercial value: 9/10
  - Rarity: 8.5/10
  - Completeness: 9.5/10
  - Build-time saved: 10/10
  - Data advantage: 4/10
  - High-ticket potential: 9/10
- Next action: Spike only the AP + PO + receiving crates behind a recovery-service boundary and perform a focused tenant-isolation/security review before considering the HTTP layer production-ready for multi-tenant hosting.

### amrzainmubarak/reconforge-erp
- Repository: https://github.com/amrzainmubarak/reconforge-erp
- Commit / revision: b61ea56bb9c135fda12546e173795af3c243e4fb
- Date discovered: 2026-09-19
- What it contains: One-star MIT-licensed Python reconciliation/audit platform with a concrete governed AP slice plus broader financial-control infrastructure. The AP implementation has supplier, purchase-order, posted-receipt, supplier-invoice and three-way-match lifecycles; exact monetary storage in integer minor units and exact quantity representations; stable variance reason codes; an exception queue; optimistic row versions; idempotency; separation-of-duties checks; atomic audit/outbox writes; backup/restore coverage; SQLite and PostgreSQL repositories; API routes; and a Postgres schema with forced row-level security and tenant-aware parent foreign keys. The three-way matcher recomputes receipt quantity, PO price, and line-total variances, moves invoices to Matched/Exception, opens or resolves a control exception, and requires a passed match plus independent approver before invoice approval.
- Why it matters: Existing lane findings cover AP transaction substrate, anomaly detection, and veto controls, but ReconForge adds a rare audit/control-plane substrate: deterministic exception routing, atomic evidence/outbox semantics, SoD, exact-money invariants, backup/restore behavior, and tested multi-tenant Postgres boundaries. The live-Postgres integration test creates two tenants, exercises the full maker/checker PO→receipt→invoice→match→approval lifecycle for one, and verifies the other tenant sees no suppliers or invoices. That substantially compresses the unglamorous control engineering needed before a high-value recovery product can safely ingest customer accounting exports.
- Commercial possibilities: Use the reconciliation/exception/evidence layers as the control plane beneath AP or freight recovery: import GL/AP/PO/receipt exports, run deterministic recovery tests, route exceptions by financial impact, preserve auditable evidence, and sell continuous-controls/recovery diagnostics or a finance-close exception cockpit. The broader stock-to-GL/reconciliation orientation also creates an adjacent inventory/WIP leakage-audit path without needing to build the entire controls framework from scratch.
- Build-time savings: Approximately 2-5 months for the finance-control, exception, audit/outbox, exact-money, Postgres tenancy, and recovery-workflow substrate; less if only the AP matcher is reused because StateSet/invoice-lens already cover part of that domain.
- Evidence inspected: Repository metadata; latest inspected commit; root `LICENSE`; recursive tree; `reconforge/application/payables.py`; `reconforge/infrastructure/sqlite_payables.py` including the full three-way-match and approval path; `tests/test_payables.py`; `tests/test_postgres_payables.py` including forced-RLS/cross-tenant-FK assertions and the optional live two-tenant lifecycle test; source/search evidence for `reconforge/infrastructure/postgres_payables.py`, API routes, architecture/current-state docs, changelog, exception queue, audit/outbox and exact-decimal migrations. Source tests cover pass/exception cases, stale-version rejection, creator-vs-approver SoD, rollback on audit/outbox failure, backup/restore preservation, tenant scoping, exact quantities, and Postgres contract parity.
- License / rights: MIT at the inspected revision. Direct reuse is permitted subject to the MIT notice; bundled dependency licenses should still be checked before redistribution.
- Reuse classification: Directly reusable.
- Scores:
  - Technical value: 9.5/10
  - Commercial value: 9/10
  - Rarity: 9/10
  - Completeness: 9/10
  - Build-time saved: 9.5/10
  - Data advantage: 3/10
  - High-ticket potential: 9/10
- Next action: Isolate the Postgres AP/reconciliation + exception/evidence/outbox modules behind the recovery-service boundary and run an independently authored synthetic multi-tenant GL/AP/PO/receipt corpus through them; keep the repository's stated boundary explicit that statutory AP posting, tax, payment execution, and ERP writeback are not implemented.

### anshpatel017/SpendGuard-
- Repository: https://github.com/anshpatel017/SpendGuard-
- Commit / revision: 160332410d015ff719e52fb71e1fd4871a3eb01c
- Date discovered: 2026-09-19
- What it contains: Zero-star Python procurement-spend anomaly project with unusually substantive and tested detection logic. The deeply inspected duplicate detector uses exact duplicate grouping plus amount/date blocking, supplier-name identity confirmation, a Fellegi-Sunter EM model with priors that resist inventing a duplicate class on clean data, far-apart look-alike reference pairs for non-match probabilities, transitive grouping of triplicates, per-field match weights, policy/evidence metadata, and repeat-amount-at-risk calculations. Its split-purchase detector finds minimal sub-threshold runs that cross an approval threshold inside a policy window and ranks them by timing, item homogeneity, identical rates, and number of parts. Its price-inflation detector uses robust log-price statistics, measurable bulk/time controls, robust residual z-scores and an Isolation Forest as a non-authoritative second opinion, while explicitly documenting weak F1 and better ranking performance rather than hiding the limitation. The repository also contains ingestion, case storage, policy retrieval and read-only agent tools plus a sizable test suite.
- Why it matters: This is one of the more sophisticated low-attention open implementations found for the specific leakage patterns that matter in AP/procurement recovery: fuzzy duplicates, approval-threshold splitting and price inflation. The duplicate tests assert deterministic results, tolerance boundaries, triplicate clustering, low false-positive behavior on clean recurring-contract data, and at least 0.90 precision / 0.75 recall on the project's synthetic injected dataset. Those synthetic numbers are not customer-ready claims, but the test design and clean-room algorithms can materially improve an evidence-ranked recovery engine beyond simple exact-duplicate rules.
- Commercial possibilities: Use the inspected concepts to build a recovery-candidate ranking layer on top of the permissively licensed AP substrate already in this lane: exact/near duplicate payments or invoices, split-purchase circumvention candidates, and statistically unusual price lines, each carrying money-at-risk plus machine-readable evidence for human confirmation. This is especially useful for retrospective AP audits where PO/receipt data is incomplete and transaction-ledger patterns must generate the initial recovery queue.
- Build-time savings: Approximately 4-8 weeks of anomaly-detection design, blocking/linkage, evidence shaping, synthetic injection/evaluation and boundary-test work if independently reimplemented; direct code reuse is not currently available because no license was found.
- Evidence inspected: Repository metadata and exact commit; recursive tree; README/status; `backend/src/spendguard/detectors/d1_duplicates.py`; `d2_splits.py`; `d3_inflation.py`; `backend/tests/test_d1.py`; backend test inventory; commit message for the current revision. Inspection also confirmed the README's Investigator/Verifier work is not yet present as completed source at this revision, so this finding is based on the implemented detectors/tools rather than future agent claims.
- License / rights: No repository license detected: GitHub license metadata is null, no LICENSE appeared in the inspected tree, and a direct fetch of `LICENSE` returned 404. Copyright therefore remains with the author by default.
- Reuse classification: Inspect / learn / clean-room implementation only unless permission or a license is established.
- Scores:
  - Technical value: 8.5/10
  - Commercial value: 8.5/10
  - Rarity: 9/10
  - Completeness: 7/10
  - Build-time saved: 7.5/10
  - Data advantage: 3/10
  - High-ticket potential: 8.5/10
- Next action: Reimplement only the valuable detector concepts against an independently authored schema and synthetic holdout corpus, then compare incremental dollars-at-risk found over invoice-lens/dedupe baselines; do not copy the unlicensed code and do not market the repository's synthetic precision/recall or price-ranking figures as real-world accuracy.


### Noone9029/Accounting-App — realized-recovery settlement and supplier-credit state machine
- Repository: https://github.com/Noone9029/Accounting-App
- Commit / revision: 90e0eaa4896a55c1c8cda1c4101f4ab1323a4a61
- Date discovered: 2026-09-22
- What actually works: Zero-star TypeScript/NestJS/Prisma accounting SaaS with a substantive AP exception and settlement layer, not merely invoice CRUD. Inspected code/tests implement purchase-order/bill/receipt matching, over-billed and pending-receipt exception states, tenant-scoped review records with no-posting side effects, purchase debit notes with immutable application/reversal rows and unapplied balances, supplier payments with unapplied credit, later application and reversal, supplier refunds sourced from either unapplied supplier payments or purchase debit notes, idempotent void/reversal behavior, supplier ledgers/statements, accounting journals, fiscal-period guards and extensive local/deployed proof artifacts.
- Evidence of implementation: `apps/api/src/purchase-matching/purchase-matching.service.ts` and its ~22KB spec; `purchase-debit-notes/*` service and ~30KB rules spec; `supplier-payments/*` service and ~48KB rules spec; `supplier-refunds/*` service and ~14KB rules spec; README accounting rules; DEV-08 evidence showing actual local mutation/reversal sequences. Tests explicitly cover over-billing, review lifecycle, cross-tenant blocking, unapplied-credit exhaustion, repeated reversal blocking, posted-refund void blockers, refund void restoration, and repeated/idempotent actions.
- Why it matters: Most recovery tools stop at “we found $X.” This supplies the missing realized-recovery state model: identified exception -> supplier credit/debit note -> application to open bill OR cash refund -> reversible/idempotent accounting evidence. That distinction is commercially important because contingency fees should be based on realized cash/credit, not merely estimated leakage.
- Useful capability/workflow: `RecoveryCase -> CreditEntitlement -> SupplierCreditSource -> Allocation/Refund -> RealizedRecovery -> Reversal` can be clean-roomed or adapted into an AP Recovery ledger. The existing purchase-matching review object is also a strong template for human-only recovery adjudication.
- Likely buyer: Controller, AP director, shared-services lead, procurement finance, recovery-audit firm.
- Pain solved: Unapplied supplier credits, overpayments, debit balances and audit findings often remain “identified” without a reliable trail proving whether they were actually applied, refunded, reversed or double-counted.
- Fastest monetization path: Managed AP-recovery engagement where imported findings are tracked through verified supplier credit/refund realization; charge contingency fee only on realized recoveries.
- Paid-pilot concept: 90-day supplier-credit recovery pilot on AP history + current open credits. Deliver a case ledger with source finding, supplier evidence, outstanding credit, application/refund proof and recovered amount.
- Estimated engineering time saved: 2-4 months for settlement/accounting state-machine design, idempotency/reversal logic and test cases.
- License / reuse status: No public repository license detected at inspected revision; project-level user authorization says rights are available. Keep provenance explicit.
- Important risks: Built as a broad accounting product rather than a recovery product; some proof is local/beta rather than production/customer-data evidence; recovery ingestion and supplier-contact workflows still need purpose-built controls.
- Connections: Combine with `invoice-lens` for discovery, `erpocr_integration` for supplier statements, and ERP-native extracts for a complete detect -> prove -> realize loop.
- Opportunity score: **9.6/10**.

### wphamman/erpocr_integration — ERPNext supplier-statement reconciliation intake
- Repository: https://github.com/wphamman/erpocr_integration
- Commit / revision: a9c82c0ff02f580ff60ebf012797686ba91e977e
- Date discovered: 2026-09-22
- What actually works: Active two-star ERPNext/Frappe application that classifies uploaded PDFs, extracts supplier statements, matches supplier identities, reconciles statement transaction references to submitted Purchase Invoices, carries a 365-day brought-forward candidate window, prefers in-period candidates deterministically, amount-checks references, performs reverse checks for ERP invoices missing from statements, re-reconciles on new PI submission and exposes accountant review status.
- Evidence of implementation: `erpocr_integration/tasks/reconcile.py`, `statement_api.py`, OCR Statement doctypes, `test_reconcile.py`, `test_statement_api.py`, and OCR Statement guide. Tests explicitly cover recycled invoice references, recurring same-ref/same-amount invoices, consumed-candidate re-reference, mixed date types, period-bounded reverse checks and enqueue-failure isolation.
- Why it matters: Supplier statements are one of the best recovery evidence sources because they reveal open credits, unapplied balances, vendor-side invoices and timing differences that the buyer's AP ledger alone cannot show.
- Useful capability/workflow: PDF supplier statement -> supplier entity match -> statement lines -> AP ledger cross-check -> missing/mismatched/not-on-statement review population.
- Likely buyer: ERPNext users, AP teams, outsourced bookkeeping/shared services.
- Pain solved: Manual supplier-statement reconciliation and hidden discrepancies across supplier vs buyer ledgers.
- Fastest monetization path: Statement-reconciliation diagnostic layered onto AP Recovery; customer uploads statements plus ERP export.
- Paid-pilot concept: Reconcile the top 25 suppliers' latest statements and produce a recovery queue for credits/mismatches/missing records.
- Estimated engineering time saved: 4-8 weeks for ERPNext statement ingestion, reconciliation edge cases and review workflow.
- License / reuse status: GPL-3.0.
- Important risks: Current credit-only statement lines are treated generically as payments; supplier credit memos/refunds need a richer classifier before money can be called recoverable. Gemini/Drive dependencies may need replacement for a local-first deployment.
- Connections: Feed discrepancies into the Accounting-App realized-recovery state machine; use Invoice Lens or a deterministic AP matcher to prove underlying invoice/PO/receipt cause.
- Opportunity score: **8.8/10**.

### ai-frankie/ap-close-engine — independent AP re-performance and control falsifier
- Repository: https://github.com/ai-frankie/ap-close-engine
- Commit / revision: db38c8476ccd21155a5dc161c5f36b9747e88e64
- Date discovered: 2026-09-22
- What actually works: Zero-star Python AP close/control engine with PO-receipt-invoice matching, duplicate-payment detection, AP subledger-to-GL reconciliation, GRNI completeness, negative balance checks, vendor-statement reconciliation and an independent reviewer that recomputes truth from raw data and compares a prepared close workbook against it.
- Evidence of implementation: `ap_match.py`, `ap_duplicates.py`, `ap_vendor_recon.py`, `ap_review.py`, `ap_controls.py`, `CONTROLS.md`, and 35 tests in `test_ap.py`. Tests pin planted duplicate recovery, price variance, GRNI, GL tie failures, manual/top-side AP-control JEs and reviewer detection of double-count/omission errors.
- Why it matters: This is a compact independent falsifier. A recovery claim should survive a separately implemented re-performance path before entering a contingency-fee recovery queue.
- Useful capability/workflow: raw AP/PO/receipt/payment/GL -> recomputed truth -> compare against prepared findings -> PASS/FAIL with diagnosis.
- Likely buyer: Controllers, audit/recovery firms, finance transformation teams.
- Pain solved: Self-confirming audit logic and spreadsheet-preparer errors.
- Fastest monetization path: Use as an independent validation pass in paid AP diagnostics, not as the primary product.
- Paid-pilot concept: Run the client's prepared AP recovery workbook through an independent recomputation and produce a falsification report before supplier contact.
- Estimated engineering time saved: 2-4 weeks for an independent control/re-performance harness.
- License / reuse status: No public license detected at inspected revision; project-level user authorization says rights are available. Core data is synthetic.
- Important risks: Single-line PO/full-receipt assumptions, floats rather than Decimal, fixed schemas, synthetic validation only.
- Connections: Pair with Invoice Lens as primary engine and require disagreement to route to human review rather than majority vote.
- Opportunity score: **8.4/10**.

### vendorrebate/vendorrebate — rebate/deduction recovery domain logic
- Repository: https://github.com/vendorrebate/vendorrebate
- Commit / revision: f37427a762555f4538aa4ffd21e7afaadc6e81e9
- Date discovered: 2026-09-22
- What it contains: Zero-star code-first practitioner reference covering versioned rebate agreements, EDI 810/852/844 ingestion, Decimal-exact accruals, deterministic eligibility/claim rules, duplicate deduction detection, short-pay recovery, dispute-window aging, immutable recovery packets, idempotent recovery queues and financial-close posting patterns. It is a reference/playbook rather than a finished application.
- Evidence of implementation: Long-form guides include concrete runnable Python/Pydantic/Decimal patterns and validation checks for schema-version hashing and replay, EDI 844 claims, duplicate detection, claim confidence, payment-to-accrual reconciliation and unauthorized-deduction recovery. Inspected `versioning-rebate-agreement-schemas` and `routing-unauthorized-deductions-for-recovery` in depth.
- Why it matters: Opens an adjacent high-value recovery vertical: vendor rebates/trade promotions/unauthorized deductions, where negotiated terms and payout tiers are often poorly reconciled and disputed.
- Useful capability/workflow: versioned agreement -> earned accrual -> incoming deduction/claim -> authorization check -> evidence packet -> dispute-window priority -> idempotent recovery queue -> realized settlement.
- Likely buyer: Retailers, distributors, CPG manufacturers, trade-promotion finance teams.
- Pain solved: Missed rebates, duplicate/invalid deductions, short-pay leakage and unreconciled trade accruals.
- Fastest monetization path: Managed rebate/deduction reconciliation pilot using ERP/POS/EDI exports before building a full SaaS.
- Paid-pilot concept: One vendor/program/quarter; recompute earned rebate and deductions to the cent, flag unsupported deductions, and package recovery evidence.
- Estimated engineering time saved: 4-8 weeks of domain modeling and failure-mode discovery; less direct code savings because this is not a complete app.
- License / reuse status: No public license detected at inspected revision; project-level user authorization says rights are available. Treat it primarily as domain-logic/reference unless provenance requires otherwise.
- Important risks: No integrated application/test suite; accounting treatment and contract interpretation remain buyer-specific and require human review.
- Connections: Strong extension of AP Recovery beyond duplicates into rebates, allowances and retailer/vendor deductions.
- Opportunity score: **8.9/10**.

### Enginatics/Oracle-EBS-SQL — Oracle EBS recovery extraction map
- Repository: https://github.com/Enginatics/Oracle-EBS-SQL
- Commit / revision: 6c0f3b1a70e1b6ff747e497176e7be9256e6e7ee
- Date discovered: 2026-09-22
- What actually works: Large current Oracle EBS SQL/report library with ready AP queries for negative supplier balances, supplier statements, invoice audit listings, PO/intercompany/SLA detail, matched/modified receipts, payment registers, open balances and trial balance. The negative-supplier query uses Oracle's SLA/open-balance machinery and filters supplier liability totals below zero; the supplier-statement query joins invoices, payments, discounts, GL periods, supplier sites and liability accounts with running/opening balances.
- Evidence of implementation: Inspected actual `AP Negative Supplier Balance.sql`, its technical description, and `AP Supplier Statement.sql`; repository contains the other named AP reports as executable SQL assets.
- Why it matters: The fastest path into large Oracle EBS buyers is often not building an API connector first—it is giving their finance/DBA team a precise read-only extract specification using native EBS tables/packages. Negative supplier balances are directly tied to overpayment/credit-refund opportunities.
- Useful capability/data/workflow: Oracle EBS read-only extraction of supplier debit balances, transaction/payment statements, receipt modifications and audit populations.
- Likely buyer: Mid-market/enterprise Oracle EBS controller, AP shared services, internal audit, recovery-audit firms.
- Pain solved: Months of reverse-engineering EBS data relationships before an AP recovery pilot can even begin.
- Fastest monetization path: Oracle-EBS-specific recovery diagnostic: customer DBA runs vetted read-only SQL, exports CSV, AP Recovery analyzes and tracks cases outside the ERP.
- Paid-pilot concept: Extract all negative supplier balances plus underlying statement/payment detail for one legal entity and validate the top recovery cases.
- Estimated engineering time saved: 1-3 months of Oracle EBS report/query mapping for an enterprise pilot.
- License / reuse status: No repository license detected; source headers assert Enginatics copyright. Under project-level user authorization, use is assumed available; otherwise the schema/table/query relationships remain valuable for independently authored extraction.
- Important risks: Oracle EBS version/configuration differences; standard packages must be current; some reports depend on Blitz substitution variables/packages.
- Connections: Best enterprise ingestion route discovered so far for the AP Recovery stack; downstream logic remains Invoice Lens + independent reviewer + realized-recovery ledger.
- Opportunity score: **9.2/10**.


### Accountw-debug/mdq — SAP AP leakage rules + synthetic gold corpus
- Repository: https://github.com/Accountw-debug/mdq
- Commit / revision: 8853e2c54fdc293903e994e40c629808008d782e
- Date discovered: 2026-09-22
- What actually works: Zero-star Python/DuckDB finance-quality and leakage engine with SAP ECC read-only extraction instructions, canonical schemas, deterministic AP leakage/control rules, explicit confidence tiers, SAP remediation fields, a fully synthetic SAP-style source corpus, planted defects, expected findings and a very large pytest regression suite. Latest commit reports 1,083 passing tests and specifically tightens data-as-of window semantics and AP-LEA-002.
- Evidence of implementation: `docs/extraction/SAP-ECC-EXTRACTION.md`; `logic/rules/AP-LEA-001.rule.sql` duplicate-payment logic; `AP-LEA-002.rule.sql` cash-discount leakage; `AP-COM-003.rule.sql` SAP duplicate-invoice-check control; `AP-CON-001.rule.sql` vendor IBAN clusters with legitimate-relationship exclusions; AP VAT/IBAN validation rules; `engine/tests/test_rules_ap.py`; `testdata/README.md`.
- Rare / undernoticed value: AP-LEA-001 does not merely flag same vendor/amount/reference pairs; it suppresses pairs when an equal-value AP credit memo later nets the duplicate, avoiding a common false “recoverable duplicate” claim. AP-LEA-002 separates realized cash-discount loss, expired-unpaid loss and still-avoidable value, using run data-as-of semantics rather than current wall-clock time. The rules preserve UNKNOWN rather than inventing a correction.
- Test corpus: deterministic synthetic SAP ECC-style dataset (~2,000 customers, 1,500 vendors, ~40k AR + ~20k AP items, ~77k rows) with planted defects and independent expected-results generation. The base tenant is designed to trigger zero rules before defects are layered.
- Useful capability/workflow: SAP ECC exports (LFA1/LFB1/LFBK/BSIK/BSAK/T052/TIBAN/T001 etc.) -> canonical AP ledger -> leakage/control rules -> evidence-bearing findings -> human review.
- Likely buyer: SAP ECC/S/4 controller, AP shared services, internal audit, treasury/procurement finance, recovery-audit firms.
- Pain solved: duplicate vendor payments, missed cash discounts, weak duplicate-invoice controls, risky shared bank accounts, invalid vendor banking/tax master data and false-positive-heavy AP recovery.
- Fastest monetization path: read-only SAP AP Recovery Diagnostic. Customer runs supplied SE16N/FBL1N exports; no SAP writeback required.
- Paid-pilot concept: one company code / 12 months AP history; quantify independently validated duplicate-payment and discount leakage plus control gaps, then track only confirmed supplier credits/refunds as realized recovery.
- Estimated engineering time saved: 2-4 months across SAP field mapping, AP domain edge cases, regression corpus, fail-closed rule semantics and QA.
- License / reuse status: no public repository license detected at inspected revision; project-level user authorization asserts reuse rights. Keep provenance and external SAP product/field documentation rights separate.
- Important dependencies/risks: extraction is file-based rather than a live SAP connector; S/4HANA source mappings need ACDOCA/CDS adaptation; synthetic benchmarks are not evidence of customer recovery yield.
- Connections: Pair directly with `ib823/sapconnect` for live RFC/OData extraction and with the AP Recovery realized-settlement ledger for credit/refund attribution.
- Opportunity score: **9.8/10**.

### ib823/sapconnect — Apache SAP ECC/S4 extraction substrate
- Repository: https://github.com/ib823/sapconnect
- Commit / revision: 5851e9fdeaba462c3137686f4ced0aae1ba4b0f7
- Date discovered: 2026-09-22
- What actually works: Zero-star Node.js SAP connectivity/extraction platform with OData and RFC support, pooled RFC connections, a universal `RFC_READ_TABLE` reader with fallback function modules, field selection, WHERE splitting, streaming/chunking, DD03L metadata reads, and concrete FI extractors for BKPF/BSEG/BSID/BSAD/BSIK/BSAK/BSIS/BSAS/ACDOCA. It also contains ECC/S4 process-mining table maps and vendor-open-item migration mappings.
- Evidence of implementation: `lib/rfc/table-reader.js`; `extraction/extractors/fi-transactions.js`; `extraction/process-mining/sap-table-config.js`; test tree for RFC/table reader, OData, extraction and integration. P2P mapping correlates purchasing documents, receipts, invoice verification, FI accounting docs and vendor open/cleared items.
- Useful capability/workflow: live SAP -> streamed finance/AP tables -> recovery canonical model. This can remove the manual SE16N export step when a buyer authorizes API/RFC access.
- Likely buyer: SAP ECC/S4 enterprise AP/finance teams and implementation partners.
- Pain solved: customer-specific extraction plumbing that otherwise delays every SAP recovery pilot.
- Fastest monetization path: keep CSV/SE16N as the default first-pilot path; offer this connector only when a buyer wants recurring continuous assurance.
- Estimated engineering time saved: 1-2 months of SAP RFC/OData connectivity and extraction plumbing.
- License / reuse status: repository contains Apache-2.0 LICENSE despite GitHub metadata showing NOASSERTION.
- Important dependencies/risks: some inspected FI field lists contain suspicious/generated field names and must be validated against the exact customer SAP release before use; RFC_READ_TABLE has platform/width/performance/security limitations; no connector output is authority by itself.
- Connections: `mdq` supplies better recovery semantics and gold tests; sapconnect supplies the transport/extraction plane.
- Opportunity score: **9.0/10** as enabling infrastructure.

### ballerina-platform/module-ballerinax-microsoft.dynamics365.finance — D365 Finance AP OData connector family
- Repository: https://github.com/ballerina-platform/module-ballerinax-microsoft.dynamics365.finance
- Commit / revision: fb15cb2f34749e8a031344943c107e115b93d7c4
- Date discovered: 2026-09-22
- What actually works: Zero-star Apache-2.0 connector family for Dynamics 365 Finance & Operations OData REST API (documented against v10.0.47), split into 30 packages with OAuth2, generated typed clients, tests and CI. AP-relevant packages include `vendor`, `vendorextended`, `vendorpayment`, `procurement`, plus ledger/payment/tax packages. The vendor-payment client includes typed list/read/create/update/delete operations for vendor payment journal headers/lines and other payment entities.
- Evidence of implementation: root README; `ballerina/vendorpayment/client.bal`, `types.bal`, package tests/mocks; corresponding vendor/procurement/payment packages and OpenAPI specs.
- Current authority connection: Microsoft Learn currently documents that the Vendor Payment Proposal “Check vendor balance” option should prevent payment when a vendor has a debit balance caused by unsettled credit memos/payments, and that approved vendor rebate claims generate vendor credit memos which enter normal AP settlement.
- Useful capability/workflow: D365 vendor/invoice/payment/procurement OData reads -> identify debit-balance/open-credit situations -> reconstruct settlement evidence -> realized supplier-credit recovery.
- Likely buyer: Dynamics 365 Finance AP/shared-services teams.
- Pain solved: building and maintaining a D365 API layer before recovery logic can even run.
- Fastest monetization path: start read-only using vendor/open-transaction/payment exports or OData; package current Microsoft settlement semantics into a D365-specific supplier-credit diagnostic.
- Estimated engineering time saved: 4-8 weeks of OData auth/client/entity scaffolding.
- License / reuse status: Apache-2.0.
- Important risks: generated connectors expose many write methods—first-pilot integration should be read-only; entity availability/security varies by D365 environment/version; connector types do not themselves determine recovery entitlement.
- Connections: Pair with `hidayattaufiqur/fno-navigator` table/process maps and AP Recovery v2 settlement evidence.
- Opportunity score: **9.1/10**.

### hidayattaufiqur/fno-navigator — tested D365 table/process relationship map
- Repository: https://github.com/hidayattaufiqur/fno-navigator
- Commit / revision: 0fd0998094abb3d9c3a8a30ca21ea9d21b7d69af
- Date discovered: 2026-09-22
- What actually works: Zero-star MIT Svelte/TypeScript Dynamics F&O navigation/data-model tool with rich process stages, table relationships, documentation links and a graph/pathfinder whose JS output is locked to committed golden results (and designed for parity with a Python implementation). AP flow maps vendor invoice through `VendInvoiceJour`/`VendInvoiceTrans`/`VendTrans`, and payment through `VendTrans`/`VendSettlement`/ledger journal/bank tables; cash-discount relationships are also mapped.
- Why it matters: It is a compact, tested semantic map for turning D365 OData entities/tables into recovery evidence chains rather than treating isolated API rows as sufficient proof.
- Commercial possibilities: use as implementation/reference infrastructure for a D365-specific read-only AP recovery adapter and analyst trace UI.
- Estimated engineering time saved: 2-4 weeks of D365 relationship discovery and documentation.
- License / reuse status: MIT.
- Important risks: primarily a navigation/reference graph, not a recovery engine; mappings need verification against customer configuration and official current Microsoft docs.
- Connections: Ballerina provides access; Microsoft docs provide controlling current product behavior; AP Recovery provides money-state semantics.
- Opportunity score: **8.6/10**.

### oracle-quickstart/oci-jde-monitoring — Oracle-published JDE AP integrity rule map
- Repository: https://github.com/oracle-quickstart/oci-jde-monitoring
- Commit / revision: 77c6aac079183e5076ff098ad00e463be16aa634
- Date discovered: 2026-09-22
- What actually works: Oracle quickstart/Logging Analytics package for JD Edwards EnterpriseOne containing deployable monitoring configuration plus a large JDE sensor knowledge base and scheduled database checks. AP sensor inventory covers F0411/F0413/F0414/F0911 and standard integrity reports such as R047001A, R04701, R04702A, R04711, R04712 and R04713.
- Evidence of domain logic: Oracle lookup content states, among other checks, that R04702A compares payment amount in F0414 to F0911 GL amount by batch; R04711 compares F0411 AP ledger gross/distribution values to F0911; R04712 checks F0414 payments against F0911; R04713 compares F0411 voucher gross/open amounts against F0414 paid amounts. The schedule also includes paid items with non-null open amount, unpaid items with null open amount, voucher/post-code mismatches, duplicate/mismatched payment IDs and stuck voucher batches.
- Why it matters: This gives an unusually authoritative map of JDE AP integrity relationships and failure modes, shortening the path to an EnterpriseOne-specific recovery/readiness diagnostic.
- Useful capability/workflow: read-only JDE F0411/F0413/F0414/F0911 extracts -> integrity/control checks -> candidate payment/voucher exceptions -> independent recovery review.
- Likely buyer: JDE EnterpriseOne controllers/AP shared services/internal audit.
- Fastest monetization path: customer DBA runs read-only extract/control queries; AP Recovery ingests the output and layers duplicate/credit/settlement logic.
- Estimated engineering time saved: 1-2 months of JDE AP table/control discovery.
- License / reuse status: UPL-1.0, Oracle copyright.
- Important risks: monitoring sensors prove integrity relationships, not entitlement/recovery; some referenced Oracle support-note details live outside GitHub; JDE customer versions/customizations require validation.
- Connections: analogous to the Enginatics Oracle EBS wedge; combine with AP Recovery’s independent validation and settlement attribution.
- Opportunity score: **9.0/10**.

### hotgluexyz/tap-netsuite-rest — NetSuite AP/credit/payment extraction connector
- Repository: https://github.com/hotgluexyz/tap-netsuite-rest
- Commit / revision: aeed1c57c266f265a95a30aca041ae8b4e84ed9d
- Date discovered: 2026-09-22
- What actually works: Zero-star Python Singer/Meltano NetSuite connector with a large SuiteQL/REST/SOAP client and stream catalog. Inspected streams explicitly extract vendor credits and their item/expense/tax lines, vendor bill transactions including foreign paid/unpaid totals, and bill-to-vendor-payment relationships through `NextTransactionLineLink`. The current repository also contains rate-limit/backoff work and smoke CI.
- Evidence of implementation: `tap_netsuite_rest/streams.py` (~127KB), `client.py` (~65KB), bill-attachment SuiteScript, tap config/tests. `BillPaymentsStream` joins `NextTransactionLineLink` to vendor payments and filters by the parent bill; `VendorCreditStream`/child streams expose credit details.
- Why it matters: This is enough read-only transaction structure for a first NetSuite supplier-credit recovery adapter without writing SuiteScript mutations.
- Useful capability/workflow: NetSuite SuiteQL/REST -> bills + unpaid amounts + vendor credits + payments + bill/payment links -> recovery canonical ledger.
- Likely buyer: NetSuite mid-market AP/controller teams.
- Fastest monetization path: a NetSuite Credit & Overpayment Diagnostic using a scoped read-only integration or exported SuiteQL result.
- Estimated engineering time saved: 1-2 months for extraction/catalog/pagination/rate-limit plumbing.
- License / reuse status: pyproject declares Apache 2.0; repository metadata exposes no recognized license, so preserve the pyproject provenance and confirm distribution notices before packaging.
- Important risks: README remains template-like/TODO-heavy; test suite is thin relative to implementation size; schema behavior varies by NetSuite role/account/features.
- Connections: combine with deterministic AP rules and Accounting-App-style realized credit/refund states.
- Opportunity score: **9.0/10**.

### kimtabilon/ebp_netsuite — NetSuite vendor-credit application reference
- Repository: https://github.com/kimtabilon/ebp_netsuite
- Commit / revision: 0f80fc77279b6806985a1868b12d37455bfae930
- Date discovered: 2026-09-22
- What actually works: Zero-star TypeScript/SuiteScript integration with large REST client, vendor bill synchronization and a ~48KB vendor-credit RESTlet. The credit path finds the PO/vendor bill, transforms a vendor bill into `VENDOR_CREDIT`, maps item/expense detail, locates the source bill in the credit's `apply` sublist, applies a specified amount, saves the credit, and persists the NetSuite vendor-credit ID/result back to its integration store.
- Why it matters: This is useful implementation evidence for how a recovered vendor credit can become applied settlement in NetSuite, which complements the read-only Hotglue extraction layer.
- Reuse classification: reference/optional writeback component only; first recovery product must remain read-only unless a customer explicitly authorizes ERP mutation.
- Estimated engineering time saved: 2-4 weeks of NetSuite vendor-credit application behavior discovery.
- License / reuse status: no public license detected; project-level user authorization asserts reuse rights.
- Important risks: application-specific assumptions/custom fields, extensive emergency logging, write/delete helpers and synchronization state require substantial hardening before production; not an independent recovery authority.
- Connections: Hotglue read layer -> recovery validation -> human approval -> optional future NetSuite credit application.
- Opportunity score: **8.4/10** as a settlement implementation donor.


### microsoft/BCApps — first-party Business Central vendor-credit/application connector
- Repository: https://github.com/microsoft/BCApps
- Commit / revision: 8b8571bf54443e2d385b6cab37845f19b1380898
- Date discovered: 2026-09-22
- What actually works: Microsoft's current MIT Business Central application repository exposes the exact vendor-settlement primitives AP Recovery needs. API v2 page `applyVendorEntries` returns open Vendor Ledger Entries including vendor, document number, Applies-to ID and Remaining Amount, and PATCHing the API invokes the standard `Gen. Jnl.-Apply` vendor application path. Purchase credit memos are exposed through API v2 as a full lifecycle entity. The underlying payables code preserves Vendor Ledger Entry and Detailed Vendor Ledger Entry application history and supports explicit unapply/cancellation semantics for posted purchase credit memos.
- Evidence of implementation: `APIV2ApplyVendorEntries.Page.al`; `APIV2PurchaseCreditMemos.Page.al`; `VendorLedgerEntry.Table.al`; `DetailedVendorLedgEntry.Table.al`; `VendEntryApplyPostedEntries.Codeunit.al`; `CancelPostedPurchCrMemo.Codeunit.al`. Crucially, `APIV2ApplyVendorEntE2E.Codeunit.al` is a real API E2E test that creates a vendor and posted purchase invoice, creates a vendor payment through API v2, GETs the open ledger entry, PATCHes `{"applied":true}`, and asserts the payment now has an Applies-to ID. The broader test tree includes invoice-to-credit-memo apply/unapply coverage.
- License / reuse status: MIT. Business Central service/API access and customer tenant permissions remain separate from repository licensing.
- Useful capability: first-party proof of `VendorCredit/Payment -> VendorLedgerEntry -> application -> remaining amount -> unapplication/reversal`.
- Likely buyer: Business Central / Dynamics SMB-midmarket controller, AP manager, outsourced accounting firm.
- Painful problem solved: Recovery audits often find supplier credits but cannot prove whether a credit is still open, was actually applied, or was later unapplied/reversed.
- Fastest monetization path: Business Central Supplier Credit Recovery diagnostic using read-only vendor ledger + purchase credit memo extraction; only buyer-approved workflows would perform any writeback.
- Realistic paid pilot: Pull the top suppliers' open ledger/credit-memo population, reconcile candidate credits to originating invoices, then re-read the ledger after buyer-side application/refund to certify realized recovery.
- Estimated engineering time saved: 1-3 months of Business Central vendor-ledger/application domain discovery and connector validation.
- Important dependencies/risks: Tenant/API permissions; localization/version differences; an application event proves ERP state but not independently that the underlying recovery entitlement was correct.
- Connections: Directly strengthens AP Recovery v2's realized-settlement plane and is structurally analogous to LedgerByte's debit-note/refund state machine.
- Opportunity score: **9.6/10**.

### Acumatica/AcumaticaRESTAPIClientForCSharp — official Acumatica AP recovery extraction/application model
- Repository: https://github.com/Acumatica/AcumaticaRESTAPIClientForCSharp
- Commit / revision: 91b52dcda9fd7f2ead3c85fee5651a86222568c3
- Date discovered: 2026-09-22
- What actually works: Official MIT C# client and generated Contract-Based REST endpoint models for multiple Acumatica releases. The AP `Bill` entity maps screen AP301000 and exposes amount, balance, vendor reference, status, approval-for-payment and `Applications`. `BillApplicationDetail` maps APAdjust and exposes applied amount, balance, adjusted document type/reference and status. The AP `Check` entity maps AP302000 / `PX.Objects.AP.APPayment`, exposing payment amount, application date, vendor, status, details/history and, critically, `UnappliedBalance`; `CheckDetail` maps APAdjust with exact amount-paid and adjusted-document reference. The repository also includes actions for AP bill creation/release/reversal and payment release/void plus generated endpoint versions across releases.
- Evidence of implementation: `Endpoints/Acumatica.Default_25.200.001/Model/Bill.cs`, `BillApplicationDetail.cs`, `Check.cs`, `CheckDetail.cs`; REST client/core libraries; endpoint generator; example applications; repository tests and published NuGet packages. The generated comments bind fields to Acumatica DAC names such as `APInvoice.CuryDocBal`, `APPayment.CuryUnappliedBal` and `APAdjust.CuryAdjgAmt`.
- License / reuse status: MIT. Actual customer Acumatica API access and commercial tenant terms remain separate.
- Useful capability: read-only reconstruction of `AP Bill -> AP payment/debit adjustment -> APAdjust application -> unapplied balance`, with versioned endpoint models.
- Likely buyer: Acumatica customers in distribution, construction, manufacturing, services and midmarket finance.
- Painful problem solved: Hidden unapplied vendor balances and ambiguous payment/credit application state otherwise require bespoke Acumatica schema/API work.
- Fastest monetization path: Acumatica-specific credit/overpayment diagnostic using the Contract-Based API with no ERP mutation in the initial pilot.
- Realistic paid pilot: Export bills, AP checks/debit adjustments, application lines and vendors for a historical window; validate negative/unapplied supplier positions and certify later application/refund from re-read state.
- Estimated engineering time saved: 1-2 months for Acumatica API/entity mapping; more across multi-version support.
- Important dependencies/risks: Endpoint customization varies by customer; `Check` includes several AP document types and needs explicit semantic mapping; ERP application state is outcome evidence, not entitlement evidence.
- Connections: Adds a clean Acumatica adapter to the same realized-recovery schema used for Business Central, Oracle EBS, SAP and D365.
- Opportunity score: **9.3/10**.

### ciphersbak/psftpp — deep PeopleSoft AP/P2P extraction and exception map
- Repository: https://github.com/ciphersbak/psftpp
- Commit / revision: 86c2aa6706d0a6fcd08965905f70123a8d5240b2
- Date discovered: 2026-09-22
- What actually works: Low-attention PeopleSoft practitioner repository containing substantial production-oriented SQL across Payables and procure-to-pay. `Check_Payables.sql` maps vouchers awaiting match/approval, supplier liability exposure, prepayments, detailed AP match exceptions, match-rule overrides, voucher/payment accounting distribution anomalies, postability/close state, pending payments and pay-cycle state. Other SQL files connect PO, receipt, voucher and payment data; `VendorMaster.sql` resolves effective-dated vendor location/payment/bank configuration.
- Evidence of implementation: direct PeopleSoft tables and views including `PS_VOUCHER`, `PS_VOUCHER_LINE`, `PS_PYMNT_VCHR_XREF`, `PS_VCHR_PPAY_XREF`, `PS_AP_MTCH_EXCPTN`, `PS_AP_MTCH_RULES`, `PS_MTCH_RULE_OVRD`, `PS_VCHR_ACCTG_LINE`, `PS_VENDOR`, PO/receipt tables and payment tables. Oracle's separate UPL-licensed `oracle-quickstart/oci-peoplesoft-monitoring@72cd95ab...` independently confirms a read-only PeopleSoft sensor architecture and grants its monitoring user SELECT access to core tables including `PS_VOUCHER`, `PS_VCHR_ACCTG_LINE`, `PS_PYMNT_VCHR_XREF` and `PS_PO_HDR`.
- License / reuse status: No public license detected for psftpp; under project authorization it remains usable. Oracle's corroborating monitoring stack is UPL-1.0. Customer PeopleSoft database rights/permissions remain separate.
- Useful capability: PeopleSoft-native extraction contract for voucher/payment/prepayment/match-exception/override/accounting state.
- Likely buyer: Enterprise/public-sector/university PeopleSoft Financials AP/shared-services teams.
- Painful problem solved: PeopleSoft recovery pilots otherwise require expensive discovery of dozens of effective-dated and status-heavy AP tables before any useful analysis can begin.
- Fastest monetization path: Customer DBA executes generalized, read-only extracts; AP Recovery operates on CSVs outside PeopleSoft.
- Realistic paid pilot: Freeze one legal entity/business unit's vouchers, payment cross-references, prepayments and match exceptions, then identify open credits/overpayments and independently validate the top cases.
- Estimated engineering time saved: 1-3 months of PeopleSoft table/status discovery.
- Important dependencies/risks: Several scripts contain organization-specific filters such as `BUSINESS_UNIT LIKE '6%'` and `SETID='UNUNI'`; these must be parameterized and independently reconciled to the customer's version/config. Repository is older, so use current customer metadata and Oracle references before treating every field/status as authoritative.
- Connections: Adds an enterprise PeopleSoft wedge parallel to Oracle EBS extraction; Oracle's official monitoring stack demonstrates a safe read-only deployment pattern.
- Opportunity score: **9.1/10**.

### pgahq/finance-agent — tested Workday Supplier Invoice SOAP integration substrate
- Repository: https://github.com/pgahq/finance-agent
- Commit / revision: bcacb4851c43b779edbb2c9554044dd20eddf52e
- Date discovered: 2026-09-22
- What actually works: One-star, actively maintained TypeScript/AWS application with a very large Workday SOAP integration layer and extensive tests. It performs OAuth-authenticated `Get_Supplier_Invoices` by Workday WID, can fetch supplier invoices with attachments, resolves suppliers/companies/POs/worktags, reads Workday custom reports, and implements Supplier Invoice submit/update workflows with detailed validation-repair logic. `src/__tests__/workday.test.ts` is over 200KB and exercises the Workday wrapper heavily.
- Evidence of implementation: `src/lib/workday.ts`, `get-supplier-invoice.ts`, `TEST-SOAP-API.md`, supplier/PO caches and large Workday tests. The tests assert the exact `Get_Supplier_Invoices_Request -> Supplier_Invoice_Reference -> WID` structure and parsed invoice numbers. IBM's Apache-2.0 Maximo-Workday connector repository independently documents a production integration pattern where final approved/paid Workday supplier invoices are fetched with `Get_Supplier_Invoices`; because Workday does not expose date-based delta extraction for that call, IBM uses a sliding 90-day paging/dedupe window.
- License / reuse status: AGPL-3.0-or-later. IBM corroborating integration documentation/mappings are Apache-2.0. Workday API/customer tenancy terms remain separate.
- Useful capability: robust Workday invoice/document ingestion plus a known incremental-extraction workaround.
- Likely buyer: Workday Financial Management AP teams.
- Painful problem solved: Workday invoice ingestion and attachment handling are difficult enough that the ERP connector can dominate pilot engineering time.
- Fastest monetization path: Read-only Workday invoice/PO/document adapter feeding AP Recovery; avoid write operations for the initial offer.
- Realistic paid pilot: Pull a bounded historical Supplier Invoice population plus supporting documents, reconcile to supplier statements/POs, and use buyer-provided settlement data to prove any recovery.
- Estimated engineering time saved: 1-3 months of Workday SOAP/auth/request/response and attachment integration work.
- Important dependencies/risks: This codebase is designed for invoice creation/enrichment, not recovery settlement; Workday payment/credit allocation proof needs a separate current readback source. AGPL obligations matter if directly incorporated into a hosted proprietary product.
- Connections: Strong ingestion component behind Invoice Lens/ReconForge; IBM's sliding-window pattern supplies the missing incremental-read strategy.
- Opportunity score: **8.9/10**.

### troystaylor/SharingIsCaring — functioning Coupa invoice connector with credit-note-ready API surface
- Repository: https://github.com/troystaylor/SharingIsCaring
- Commit / revision: 836ba71d13bec220acac4c945f68300bf5f161c3
- Date discovered: 2026-09-22
- What actually works: Active enterprise connector collection containing a Coupa Power Platform custom connector/MCP implementation. `Coupa/script.csx` implements runtime `list_invoices` and `get_invoice` tools against `/api/invoices` with status, invoice-number and supplier filters, alongside purchase-order/supplier operations. The Swagger and OAuth properties define Coupa invoice read/write scopes.
- Evidence of implementation: `Coupa/script.csx`, `Coupa/apiDefinition.swagger.json`, `Coupa/apiProperties.json`, `Coupa/readme.md`. The separate zero-star `api-evangelist/coupa@ddd4c1d...` current API profile provides a useful normalized schema/reference: invoice `document-type` includes Invoice/Credit Note; credit notes carry `is-credit-note`, `original-invoice-number`, `original-invoice-date`, `credit-reason` and credit variance, while invoice records expose `paid`, `payment-date`, supplier, status and line items.
- License / reuse status: No public license detected for SharingIsCaring or the API-Evangelist profile; project authorization applies to repository content. Coupa's actual API/service is proprietary and separately governed by customer access/terms.
- Useful capability: Coupa invoice/credit-note extraction and original-invoice linkage without inventing the resource model.
- Likely buyer: Coupa BSM enterprise AP/procurement teams.
- Painful problem solved: Linking supplier credit notes back to original invoices and knowing whether associated invoices are paid/disputed/exported is a prerequisite to recovery but is easy to lose across ERP/procurement boundaries.
- Fastest monetization path: Coupa read-only credit-note diagnostic using customer-authorized API credentials; export canonical invoice/credit relationships into AP Recovery.
- Realistic paid pilot: Extract supplier invoice and credit-note population for the top vendors, link credits to originals, reconcile against downstream ERP/payment evidence, and flag credits with no proven realization.
- Estimated engineering time saved: 3-6 weeks of Coupa connector/schema discovery.
- Important dependencies/risks: Coupa's `paid/payment-date` is useful corroboration but is not by itself proof that a specific credit note was economically applied; downstream ERP/remittance evidence remains required. API schemas/profile provenance should be checked against the customer's live Coupa version.
- Connections: Completes another major procurement front-end feeding the Supplier Credit Recovery case ledger.
- Opportunity score: **8.7/10**.
