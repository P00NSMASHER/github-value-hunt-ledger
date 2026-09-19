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
