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
- Commercial possibilities: Permissioned direct reuse/adaptation inside the Freight Recovery product: evidence-backed detention recovery for carriers/brokers, or shipper-side detention/accessorial validation that verifies billed detention against geofence, appointment, notice, free-time and rule-card evidence before payment. The existing evidence-share/approval workflow can also feed dispute packets and recovery attribution.
- Build-time savings: Very high under the user's separate commercial modification/deployment permission. The inspected implementation/test suite can now be reused/adapted rather than independently re-created, collapsing months of work across event pairing, appointment-aware pricing, notice requirements, evidence hashing, approval controls, idempotent billing and dispute-ready artifacts.
- Evidence inspected: Repository metadata and latest main commit; `backend-dotnet/Services/DetentionService.cs` showing consumed-event-ledger semantics, job attribution, later-of appointment/arrival clocking, pre-expiry notices, rule-card selection, fail-closed pricing, rounding and caps; `backend-dotnet.Tests/DetentionApprovalPostgresTests.cs` exercising the real geofence-event -> dwell -> price -> approval pipeline, immutable evidence SHA linkage, double-approve prevention, missing-reference gate, audited override, public share token, and recovery funnel; detention schema migration/search evidence; deployment helper commit. No secrets or private data were collected.
- License / rights: No public `LICENSE` file at the inspected revision. On 2026-09-19 the user stated they hold separate permission covering **commercial modification and deployment** of this repository. Treat that permission as the operative reuse basis for the user's projects. Preserve the permission record in writing; do not infer redistribution, sublicensing or rights for third parties unless the permission expressly grants them.
- Reuse classification: **Permissioned direct reuse for the user's commercial modification/deployment.** Public-repo visibility alone still grants no rights to others.
- Scores:
  - Technical value: 9.5/10
  - Commercial value: 9.7/10
  - Rarity: 9.6/10
  - Completeness: 9.1/10
  - Build-time saved: 9.5/10
  - Data advantage: 9.1/10
  - High-ticket potential: 9.6/10
- Next action: Promote Opstrax into the core Freight Recovery stack. Reuse/adapt the detention evidence subsystem directly under the user's permission: consumed geofence-event ledger, appointment-aware clock, customer/tenant rule cards, notice timing, immutable evidence hash, approval/idempotency guards and shareable dispute evidence. Add regression tests that prove the imported path preserves v8/v9 fail-closed money states and never converts unsupported dwell/accessorial evidence into recovery.

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


### Etherlabs-dev/multi-processor-reconciliation — ambiguity-safe settlement matcher
- Repository: https://github.com/Etherlabs-dev/multi-processor-reconciliation
- Commit / revision: 2f9397fbe56a76abeee42a01a37536ad1811a806
- Date discovered: 2026-09-19
- What it contains: MIT reconciliation engine with immutable canonical financial records, source/account/currency/type hard controls, amount/date tolerances, reference-aware scoring, duplicate-input detection, refund/reversal classification, explicit ambiguous-candidate states, bounded split-payment matching, discrepancies and input fingerprints; supported by tests and benchmark code.
- Rare / undernoticed value: Its most valuable feature for Freight Recovery is not payment-processor connectivity; it is disciplined refusal to invent matches. Multiple near-equal candidates or multiple valid split groups are explicitly marked ambiguous instead of forced into a settlement allocation.
- Likely buyer / user: Internal v7 settlement/recovery-attribution service.
- Painful problem: Carrier credits/refunds often arrive later and may aggregate several findings. A recovery company can accidentally overstate its success fee if a credit is guessed onto the wrong finding, if a refund was already expected, or if several valid allocations exist.
- Monetization mechanism: Enables defensible success-fee billing by proving which realized credits/refunds can be uniquely tied to v7-unique findings; unresolved allocations remain fee-ineligible.
- Build-time / data advantage: Likely 1–2 months saved across canonical financial normalization, ambiguity controls, split-payment logic, idempotency/fingerprints and reconciliation tests.
- Evidence inspected: MIT metadata; matching.py; models.py; matching tests; benchmark structure. Source inspection confirmed exact-reference, fee-aware, refund/reversal, amount/date-window and bounded split matching.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT terms; adapters must be rewritten for freight settlement records.
- Why non-obvious: Only a few stars and positioned around Stripe/PayPal/Square/ACH, but the reconciliation semantics are directly applicable to freight credits/remittances.
- Scores:
  - Technical value: 9.1/10
  - Commercial value: 9.0/10
  - Rarity: 8.8/10
  - Completeness: 8.8/10 for conservative allocation
  - Build-time saved: 8.2/10
  - Data advantage: 5.0/10
  - High-ticket potential: 9.0/10 as success-fee integrity layer
- Combination opportunities: recovery_attribution ledger + carrier credit memo/remittance ingest + this matcher. Strict reference/currency/type checks first; bounded split only after; ambiguity => unresolved and $0 fee eligible.
- Next action: Use as implementation donor for the freight-specific settlement-attribution harness already created; add carrier invoice/credit/remittance references as stronger match evidence than amount/date alone.

### europeanplaice/subset_sum — deterministic many-to-many recovery allocation
- Repository: https://github.com/europeanplaice/subset_sum
- Commit / revision: 62fe41b4c8f5d287d1904f573a9594cac254d340
- Date discovered: 2026-09-19
- What it contains: MIT subset-sum/reconciliation library with Rust/Python surfaces, one-to-many, many-to-one and bounded many-to-many transaction matching, exact matching, configurable tolerance and tests. Its own agent skill explicitly says the numeric solver—not an LLM—must be the source of truth, strict matching should run before tolerance, and confirmed numeric matches must be separated from hypotheses.
- Rare / undernoticed value: Freight credits can collapse several invoice adjustments into one payment/credit memo or apply one correction across multiple remittance lines. Deterministic subset decomposition is a better foundation than LLM reasoning for that allocation problem.
- Likely buyer / user: Internal v7 recovery-attribution/reconciliation engine.
- Painful problem: Many-to-many settlement creates a combinatorial matching problem; guessing by narrative/reference text can misattribute success fees.
- Monetization mechanism: Protects contingency economics by supporting auditable, numeric allocation of realized recovery to findings.
- Build-time / data advantage: Saves weeks of deterministic subset/reconciliation work and provides tested group-matching primitives.
- Evidence inspected: MIT license metadata; reconciliation.rs; Python tests; dpss-reconcile operating skill.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT terms.
- Why non-obvious: Tiny generic numeric project, but it solves a high-value freight settlement edge case more directly than most logistics repositories.
- Scores:
  - Technical value: 8.9/10
  - Commercial value: 8.8/10
  - Rarity: 8.7/10
  - Completeness: 8.6/10 for numeric many-to-many matching
  - Build-time saved: 7.8/10
  - Data advantage: 3.0/10
  - High-ticket potential: 8.8/10 as attribution infrastructure
- Combination opportunities: Use after exact-reference matching. Integer minor units + bounded group sizes + unique-solution requirement; do not allow combinatorial match alone to establish entitlement.
- Next action: Integrate only as a numeric candidate generator under v7; require independent reference/provenance evidence or unique bounded solution before setting allocation_status=resolved.

### apimeister/x12-types — freight invoice + remittance transaction primitives
- Repository: https://github.com/apimeister/x12-types
- Commit / revision: e8238385d9f4a8a21b6e4525f5ab3acc7bed3978
- Date discovered: 2026-09-19
- What it contains: Apache-2.0 Rust X12 transaction-set types/parsers with freight-relevant test fixtures including X12 210 Motor Carrier Freight Details and Invoice plus X12 820 Payment Order/Remittance Advice. The test corpus also covers transportation status/order families such as 204/214 alongside many business transaction types.
- Rare / undernoticed value: Gives v7 typed/tested EDI primitives on both sides of the money chain: carrier billing (210) and payment/remittance (820), reducing dependence on OCR/CSV for customers already exchanging EDI.
- Likely buyer / user: Enterprise shippers, 3PLs and freight-payment teams with EDI feeds; internal v7 ingestion layer.
- Painful problem: To prove realized recovery, v7 needs to connect original freight billing to later remittance/adjustment evidence. EDI 210 + 820 parsing provides a structured enterprise path.
- Monetization mechanism: Faster enterprise onboarding and more reliable settlement proof for continuous assurance.
- Build-time / data advantage: Saves weeks to months of X12 schema/parser work and gives test examples for freight invoice and remittance transaction families.
- Evidence inspected: Apache-2.0 metadata; v005010 820 docs/tests; committed X12 210 test fixture and broader transportation transaction fixtures.
- Important limitation: X12 syntax/types do not solve customer-specific trading-partner mappings, semantic provenance, or recovery attribution by themselves. Some test examples originate from third-party open sample sources whose provenance should remain attributed.
- License / rights: Apache-2.0 for repository code. Treat external sample fixture provenance separately.
- Reuse classification: Directly reusable code subject to Apache-2.0; fixtures reviewed individually for source attribution.
- Why non-obvious: Generic X12 library rather than logistics product, but directly shortens freight bill/remittance ingestion.
- Scores:
  - Technical value: 9.0/10
  - Commercial value: 8.7/10
  - Rarity: 8.5/10
  - Completeness: 8.5/10 for X12 parsing primitives
  - Build-time saved: 8.5/10
  - Data advantage: 5.0/10
  - High-ticket potential: 8.8/10 as enterprise integration enabler
- Combination opportunities: X12 210 -> carrier_invoice; X12 820 -> settlement/remittance; then Etherlabs/subset-sum allocation -> recovery_attribution.
- Next action: Define exact canonical field mappings for 210 invoice numbers/amounts/references and 820 remittance reference/amount/adjustment elements before customer EDI onboarding.


### U.S. GAO adjudicated freight cases — real historical benchmark layer
- Sources: Official GAO transportation decisions including B-135992 (1961), B-130579 (1957), B-129646 (1957), B-152744 (1964), B-134575 (1958), B-148611 (1962), B-202596 (1982), and B-211465 (1983).
- Date discovered / packaged: 2026-09-19
- What it contains: Eight real, publicly adjudicated freight-payment disputes with government bills of lading, carrier billing facts, rate/tariff/tender issues, shipment weights and/or official overcharge/recovery amounts. This is intentionally separated from current commercial benchmarks because the tariff/regulatory context is historical.
- Rare / undernoticed value: Unlike synthetic freight datasets, these are real payment disputes with independently adjudicated outcomes. They validate durable audit semantics: minimum-weight errors, wrong rate authority, alternate lower route/rate, service-entitlement mismatch, commodity/classification logic, tender-vs-tariff selection, disputed weight basis and evidence burden.
- Strongest cents-level case: GAO B-135992. Published facts show a shipment actually weighing 21,793 lb, carrier billing construction charging an equivalent 28,931 lb, a $2.11/100-lb rate and proper 24,000-lb volume minimum. Independent arithmetic: (28,931 - 24,000) / 100 × 2.11 = $104.0441; GAO reported a $104.05 overcharge.
- Other published amounts captured: B-130579 $571.25 refund; B-129646 $109.42 initial recovery plus $88.58 additional recovery; B-152744 $122.20 overcharge; B-134575 $1,034.02 overpayment collected; B-148611 $45.96 overcharge. Cases whose public summary does not expose a complete recoverable amount are explicitly fail-closed at $0 asserted recovery in the benchmark.
- Likely buyer / user: Internal v7 benchmark/QA; enterprise prospects evaluating whether the truth engine handles real-world tariff/entitlement reasoning beyond simple line arithmetic.
- Painful problem: Synthetic benchmarks can overfit modern normalized schemas. Real adjudicated cases demonstrate that actual leakage often depends on rate authority, service entitlement, routing, classification and evidentiary sufficiency.
- Monetization mechanism: Strengthens credibility of the paid Freight Audit Acceptance Test by showing the truth engine is regression-tested on both modern freight fixtures and real adjudicated cases.
- Evidence inspected: Official GAO decision pages; numeric facts were paraphrased into an independent benchmark. No historical tariff text was republished.
- Rights / provenance: U.S. Government public decision records used as factual source material. Preserve source URLs/case IDs. Historical rates/rules are not current commercial authority.
- Reuse classification: Real public benchmark facts / independently encoded test cases. Do not use old rates as current pricing.
- Scores:
  - Technical value: 9.0/10
  - Commercial value: 8.8/10
  - Rarity: 9.4/10
  - Completeness: 8.3/10 across the eight cases
  - Build-time saved: 7.5/10
  - Data advantage: 9.0/10 as real adjudicated evidence
  - High-ticket potential: 8.7/10 as credibility/QA layer
- Combination opportunities: Real adjudicated cases + MIT synthetic semantic cases + Cointab arithmetic benchmark + rate-con OCR gate + customer-specific blind gold truth. This gives v7 four distinct QA layers: extraction, arithmetic/rating, freight semantics, and real-world adjudicated reasoning.
- Next action: Continue adding modern public audit cases when transaction-level facts are sufficiently specific, but keep them distinct from current customer data and current commercial rate authority.


### august-andersen/tabular-reconciliation-eval — MIT freight rounding/scope benchmark
- Repository: https://github.com/august-andersen/tabular-reconciliation-eval
- Commit / revision: 3ed898457f71839d207880996cefad8b50e1300a
- Date discovered: 2026-09-19
- What it contains: MIT evaluation suite for exception-blindness in tabular reconciliation. Its T3 logistics carrier-settlement task reconciles ~500 carrier invoice lines against shipment manifests, computes per-shipment fuel, individually rounds accessorials using a declared rounding method, and applies a $0.02 dispute tolerance. Source/test inspection shows a frontier model repeatedly failed 16/17 checks because it summed raw fuel first and rounded only at invoice scope rather than rounding each shipment first.
- Rare / undernoticed value: This is a high-leverage freight-specific QA case where an auditor can be nearly perfect yet still make a deterministic pennies-level error that flips a payment/dispute decision. The benchmark explicitly models rounding method and rounding scope as business rules, not generic formatting.
- Likely buyer / user: Freight Recovery v8 internal QA, FAP implementation/acceptance testing, finance/AP systems that aggregate shipment-level charges.
- Painful problem: Global rounding assumptions can create systematic false disputes or missed variances across high invoice volume; invoice-level totals can look plausible while violating the controlling calculation scope.
- Monetization mechanism: Strengthens the paid Acceptance Test by detecting subtle implementation/configuration errors in incumbent/challenger systems and preventing false-positive dispute labor.
- Build-time / data advantage: Saves weeks of designing/verifying a realistic carrier-settlement edge-case corpus and supplies a proven failure mechanism.
- Evidence inspected: MIT metadata; README T3 design/results; T3 instruction.md; deterministic build_inputs.py; verifier test_outputs.py. The original generated task data need not be copied to reproduce the generic rounding invariant.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT; v8 independently implemented its own smaller rounding-scope regression fixture.
- Why non-obvious: One GitHub star and framed as a general data-science eval, but the freight task directly exposes a production-relevant settlement failure.
- Scores:
  - Technical value: 9.2/10
  - Commercial value: 8.9/10
  - Rarity: 9.2/10
  - Completeness: 9.0/10 as a rounding/scope benchmark
  - Build-time saved: 8.5/10
  - Data advantage: 8.0/10
  - High-ticket potential: 8.8/10 as assurance infrastructure
- Combination opportunities: Add contract-defined rounding_method + rounding_scope to rate_rule/rating_component; score exact cents and dispute-threshold classification in the challenge tier. Pair with RulesEngine and the blind FAP bake-off so a challenger cannot pass by matching dollars approximately.
- Next action: Keep the independently authored v8 regression where per-shipment banker's rounding settles the invoice but aggregate rounding creates a false $0.04 dispute; extend to accessorial-specific and minimum/rate-break boundary rounding.

### NexusFeed/nexusfeed-mcp — optional verifiable LTL fuel-data adapter
- Repository: https://github.com/NexusFeed/nexusfeed-mcp
- Commit / revision: 5fe18953bd4e9e5b68b9ff4f46b0462800f5e13c
- Date discovered: 2026-09-19
- What it contains: MIT Python MCP client for a commercial NexusFeed backend. The LTL client exposes normalized carrier fuel-surcharge data and carrier metadata, with response verifiability fields such as source timestamp, extraction confidence, source evidence URL, extraction method and freshness TTL. README claims current/history coverage across major LTL carriers; inspected client code currently calls commercial /v1/ltl/fuel-surcharge and /v1/ltl/carriers endpoints. Accessorial endpoint exists in the client but is explicitly marked COMING SOON.
- Rare / undernoticed value: A low-star ready-made adapter pattern for pulling volatile carrier fuel data with source/freshness/confidence metadata rather than treating a scraped percentage as timeless truth.
- Likely buyer / user: Optional v8 external-truth connector for customers whose contracts explicitly reference carrier-published fuel tables.
- Painful problem: Carrier fuel pages are often dynamic and version-sensitive; stale or low-confidence data can create incorrect dispute claims.
- Monetization mechanism: Reduces integration/maintenance burden for fuel validation inside continuous shadow assurance; not itself the commercial wedge.
- Build-time / data advantage: Potentially weeks of carrier-page extraction/normalization maintenance if the commercial service is licensed.
- Evidence inspected: MIT repo metadata; README; mcp_server/tools/ltl.py; freight_audit_workflow prompt. No API key or paid data was accessed.
- License / rights: Client wrapper is MIT. NexusFeed backend/data service is explicitly commercial and governed separately; requires API access/terms. The client license does not grant data-service rights.
- Reuse classification: Client reusable under MIT; backend/data only under commercial authorization. Treat its published carrier data as corroborating evidence, not customer contract entitlement.
- Why non-obvious: One-star repo with a narrow MCP wrapper, but the verifiability envelope is useful for v8 source provenance. Limitation: accessorial service is not implemented yet in inspected client.
- Scores:
  - Technical value: 7.8/10
  - Commercial value: 7.5/10
  - Rarity: 8.2/10
  - Completeness: 6.5/10
  - Build-time saved: 7.5/10
  - Data advantage: 7.5/10 if commercially licensed
  - High-ticket potential: 6.5/10 as supporting infrastructure
- Combination opportunities: Optional adapter into the external-truth layer: raw source URL + timestamp + confidence + freshness → tariff-authority gate → customer contract formula. Never use carrier-published fuel data without proving customer incorporation/effective date.
- Next action: Keep optional, not core. Prefer direct carrier/EIA sources for benchmark/reference and use NexusFeed only if a customer pilot justifies commercial API cost.


### srthck/trustmesh — proof-obligation / next-best-evidence control-plane donor
- Repository: https://github.com/srthck/trustmesh
- Commit / revision: 5a93d70b37aafecaf61a5bc0296eaf831e5504ac
- Date discovered: 2026-09-19
- What it contains: MIT evidence-decisioning control plane originally built for payment disputes. Deep source inspection confirmed explicit proof obligations, blocking-evidence analysis, evidence graphs, versioned adjudication/policy layers, deadline-aware evidence-action optimization, duplicate-evidence filtering, counterfactual supportive/contradictory outcomes, deterministic ranking/replay traces, and a UI/API layer that answers “what evidence is preventing a stronger decision?” and “what should be acquired next?”
- Rare / undernoticed value: 0-star repository with unusually mature **proof-readiness and next-best-evidence** mechanics. The valuable layer is not payment-domain policy; it is the architecture that prevents a system from turning an incomplete case into an asserted financial decision and directs analysts toward the highest-value missing proof.
- Likely buyer / user: Freight Recovery v8 operator console, freight-audit/FAP implementation QA, recovery analysts and dispute teams.
- Painful problem: Once a freight discrepancy is identified, analysts waste time manually figuring out which missing document/fact would make the finding defensible. Generic audit tools often surface “missing evidence” without prioritizing the next evidence acquisition or checking deadline feasibility/duplication.
- Monetization mechanism: Reduce analyst touches/time per validated finding; accelerate claim-ready cases; suppress false disputes; strengthen paid Acceptance Tests and continuous shadow assurance.
- Build-time / data advantage: High. Likely saves 1–3 months of designing proof-obligation, evidence-gap, deadline, trace/replay and evidence-action optimization infrastructure.
- Evidence inspected: MIT metadata; trustmesh/application/evidence_gaps.py; engine/proof_obligation.py; optimizer/policy.py; extensive optimizer/adjudication test suite including blocking-obligation targeting, no-action state, deterministic ranking, dependency-depth prioritization, deadline infeasibility, duplicate/unavailable evidence filtering, supportive/contradictory counterfactuals, immutable original cases, explicit heuristic calibration notices and replay integrity.
- License / rights: MIT repository code. **Do not reuse its Visa/Razorpay/payment-network policy content as freight entitlement policy.** Freight obligation/action definitions must be independently domain-specific and source-backed.
- Reuse classification: Structural code/patterns reusable under MIT; payment-domain rules/policy are not adopted as freight policy.
- Why non-obvious: Repo name and domain suggest payment disputes rather than transportation; the reusable commercial value is the general proof/readiness optimizer beneath the payment examples.
- Scores:
  - Technical value: 9.4/10
  - Commercial value: 9.2/10
  - Rarity: 9.5/10
  - Completeness: 9.2/10 as proof/readiness architecture
  - Build-time saved: 9.1/10
  - Data advantage: 6.5/10
  - High-ticket potential: 9.0/10 as part of v8
- Combination opportunities: Freight Recovery v8 finding → freight-native blocking obligations → ranked evidence action → re-evaluate finding without mutating the original decision. Key freight actions include controlling rate document/amendment, BOL, signed POD, lumper receipt, dwell timestamps, weight ticket, contract-defined fuel evidence, carrier identity, credit memo/remittance allocation and incumbent audit export.
- Validation result: An independently authored freight-native optimizer now passes 10 tests. Missing lumper support recommends lumper receipt; missing detention proof recommends dwell timestamps; stale historical authority recommends controlling rate evidence; ambiguous settlement recommends remittance allocation; missing incumbent output recommends incumbent export; expired deadline returns no feasible action; duplicate evidence is filtered; rankings/traces replay deterministically. Heuristic outcome priors are explicitly labeled uncalibrated and never described as probability of recovery.
- Next action: Integrate the freight-native optimizer into v8 core/API/UI as “What evidence do we need next?” while preserving the invariant that evidence recommendations never change finding or recovery dollars by themselves.


### elliepetalmedia/freight-class-pro — current 13-tier density reference, licensing unresolved
- Repository: https://github.com/elliepetalmedia/freight-class-pro
- Commit / revision: 03d813c918cb3e06af3c4f45b1e5afe4cbe39d6d
- Date discovered: 2026-09-19
- What it contains: Browser-side freight density/class calculator and manifest/BOL utility. Its published calculator summary implements the modern 13-tier density scale and discloses handling-unit measurement assumptions.
- Why it matters: Useful corroborating clean-room implementation reference for the LTL density math/UI, but not authoritative NMFC item classification. Current NMFTA sources independently confirm the 13-tier scale and warn that full-density treatment does not apply blindly to every commodity/item.
- Current authoritative validation: NMFTA's Apr. 7, 2026 help material confirms the 13 breaks: <1=400, 1-<2=300, 2-<4=250, 4-<6=175, 6-<8=125, 8-<10=100, 10-<12=92.5, 12-<15=85, 15-<22.5=70, 22.5-<30=65, 30-<35=60, 35-<50=55, 50+=50. NMFTA states the Docket 2025-1 modernization became effective July 19, 2025 and that correct item identification plus handling/stowability/liability concerns can still prevent simple full-density classification.
- Evidence inspected: README; calculator.md; repository tree/license state; current NMFTA 2026 FAQ/help and ClassIT+ API documentation.
- License / rights: README claims MIT, but repository tree contains no LICENSE file and GitHub metadata reports no recognized license. Treat repository code as inspect/clean-room only unless a license file/permission appears. The v8 density implementation was independently authored from current NMFTA public guidance rather than copied from this code.
- Reuse classification: Inspect/clean-room only for repo code. Public density thresholds used only with NMFTA attribution/source context.
- Non-obviousness: Zero-star repo with current industry-change awareness, but the key value is identifying a high-risk oversimplification: assigning class from density alone without proving the controlling item is full-density.
- Commercial consequence: v8 now exposes both density_scale_class and asserted_class. asserted_class remains null unless source evidence proves full-density applicability; HSL or unknown applicability => REVIEW_ZERO_ASSERTION.
- Build/validation result: Independently authored LTL classification gate passes 5 boundary/applicability tests, including the public 48×40×48, 800-lb example (15.0 pcf → class 70) and fail-closed HSL/unknown-item cases.
- Next action: Integrate the gate into the v8 challenge tier and customer intake. For production, accept customer-authorized ClassIT+/carrier/item evidence or controlling tariff proof; do not scrape/recreate the proprietary NMFC commodity catalog.


### emoss08/Trenova — detention-policy challenge oracle
- Repository: https://github.com/emoss08/Trenova
- Commit / revision: `95fcf816562025ad9af864ded4a5fce8a555bd65`
- Date discovered / revalidated: 2026-09-19
- What it contains: Current TMS implementation with a broad detention-policy model covering clock-start basis, multiple late-arrival rules, pickup/delivery/pay free-time overrides, billing increments, Up/Down/Nearest/Exact rounding, flat-vs-tiered rates, per-stop/day/shipment caps, layover conversion, notification requirements/unnotified behavior, approval thresholds, immutable policy snapshots/calculation traces and append-only hash-chained detention evidence.
- Why it matters: It exposes policy dimensions that can make a physically correct Opstrax dwell calculation commercially wrong if the customer's contract uses different detention semantics. It is therefore an excellent independent challenge oracle for v10 policy compatibility.
- Evidence inspected: Current PostgreSQL/SQLite detention-policy migrations, repository metadata and LICENSE.
- License / rights: `FSL-1.1-ALv2`. Current versions may be used for permitted purposes but **not for a competing commercial product/service with the same or substantially similar functionality** until the future Apache-2.0 conversion date for that version. Do not embed/copy Trenova code into Freight Recovery under the current FSL terms.
- Reuse classification: Inspect/compare/independently reauthor generic policy tests only. No direct competing-product code reuse.
- Commercial value: High as a negative-test oracle; low as a directly reusable component under current rights.
- New v10 result: Freight Recovery v10.2 now has an independently authored policy-parity gate. If the customer's policy requires unsupported semantics (for example round-up, arrival-only clock, different pickup/delivery free time, tiered rates, required-notice suppression, layover conversion or per-day/per-shipment caps), the Opstrax path returns `REVIEW_ZERO_ASSERTION` instead of silently applying its own algorithm.
- Next action: Keep Trenova out of the runtime stack. Add any newly observed policy dimensions as rights-clean challenge cases and only automate money after exact policy parity is proven.
