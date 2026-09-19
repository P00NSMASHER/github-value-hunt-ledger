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


### wearewarp/warp-tools — permissive freight-operations shell
- Repository: https://github.com/wearewarp/warp-tools
- Commit / revision: 0646e7491771b7f5ddd2934fcac6e8ecb566c7fd
- Date discovered: 2026-09-19
- What it contains: MIT monorepo with functioning standalone logistics apps for invoice/payment tracking, document vault, rate management/RFQs, shipment management/Mini-TMS, carrier management, load dispatch, detention/demurrage calculation, rate-confirmation generation and other operations. Source inspection confirmed concrete schemas/APIs rather than README-only claims: invoice tracker has freight/fuel/detention/accessorial/lumper line types and carrier-payment status including disputed; rate management has lane/carrier contract+spot rates, effective/expiry dates, rate source, customer tariffs, RFQ responses and awarded rates; Mini-TMS has quote→booked→dispatched→in_transit→delivered→invoiced→paid→closed plus BOL/POD/rate-confirmation/invoice document linkage; document vault tracks load/carrier/customer-linked BOL/POD/rate-confirmation/invoice/weight/lumper evidence.
- Rare / undernoticed value: Only ~1 star at inspection despite a broad, coherent, modern freight back-office surface. It materially reduces CRUD/UI/schema work around the recovery engine and comes from the same Warp ecosystem as the live-evidence connector.
- Likely buyer / user: Internal operators of the freight-recovery service, smaller shippers/3PLs wanting a self-hosted evidence workspace, or an embedded operations layer around the audit/recovery core.
- Painful problem: The audit math is only one part of the product; teams also need rate/RFQ history, load identity, document completeness, invoice/payment state and an operator queue. Rebuilding all of that from scratch would waste months.
- Monetization mechanism: Use as the internal/operator shell supporting paid audits, continuous assurance and recovery case management rather than selling the generic tools themselves.
- Build-time / data advantage: Likely 2–5 months saved across freight-specific UI, schemas, REST routes and operational workflows.
- Evidence inspected: Root README/architecture; MIT metadata; invoice-tracker README/schema/seed; rate-management README/schema/seed; shipment-management README/schema; document-vault schema; detention calculator README.
- Important limitation: The apps are primarily standalone with their own SQLite databases. The architecture says they are designed to connect/share a database, but integration is not complete. They do not themselves implement the deterministic billed-vs-entitled recovery engine or settlement attribution.
- License / rights: MIT for repository code. Any live customer/carrier data remains separately controlled.
- Reuse classification: Directly reusable subject to MIT terms, best as UI/workflow/schema donor.
- Scores:
  - Technical value: 9.0/10
  - Commercial value: 8.8/10
  - Rarity: 9.1/10
  - Completeness: 8.8/10 as operations shell
  - Build-time saved: 9.1/10
  - Data advantage: 5.5/10
  - High-ticket potential: 8.6/10 when combined with recovery core
- Combination opportunities: Freight Recovery v6 + Warp Agent MCP live evidence + Warp Tools operator shell. Map awarded RFQ/carrier rate → shipment → BOL/POD/rate-confirmation/invoice → finding → dispute → carrier payment/credit.
- Next action: Do not merge all apps blindly. Extract the shared canonical entities/UX needed for recovery: rate_authority, shipment, evidence_document, carrier_invoice, finding, dispute, settlement and recovery_attribution. Preserve the fail-closed audit engine as a separate service.

### MicrosoftDocs/dynamics-365-unified-operations-public — native freight-reconciliation semantics
- Repository: https://github.com/MicrosoftDocs/dynamics-365-unified-operations-public
- Commit / revision: b81257fa8c6f2e0599f477653b740f4565649276
- Date discovered: 2026-09-19
- What it contains: Current CC-BY-4.0 Dynamics 365 Supply Chain Management documentation defining native TMS freight reconciliation: system-generated freight bill/estimated cost versus carrier invoice, manual and automatic matching, mandatory/optional match fields, tolerance limits, audit masters, overpayment/underpayment reason codes, split reconciliation reasons, approval and posting. Related docs also describe TMS rate engines and small-parcel carrier API integration.
- Rare / undernoticed value: This is not another freight-audit codebase; it is the documented behavior of a major ERP/TMS buyer environment. It tells us what an enterprise customer already has and therefore what our product must complement rather than duplicate.
- Likely buyer / user: Dynamics 365 shippers, AP/freight-payment teams, 3PLs and implementation partners.
- Painful problem: Native reconciliation can match freight bills and invoices, but buyers still need independent assurance, historical leakage testing, evidence quality, cross-system/carrier normalization, benchmark scoring and recovery attribution.
- Monetization mechanism: Sell an external acceptance-test/assurance layer that exports/imports D365 freight bills/invoices/reason codes, independently rerates them, identifies missed/false findings and tracks incremental realized recoveries.
- Build-time / data advantage: Saves weeks of reverse-engineering enterprise freight-payment semantics and gives a concrete integration/compatibility target.
- Evidence inspected: Current Microsoft freight-reconciliation documentation, freight bill type/audit master/tolerance/reason-code behavior, auto-match example and current TMS rate-engine/small-parcel docs.
- License / rights: Documentation repository is CC-BY-4.0. Dynamics product/APIs and customer data remain governed separately.
- Reuse classification: Directly reusable documentation/reference with attribution; implementation should be independently built around supported exports/APIs.
- Why non-obvious: The strongest commercial implication is negative: do not pitch “invoice matching” alone to D365 customers because it is already native. Pitch independent accuracy/recovery assurance and evidence.
- Scores:
  - Technical value: 8.3/10
  - Commercial value: 9.2/10
  - Rarity: 8.6/10
  - Completeness: 9.0/10 for D365 reconciliation behavior
  - Build-time saved: 7.8/10
  - Data advantage: 4.0/10
  - High-ticket potential: 9.2/10 as enterprise wedge
- Combination opportunities: Freight Recovery v6 + D365 export/API adapter + recovery-attribution ledger. Preserve D365 reason codes/tolerances but independently score dollar-weighted recall/precision and missed recovery.
- Next action: Define a D365-compatible canonical mapping for freight_bill, carrier_invoice, match_reason, tolerance, audit_master, load/shipment, expected charge and variance. A customer pilot should demonstrate value *after* native reconciliation, not duplicate it.


### EasyPost/easypost-python — parcel claim/refund recovery adapter
- Repository: https://github.com/EasyPost/easypost-python
- Commit / revision: d0dd20d900e38ee954af6e6c1c4ea2aaba96cda6
- Date discovered: 2026-09-19
- What it contains: Official MIT Python SDK from EasyPost. Source inspection verified first-class Claim create/list/retrieve/cancel operations and Shipment Refund create/list/retrieve/pagination, with VCR-backed tests exercising real API request/response shapes. Current EasyPost documentation defines claim lifecycle statuses including submitted, in_review, approved, approved_partial, rejected, cancelled and needs_action, plus evidence attachments and requested/approved amounts. Shipping refunds expose submitted/refunded/rejected states and shipment/tracking linkage.
- Rare / undernoticed value: It supplies a tested recovery-action and recovery-state adapter for parcel shipments rather than only audit/detection logic. EasyPost's Carrier Claims Program also publicly describes automated eligible carrier claims and successful reimbursements applied as account credits.
- Likely buyer / user: Parcel shippers already using EasyPost; e-commerce/fulfillment operations; later parcel-recovery expansion of the freight assurance product.
- Painful problem: Even a correct parcel finding is not money until a valid claim/refund is submitted, adjudicated and credited. This connector provides concrete state transitions and IDs for that downstream lifecycle.
- Monetization mechanism: Continuous parcel assurance plus optional success fee on confirmed credits/refunds. Keep this as an expansion path rather than the initial LTL/FTL dependency.
- Build-time / data advantage: Likely saves several weeks of parcel refund/claim API plumbing, pagination/state handling and tests.
- Evidence inspected: Official GitHub metadata/MIT license; claim_service.py; refund_service.py; test_claim.py; test_refund.py; current EasyPost claims/refunds/carrier-claims documentation.
- Important limitations: Claims/refunds are available only within EasyPost-supported/account-authorized workflows and have carrier/program eligibility rules. A refund or approved claim is not equivalent to a freight invoice overcharge recovery. Parcel billing retrieval remains a separate problem.
- License / rights: MIT SDK. API/customer/shipment data and carrier program terms remain separate.
- Reuse classification: Directly reusable subject to MIT terms; customer/API use only with authorization.
- Scores:
  - Technical value: 8.5/10
  - Commercial value: 8.3/10
  - Rarity: 8.0/10
  - Completeness: 8.7/10 for supported parcel recovery actions
  - Build-time saved: 8.0/10
  - Data advantage: 7.0/10 with authorized accounts
  - High-ticket potential: 7.8/10 as parcel expansion
- Combination opportunities: Freight Recovery assurance core + EasyPost claim/refund state adapter + recovery-attribution ledger; map approved/credited outcomes to realized recovery only after account credit/payment proof.
- Next action: Keep parcel as phase 2. Build initial LTL/FTL acceptance-test product first; add EasyPost when a customer has an authorized EasyPost shipment population.


### aiparallel0/freight-audit — rights-clean freight benchmark + audit-engine donor
- Repository: https://github.com/aiparallel0/freight-audit
- Commit / revision: e7869162cf9cb23f6d520a0cd71f87cf973d8c28
- Date discovered: 2026-09-19
- What it contains: MIT-licensed, zero-star freight-audit codebase with a tested rate-confirmation + carrier-invoice + POD matching engine, integer-cents money handling, client-configurable rules/vocabulary/layouts, OCR pipeline, synthetic freight-document generator, benchmark scorer, API/review tooling and explicit PII-free sample loads. The five committed scenarios include a clean invoice, linehaul overcharge + duplicate fuel, unauthorized liftgate, billed detention unsupported by POD timestamps, and POD-proven detention that was not billed.
- Rare / undernoticed value: The benchmark design is unusually honest. Its docs report 100% field/total/line-amount accuracy only on its known synthetic freight layout, but an out-of-distribution CORD-v2 test produced about 40% raw total legibility, 8% generic-layout total extraction and 4% line-amount recall. Rather than hiding this, the repository treats format-specific layout calibration and OCR-provider substitution as required production work. That failure data is more valuable to v7 than a polished demo claiming generic OCR is solved.
- Likely buyer / user: Internal benchmark/QA team for Freight Recovery v7; freight-audit vendors and shippers validating extraction/matching behavior.
- Painful problem: A freight-assurance product can have correct rerating logic and still invent dollars if OCR/document extraction silently accepts bad fields. This repo supplies a reproducible way to measure that layer and concrete freight challenge cases with rate-confirmation/invoice/POD truth.
- Monetization mechanism: Not a standalone business recommendation. Use its benchmark corpus and evaluation patterns to harden the paid Freight Audit Acceptance Test and demonstrate measured extraction/audit reliability before customer pilots.
- Build-time / data advantage: Likely 1–3 months saved across freight-specific sample generation, image rendering, OCR regression scoring, configurable document layouts, matching rules and review semantics.
- Evidence inspected: MIT LICENSE; README; docs/BENCHMARKS.md; docs/REPORT.md; synth benchmark/generator/scorer/dataset adapters; test_benchmark.py; sample loads 001–005; matching/reporting architecture. Repository explicitly states samples are synthetic and PII-free.
- Concrete benchmark cases:
  - clean rate confirmation + invoice + POD;
  - linehaul billed above agreement plus duplicate fuel line;
  - unauthorized accessorial;
  - detention billed but POD lacks timestamps => block/review rather than assert;
  - POD shows 4.25h onsite, 2h free time, $80/hr agreed detention but invoice omits detention => candidate recoverable revenue.
- License / rights: MIT code and committed synthetic sample data under repository license. External CORD-v2 benchmark retains CC-BY-4.0 attribution requirements.
- Reuse classification: Directly reusable subject to MIT terms; preserve attribution and keep external-dataset licenses separate.
- Why non-obvious: Zero stars and generic repo name obscure a serious freight-specific benchmark/evaluation system. The strongest contribution is not the SaaS scaffold; it is the falsifiable, cents-based freight document/audit test harness plus explicit evidence that generic OCR performs poorly out of distribution.
- Scores:
  - Technical value: 9.2/10
  - Commercial value: 8.8/10
  - Rarity: 9.3/10
  - Completeness: 9.0/10 as benchmark/audit donor
  - Build-time saved: 8.8/10
  - Data advantage: 8.5/10 for safe benchmark coverage
  - High-ticket potential: 8.5/10 as assurance-enabling infrastructure
- Combination opportunities: Freight Recovery v7 gold-truth harness + Assay confidence gate + Zerox/invoice extraction pipeline + this repo's rendered freight benchmark. Add its five challenge cases to the acceptance-test regression suite, then extend with duplicate invoice, stale/superseded rate, partial settlement, reclass/reweigh, fuel-index date, missing POD and ambiguous accessorial cases.
- Next action: Import the MIT synthetic sample corpus/benchmark specification into the ChatGPT Freight Recovery benchmark library and adapt the v7 acceptance harness so extraction confidence and audit-rule correctness are measured separately.

### indy-viberr/stowaway — proprietary benchmark concepts only / do not reuse
- Repository: https://github.com/indy-viberr/stowaway
- Commit / revision: 9dc69e05769bd0c33aa59b3e898ec025897797dd
- Date discovered: 2026-09-19
- What it contains: Synthetic freight audit/fraud demo with 51 invoices, planted anomalies, generated POD scan images and an answer key; its pipeline test asserts exact recovery of the planted answer key.
- Why it matters: Confirms useful generic benchmark dimensions such as duplicate billing/accessorials, stale fuel-week selection, carrier authority/name mismatch, linehaul variance, missing/unsigned POD and consignee mismatch.
- Evidence inspected: LICENSE; synthetic-data notice; answer_key.json; generation script; truth/pipeline tests. No dataset/code was copied into our stack.
- License / rights: Explicit proprietary/confidential evaluation-only license: no use/copy/reproduction/modification/derivatives without permission.
- Reuse classification: **Do not reuse code or data.** High-level industry problem categories may be independently implemented from public freight-domain knowledge.
- Why non-obvious: Public GitHub visibility could easily be mistaken for open-source permission; the LICENSE explicitly says otherwise.
- Scores:
  - Technical value: 7.5/10 as conceptual reference
  - Commercial value: 2.0/10 under current rights
  - Rarity: 8.0/10
  - Completeness: 7.5/10 conceptually
  - Build-time saved: 0/10 reusable
  - Data advantage: 0/10 usable
  - High-ticket potential: 0/10 as-is
- Next action: Do not revisit or import unless license/permission changes. Cover equivalent generic cases independently in the MIT v7 benchmark suite.


### ehs9nino/traffic-ocr-llm-benchmark — CC-BY rate-confirmation extraction gate
- Repository: https://github.com/ehs9nino/traffic-ocr-llm-benchmark
- Commit / revision: f4cccc066c544b072ace6b98f070c2dd590209f0
- Date discovered: 2026-09-19
- What it contains: CC BY 4.0 research benchmark with 15 synthetic/anonymized rate-confirmation images plus structured ground truth for load number, pickup/dropoff locations and times, total rate and rate-per-mile. It also contains pseudonymized driver/CDL research data, but that subset is not needed for Freight Recovery.
- Rare / undernoticed value: It creates a clean, independent gate specifically for the document that establishes commercial intent before billing. Most invoice-OCR benchmarks do not test whether the accepted/negotiated rate confirmation itself was extracted correctly.
- Likely buyer / user: Internal QA for Freight Recovery v7; vendors benchmarking OCR/vision extraction of freight rate confirmations.
- Painful problem: A perfect invoice parser still produces wrong recovery dollars if the controlling rate confirmation is misread. Rate amount, lane, load identity and timing must be validated upstream of any rerating.
- Monetization mechanism: Benchmark infrastructure for the paid Freight Audit Acceptance Test; use it to substantiate extraction reliability and identify format-specific calibration needs.
- Build-time / data advantage: Saves weeks of creating rate-confirmation image fixtures and manually labeling freight-specific commercial fields.
- Evidence inspected: README; CC BY 4.0 LICENSE; rate_confirmations/annotations/ratecon_ground_truth.json; DOI-backed dataset description.
- License / rights: CC BY 4.0. Commercial sharing/adaptation allowed with attribution and indication of changes. Do not use driver/CDL subset for re-identification or biometric reconstruction; v7 does not need that subset.
- Reuse classification: Directly reusable with attribution; restrict v7 use to rate-confirmation benchmark subset.
- Why non-obvious: Only ~1 GitHub star, academic framing, but directly tests one of the highest-risk v7 inputs.
- Scores:
  - Technical value: 8.8/10
  - Commercial value: 8.2/10
  - Rarity: 9.1/10
  - Completeness: 8.5/10 for rate-con extraction
  - Build-time saved: 8.2/10
  - Data advantage: 8.5/10
  - High-ticket potential: 7.8/10 as QA infrastructure
- Combination opportunities: Rate-con benchmark → Zerox/invoice-extraction-pipeline → Assay confidence gate → canonical rate_authority/rate_rule → deterministic rerating. Score load-ID exactness, total-rate exactness, pickup/dropoff identity and extraction abstention separately before allowing rate authority into the gold-truth pipeline.
- Next action: Add a v7 rate-authority extraction scorecard and require a configurable confidence threshold; incorrect or low-confidence rate authority must force review and $0 asserted recovery.
