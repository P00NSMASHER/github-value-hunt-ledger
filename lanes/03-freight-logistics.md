# Freight & Logistics

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
### DominicFinn/open_tms
- Repository: https://github.com/DominicFinn/open_tms
- Commit / revision: 93d8c2b8ff78373ff69bb7ea546743e4703628b1
- Date discovered: 2026-09-19
- What it contains: Active TypeScript transport-management platform with React frontend, Fastify backend, Prisma/PostgreSQL, CQRS/event-driven domain modeling, shipment/customer/carrier/order operations, IoT tracking, EDI work, reporting, deployment templates, and a shared TMS/WMS core.
- Why it matters: This is a substantial logistics application substrate rather than a demo. Its current roadmap shows active September 2026 work on EDI ingestion, carrier connectivity, shipment quality, tenancy, reporting, deployment, and WMS separation.
- Commercial possibilities: Base layer for a freight-audit/recovery product, shipper operations portal, carrier performance product, or logistics workflow system when paired with document extraction and audit rules.
- Build-time savings: Very high. It can eliminate much of the commodity work around logistics domain models, API/UI scaffolding, tenancy, deployment, shipment workflows, and carrier/EDI foundations.
- Evidence inspected: README.md; package.json with build/test/lint workspaces; roadmap.md reviewed September 2026 describing EDI inbound, carrier connectivity, reporting, platform hardening, and TMS/WMS split.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT terms.
- Scores:
  - Technical value: High
  - Commercial value: High when combined with a specific ROI product
  - Rarity: Medium-High
  - Completeness: High but still pre-release/active development
  - Build-time saved: Very High
  - Data advantage: Low by itself
  - High-ticket potential: High
- Next action: Inspect shipment/rate/EDI domain models and identify the shortest path to add invoice/rate-contract verification plus evidence-backed exception reporting.

### kodekinetics79/opstrax-enterprise-build
- Repository: https://github.com/kodekinetics79/opstrax-enterprise-build
- Commit / revision: fec2ba1432d6f8b4ba4c48be3d58e7e096819045
- Date discovered: 2026-09-19
- What it contains: A zero-star but production-oriented logistics platform with a particularly deep detention-recovery subsystem. The implemented flow consumes geofence Entry/Exit events through a one-time consumed-event ledger, attributes dwell to the matching job/driver/customer, applies an appointment-aware billable clock using later-of(appointment, arrival), sends pre-expiry notices, resolves customer-vs-tenant rule cards, prices detention fail-closed, stores immutable evidence bundles with SHA-256 linkage, requires AP-style approval before billing, creates exactly one detention job charge, blocks double approval, and exposes shareable evidence packets. The repo also contains PostgreSQL migrations, .NET services, production deployment tooling, and integration tests that exercise the real event-to-charge path.
- Why it matters: This is unusually complete domain logic for converting physical-truth telemetry into evidence-grade money recovery. It addresses the hard parts that generic freight-audit products usually lack: bounce/re-entry deduplication, appointment anchoring, evidence provenance, notice timing, fail-closed pricing, claim-window constraints, approval gates, and idempotent billing. That architecture could materially strengthen a freight-invoice audit/recovery product by validating detention/accessorial charges against physical evidence instead of trusting invoice text alone.
- Commercial possibilities: Clean-room blueprint for an evidence-backed detention recovery module sold to carriers/brokers on contingency or shared savings; or, inverted for shippers, a detention/accessorial validation layer that verifies whether billed detention is supported by geofence, appointment, notice, and rule-card evidence before payment. The evidence-share packet could also support dispute automation and recovery workflows.
- Build-time savings: High even without code reuse. The inspected implementation/test suite collapses months of domain discovery around event pairing, pricing state machines, notice requirements, evidence hashing, approval controls, and dispute-ready artifacts; estimated 3-6 months of clean-room design/edge-case work for a focused detention module.
- Evidence inspected: Repository metadata and latest main commit; `backend-dotnet/Services/DetentionService.cs` showing consumed-event-ledger semantics, job attribution, later-of appointment/arrival clocking, pre-expiry notices, rule-card selection, fail-closed pricing, rounding and caps; `backend-dotnet.Tests/DetentionApprovalPostgresTests.cs` exercising the real geofence-event -> dwell -> price -> approval pipeline, immutable evidence SHA linkage, double-approve prevention, missing-reference gate, audited override, public share token, and recovery funnel; detention schema migration/search evidence; deployment helper commit. No secrets or private data were collected.
- License / rights: No `LICENSE` file at the inspected revision (GitHub contents lookup returned 404; repository metadata reports no license). Copyrighted source is therefore inspect/learn only unless permission is later established.
- Reuse classification: Inspect / learn / clean-room implementation only.
- Scores:
  - Technical value: 9.5/10
  - Commercial value: 9.3/10
  - Rarity: 9.6/10
  - Completeness: 9.1/10
  - Build-time saved: 8.8/10
  - Data advantage: 9.1/10
  - High-ticket potential: 9.4/10
- Next action: Clean-room implement only the detention evidence core beside the existing freight-audit stack: geofence/dwell evidence schema, appointment-aware clock, rule-card versioning, immutable evidence hash, approval gate, and dispute packet; validate it against synthetic geofence/appointment/invoice cases before any customer pilot.

### wearewarp/warp-tools
- Repository: https://github.com/wearewarp/warp-tools
- Commit / revision: 0646e7491771b7f5ddd2934fcac6e8ecb566c7fd
- Date discovered: 2026-09-19
- What it contains: A one-star MIT-licensed TypeScript monorepo containing multiple standalone freight/logistics applications rather than a single demo: carrier management, invoice/payment tracking, document vault, dispatch/load board, dock appointment scheduling, driver settlements, rate management, a mini-TMS, customer portal, fleet maintenance, and smaller operational tools for detention/demurrage, rate confirmations, freight parsing, load profitability, IFTA, deadhead, and settlements. The inspected rate-management implementation has real SQLite/Drizzle schemas and migrations for lanes, carrier rates, effective/expiry dates, spot-vs-contract rate types, customer tariffs with contract references, RFQs, responses, awards, and multiple rate bases (`per_mile`, `flat`, `per_cwt`, `per_pallet`). The invoice tracker separately models invoice line types including freight, fuel surcharge, detention, accessorial and lumper charges; invoice partial-payment states; carrier payments; payments received; and load-to-invoice/payment linkage. The detention tool contains implemented free-time, hourly-rate, daily-cap and tiered demurrage calculations rather than a static UI.
- Why it matters: This fills a different gap from `open_tms`. `open_tms` is the stronger general TMS substrate, while Warp Tools provides a permissively licensed set of small, separable operational modules that map unusually well to the supporting control plane of a freight-audit/recovery product: contract/rate-card storage, tariff version dates, invoice/payment state, charge categorization, detention math, document handling and rate-confirmation workflows. Because the modules are standalone and SQLite-first, they are attractive for rapidly composing a pilot without adopting an entire TMS architecture.
- Commercial possibilities: Directly reuse/adapt the rate-management + invoice/payment + document/detention modules as the back-office shell for an evidence-first freight audit/recovery pilot; build a self-hosted shipper audit appliance; or use the rate/RFQ schemas as the customer-authorized contractual-truth layer feeding deterministic invoice checks. A particularly practical combination is Warp rate/tariff storage + the existing evidence-first audit stack, with `opstrax` concepts supplying physical evidence for detention disputes.
- Build-time savings: High. For a narrow freight-audit pilot, the inspected modules can plausibly eliminate 2-4 months of commodity CRUD/schema/UI work around rates, tariffs, invoice/payment states, charge categorization, RFQs, detention calculations, deployment and local persistence. Savings are lower if the team already commits fully to `open_tms`, so the best use is selective component reuse rather than adopting both whole platforms.
- Evidence inspected: Repository metadata and exact latest commit; root `README.md` with independently runnable apps and Docker/SQLite setup; actual `LICENSE`; `apps/rate-management/src/db/schema.ts` showing lane, carrier-rate, customer-tariff, RFQ and RFQ-response models with effective/expiry dates and contract refs; Drizzle config/migration/seed evidence for rate management; `apps/invoice-tracker/src/db/schema.ts` showing invoice/payment/load state plus freight/fuel/detention/accessorial/lumper line types; `apps/detention-calculator/src/app/page.tsx` showing implemented detention free-time/hourly-cap calculations and demurrage free-day/tier calculations; rate-confirmation/load-profitability source showing fuel surcharge and accessorial arithmetic. No obvious automated test suite surfaced in repository code search, which is a validation limitation and lowers the completeness score.
- License / rights: MIT License at the inspected revision, Copyright (c) 2026 Warp. The license explicitly permits use, modification, distribution, sublicensing and sale subject to retaining the copyright/permission notice. No third-party carrier rate tables or proprietary tariff content were relied on as reusable data in this finding.
- Reuse classification: Directly reusable subject to MIT terms.
- Scores:
  - Technical value: 9.0/10
  - Commercial value: 8.9/10
  - Rarity: 9.0/10
  - Completeness: 8.6/10
  - Build-time saved: 9.2/10
  - Data advantage: 4.5/10
  - High-ticket potential: 8.7/10
- Next action: Prototype the audit control plane by reusing only the Warp rate/tariff and invoice/payment schemas around the existing freight-audit rules; add explicit rate-card version provenance and recovery-evidence fields, then run the current synthetic audit/payment benchmarks before deciding whether any additional Warp UI modules are worth importing.


### bwllaming/matrix-paper
- Repository: https://github.com/bwllaming/matrix-paper
- Commit / revision: current main inspected 2026-09-19 (exact tree inspected via GitHub; use latest pinned commit before reuse).
- Date discovered: 2026-09-19
- What it contains: MIT-licensed open research dataset of anonymized UBL invoice documents prepared in collaboration with Kuehne+Nagel for business-document understanding. README explicitly states sensitive identifiers and structured data were pseudonymized/randomized while preserving document structure; includes invoice XML and ground-truth transport references.
- Why it matters: This is one of the rare clearly intentional, anonymized, real-world logistics invoice corpora found on GitHub. It is useful for validating invoice parsing, EN16931/UBL normalization, reference extraction and evidence provenance on documents derived from real operational material.
- Commercial possibilities: Use as a safe real-world extraction/normalization benchmark for the freight recovery stack; do not treat it as a recovery corpus because matching contract/rate authority, shipment truth and settlement records are not present.
- Build-time savings: Weeks of benchmark-data acquisition/cleaning for real-world invoice structure.
- Evidence inspected: Repository README; MIT license metadata; data/ground_truth.json; representative UBL invoice XML.
- License / rights: Repository states MIT. Dataset publication is explicit and anonymization is described by the authors. Preserve license/citation terms.
- Reuse classification: Directly reusable for benchmarking subject to MIT/citation obligations; not sufficient to assert recoverable dollars.
- Scores:
  - Technical value: 8.5/10
  - Commercial value: 7.5/10
  - Rarity: 9.2/10
  - Completeness: 6.5/10 for freight audit, high for invoice extraction
  - Build-time saved: 7.5/10
  - Data advantage: 9.0/10
  - High-ticket potential: 5.0/10 as a dataset; higher as stack validation
- Next action: Import a representative subset into the ChatGPT Freight Recovery benchmark library and run EN16931/UBL extraction/reference-linking tests. Do not label any variance as recoverable without matching rate authority and shipment evidence.

### RojaJoseph/Trucking-Management-System — signed rate-confirmation samples
- Repository: https://github.com/RojaJoseph/Trucking-Management-System
- Commit / revision: current main inspected 2026-09-19.
- Date discovered: 2026-09-19
- What it contains: A TMS rate-confirmation extraction project whose repository tree includes signed broker PDFs named for Allen Lund, BlueGrace and Stevens Transport; README describes them as “three real document formats.”
- Why it matters: Potentially valuable real-world layout coverage for rate-confirmation extraction.
- Commercial possibilities: None unless provenance/permission is established; do not use the customer/broker paperwork itself for commercial benchmarking or audit claims.
- Build-time savings: Could inform layout coverage only after a lawful/permissioned sample is established.
- Evidence inspected: README and repository tree/filenames only. The signed PDFs were intentionally not opened or imported because the repo provides no clear anonymization/consent statement and no repository license.
- License / rights: No LICENSE found in repository metadata at inspection. Public visibility does not establish reuse rights. Real signed broker/customer documents may contain confidential commercial terms or personal/business identifiers.
- Reuse classification: Quarantined / do not import or reproduce. Inspect high-level repository structure only unless explicit publication rights or anonymization are established.
- Scores:
  - Technical value: 6.0/10
  - Commercial value: 0/10 until rights/provenance established
  - Rarity: 8.0/10
  - Completeness: 3.0/10 for our use
  - Build-time saved: 0/10 under current rights
  - Data advantage: 0/10 usable
  - High-ticket potential: 0/10 as-is
- Next action: Prefer clearly licensed/anonymized research corpora or customer-provided documents. Do not revisit these signed PDFs unless the repository later adds an explicit license/provenance/anonymization statement.


### siddhartha-devops/Cointab-data-analysis- — courier billing verification benchmark
- Repository: https://github.com/siddhartha-devops/Cointab-data-analysis-
- Commit / revision: 393cf592000d0a136b44b67b4c107d6d6507ff15
- Date discovered: 2026-09-19
- What it contains: Public Cointab Software Private Limited Data Analyst hiring challenge implementing a “real-life scenario” for an anonymized ecommerce Company X. The package links order/SKU truth, warehouse-to-customer pincode zones, courier billed weights/zones/amounts, and a zone/weight-slab rate card at order/AWB grain. It is therefore a rare compact end-to-end invoice/rate/operational-truth benchmark, although public evidence does not establish that the rows are a live customer ledger.
- Why it matters: It exercises the exact core freight-recovery invariant we need: reconstruct contractual/expected cost from customer-side operational truth and compare it against billed carrier cost. Unlike many freight demos, the dataset contains independent weight/zone truth rather than only invoice rows.
- Commercial possibilities: Internal benchmark for the freight-recovery engine; use it to validate deterministic rating, zone/weight reconciliation, evidence-linked variance reporting and abstention. Do not market its discrepancies as real customer recoveries.
- Build-time savings: Medium-high for benchmark/evaluation work; eliminates weeks of constructing a realistic order-to-invoice reconciliation corpus.
- Evidence inspected: Challenge README; rates.csv; SKU master; pincode-zone mapping; order report; courier invoice; author final output; author solution code; independent recomputation performed 2026-09-19.
- Independent recomputation: 124 orders audited; 22 correctly charged; 79 billed above independently recomputed expected charge; 23 billed below expected; aggregate candidate overbilling INR 4,426.60; aggregate underbilling INR 575.10; net billed-above-expected INR 3,851.50; 65 zone mismatches; 60 weight-slab mismatches. Largest single billed-above-expected variance observed was INR 342.50.
- License / rights: Repository metadata did not expose a clear LICENSE file at inspection despite the challenge being publicly distributed. Treat raw files/code as inspect/evaluate only unless source rights are clarified. Derived independently recomputed factual metrics may be retained internally with provenance.
- Reuse classification: Benchmark/reference only under current rights evidence; do not redistribute source package.
- Scores:
  - Technical value: 8.7/10
  - Commercial value: 8.3/10
  - Rarity: 9.0/10
  - Completeness: 9.1/10 as a parcel/courier billing benchmark
  - Build-time saved: 8.2/10
  - Data advantage: 8.8/10
  - High-ticket potential: 6.5/10 directly; high as validation substrate
- Next action: Use the derived benchmark as a regression gate for the Freight Recovery v4 canonical model, then keep searching for an explicitly anonymized real operational package containing invoice + contract/rate authority + shipment/BOL/POD from the same transaction.


### warpfreight/warp-agent-mcp
- Repository: https://github.com/warpfreight/warp-agent-mcp
- Commit / revision: 1850556032b465a0c24839e28564687462067323
- Date discovered: 2026-09-19
- What it contains: MIT-licensed, actively maintained MCP/API client for Warp's production freight network. Source and manifest expose live quote, multi-carrier LTL option, booking, tracking/event history, lane history, booking history, quote history, delivered-shipment invoice retrieval, and shipment-document retrieval including BOL/POD/customs. The client implementation calls authenticated production freight invoice/document endpoints, while tests deliberately avoid real booking/charges. Its read-only freight-review workflow requires explicit source labels, comparability evidence, preserves negative savings, rejects duplicate shipment IDs, excludes unknown/mismatched requirements, separates quote opportunities from final-invoice differences, and explicitly refuses to call a difference realized savings.
- Why it matters: This closes a major integration gap in Freight Recovery v4. For a customer-authorized Warp account, one connector can provide the transactional chain around a shipment—quote/booking history, tracking events, invoice, and BOL/POD documents—without asking the customer to manually export each artifact. It does not replace contractual truth for arbitrary carriers, but it can supply live source evidence and a model for other TMS/carrier connectors.
- Commercial possibilities: Authorized live-data connector for freight-audit acceptance testing; compare accepted Warp quote to final invoice and delivery evidence; audit accessorial/supporting-document consistency; use quote/book/document/invoice lineage as one reference integration for a broader multi-carrier recovery service.
- Build-time savings: High. Likely saves 1-3 months of production-grade quote/booking/document/invoice integration, auth/error handling, operator workflow, and evidence-comparison plumbing for Warp-connected customers.
- Evidence inspected: README; machine-readable manifest; exact latest commit; src/client.ts invoice/document/quote/book paths; src/tools.ts get_invoice/get_documents registration; src/workflows.ts evidence/comparability rules; test/e2e.mjs; test/freight-review.mjs; test/refund.mjs. No live shipment was booked and no customer data was accessed.
- License / rights: MIT repository code. Live Warp/customer shipment, quote, invoice and document data remain account-authorized customer data governed separately by Warp/customer terms and privacy obligations. Access requires authentication. Do not treat live market quotes as contract entitlement or historical invoice differences as realized recovery.
- Reuse classification: Directly reusable subject to MIT terms for software; live data only with customer authorization.
- Scores:
  - Technical value: 9.4/10
  - Commercial value: 9.5/10
  - Rarity: 9.5/10
  - Completeness: 9.1/10 for one-network transaction evidence
  - Build-time saved: 9.0/10
  - Data advantage: 8.5/10 when customer-authorized
  - High-ticket potential: 9.3/10 as a connector inside freight assurance/recovery
- Next action: Add a Warp adapter to the v4 canonical intake contract mapping quote_id/order_id/shipment_id → accepted quote → invoice → events → BOL/POD. First validation must be read-only on an authorized account: retrieve an already-delivered shipment and prove exact source lineage without booking, disputing, paying, or contacting any carrier.


### shafeehhecker/HaulSync
- Repository: https://github.com/shafeehhecker/HaulSync
- Commit / revision: 0d6fd34b21c1e09309ea155cc29ca06c2242e307
- Date discovered: 2026-09-19
- What it contains: MIT-licensed self-hosted logistics operations shell with a real RFQ/quote award model, quote-linked shipments, tracking events, authenticated POD upload/storage, and shipment-linked invoice records/statuses. The Prisma schema gives a clean RFQ → awarded quote → shipment → POD → invoice lineage.
- Why it matters: Useful rights-clean workflow/data-model donor for preserving accepted commercial intent and delivery evidence around a freight audit. However, source inspection does NOT support the README's stronger “invoice reconciliation” claim: the inspected invoice route creates/updates invoice CRUD records and does not compare billed freight against the awarded quote, POD, or contract.
- Commercial possibilities: Reuse selected RFQ/award/shipment/POD schema and UI concepts as a lightweight customer evidence portal around Freight Recovery v5; do not adopt it as the audit engine.
- Build-time savings: Medium, roughly 3-6 weeks for RFQ/quote/shipment/POD/invoice workflow scaffolding if needed.
- Evidence inspected: README; MIT license metadata; backend/prisma/schema.prisma; backend/src/routes/rfq.js; backend/src/routes/shipments.js; backend/src/routes/invoices.js.
- License / rights: MIT for repository code; customer operational data remains separately controlled.
- Reuse classification: Directly reusable workflow shell subject to MIT terms; README invoice-reconciliation claim downgraded as unimplemented in inspected backend.
- Scores:
  - Technical value: 7.4/10
  - Commercial value: 7.2/10
  - Rarity: 6.8/10
  - Completeness: 6.5/10
  - Build-time saved: 7.2/10
  - Data advantage: 3.0/10
  - High-ticket potential: 7.0/10 when combined with the v5 audit core
- Next action: Borrow only the accepted-quote→shipment→POD lineage pattern if Open TMS/Warp do not already cover it more cleanly. Do not spend search time on its invoice module unless new reconciliation code lands.

### clickpost-tech/clickpostERP
- Repository: https://github.com/clickpost-tech/clickpostERP
- Commit / revision: 7808a6dbc25a4698acff7acd14c1a8704777f0c7
- Date discovered: 2026-09-19
- What it contains: MIT ERPNext integration for ClickPost with carrier master sync, carrier recommendation/selection, shipment creation, AWB registration, shipment sync, tracking webhooks, and shipment-to-sales-invoice linkage. The implementation contains meaningful B2B shipment orchestration and fallback-to-alternate-carrier behavior.
- Why it matters: Potential ERP-side connector pattern for getting carrier allocation, AWB and tracking truth into a recovery product. Source inspection did not locate implemented freight invoice reconciliation despite the README saying the integration covers it; the inspected code is centered on shipment creation/tracking rather than billed-vs-expected audit.
- Commercial possibilities: ERPNext/ClickPost intake connector or clean integration reference for shipment/AWB/tracking evidence; not a replacement for deterministic rerating or invoice audit.
- Build-time savings: Medium for ERPNext/ClickPost integration, low for the core recovery engine.
- Evidence inspected: README; MIT license metadata; APIs carrier.py and shipment.py; custom_scripts/shipment.py; shipment webhook; sales-invoice linkage. Most generated doctype test files are scaffolding rather than substantive audit tests.
- License / rights: MIT repository code; ClickPost API/customer data terms are separate.
- Reuse classification: Directly reusable integration plumbing subject to MIT terms; invoice-reconciliation capability unverified/unimplemented in inspected source.
- Scores:
  - Technical value: 7.6/10
  - Commercial value: 7.3/10
  - Rarity: 7.2/10
  - Completeness: 7.0/10 for shipment integration, low for audit
  - Build-time saved: 7.5/10 for ERPNext connector work
  - Data advantage: 5.0/10 with authorized customer integration
  - High-ticket potential: 7.2/10 as an enterprise connector
- Next action: Keep as an optional ERPNext/ClickPost adapter reference. Do not promote into the v5 core until an actual invoice/billing reconciliation path is implemented and tested.
