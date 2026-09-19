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
