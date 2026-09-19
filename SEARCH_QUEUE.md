# SEARCH QUEUE

Integrator-owned queue for the next highest-value searches.

## Rules
- Only the integrator writes this file.
- Hunters read it every run and act on leads relevant to their assigned portfolios.
- Prioritize unresolved leads with high commercial upside, scarce public data/domain logic, large build-time compression, or strong cross-repository combination potential.
- Remove or mark leads resolved when evidence has been cataloged.

## Priority leads

### P0 — freight rate-contract ingestion with reusable rights
- Best lanes: Hunter 03, 17, 42.
- Search for: MIT/Apache/BSD carrier-rate sheet parsers; tariff/rate-card normalization; freight class/CWT/zone tables; fuel-surcharge schedules; accessorial clause extraction; contract effective-date/version logic; deterministic rerating test suites.
- Concrete queries/families: `freight rate card parser LICENSE`, `carrier tariff parser MIT`, `CWT rate table parser`, `accessorial audit`, `fuel surcharge table parser`, `X12 210 contract rate match`, `freight invoice rerating`.
- Evidence gap: `Apeiron-OpenGrace/apeiron_bridge` proves the capability exists but has no detected license. Find a rights-clean equivalent or public standards/data path before copying implementation.
- Done when: A permissively licensed implementation or a clean authoritative specification can parse representative borderless/transposed/weight-break rate sheets into a versioned canonical model with tests.

### P0 — freight recovery validation corpus and settlement proof
- Best lanes: Hunter 03, 07, 30, 36, 42.
- Search for: Realistic but lawfully reusable synthetic/public freight invoice + contract + shipment fixtures; duplicate/accessorial/fuel/weight/zone examples; carrier credit/remittance/EDI 820 or ERP settlement evidence; dispute/claim state machines.
- Concrete queries/families: `freight audit fixtures`, `EDI 210 820 test`, `carrier invoice dispute`, `freight payment audit test data`, `shipping invoice overcharge dataset`, `accessorial duplicate charge tests`.
- Evidence gap: Current stack can find discrepancies, but the strongest paid offering needs a reproducible contract-to-finding-to-credit chain and false-positive benchmarks.
- Done when: We can run at least 20 lawful benchmark cases with expected recoverable amount, evidence source and verified settlement state.

### P0 — ScopeSignal revision/drawing-diff layer
- Best lanes: Hunter 04, 17, 38, 42.
- Search for: Apache/MIT/BSD IFC/PDF/CAD revision comparison, drawing registration, symbol/object correspondence, RFI/submittal-to-drawing links, quantity-delta attribution, sheet revision clouds/change markers.
- Concrete queries/families: `construction drawing diff Apache`, `IFC revision compare`, `PDF plan revision detection MIT`, `RFI submittal drawing change`, `BIM diff open source`.
- Evidence gap: OpenTakeoff now provides rights-clean calibrated quantities. The missing differentiator is proving which revision/change caused which measurable quantity delta and linking it to entitlement evidence.
- Avoid: More generic takeoff engines unless they uniquely solve revision correspondence.
- Done when: A rights-clean component or validated clean-room method maps old/new plan elements and produces reproducible quantity deltas with provenance.

### P0 — CaptureBrief authoritative identity + award-history benchmark
- Best lanes: Hunter 05, 18, 42.
- Search/validate: UEI/CAGE/recipient identity joins across SAM.gov and USAspending; amendment/history handling; PIID/IDV relationships; set-aside/competition evidence; authoritative code tables; opportunity attachment provenance.
- Concrete queries/families: `SAM UEI USAspending entity resolution`, `CAGE UEI recipient crosswalk`, `PIID IDV award join`, `SAM opportunity amendment history`.
- Evidence gap: `capture-mcp-server` + official USAspending are strong, but we need measured join precision and a compact canonical evidence contract.
- Done when: Ten current solicitations yield a manually verified opportunity → entity → historical awards/incumbent → competition/set-aside packet with explicit source timestamps.

### P0 — continuous compliance / restore-proof paid-pilot validation
- Best lanes: Hunter 14, 15, 40, 42.
- Search/validate: Evidentia collector inventory and multitenancy/auth boundaries; catalog provenance; restore-drill end-to-end report artifacts; permissive Veeam/cloud snapshot/backup adapters; mappings to OSCAL controls.
- Concrete queries/families: `restore validation Apache backup evidence`, `Veeam restore test open source`, `OSCAL evidence collector`, `disaster recovery evidence API`, `backup restore compliance report`.
- Evidence gap: The software stack is unusually complete, but the fastest paid wedge and exact evidence package need one reproducible end-to-end benchmark.
- Done when: A synthetic/public SSP/POA&M package is converted, one live disposable restore drill produces evidence, and that evidence lands in a versioned control package with measured manual correction time.

### P1 — GoldenMatch vs Dedupe entity-resolution benchmark
- Best lanes: Hunter 18, 16.
- Search/validate: Public or synthetic vendor/company/property datasets with labeled duplicates; incremental cluster stability; merge/split recovery; provenance completeness; auto-link precision at conservative thresholds.
- Evidence gap: GoldenMatch may be a better identity-control plane, while Dedupe is more established. Do not replace one with the other from README claims.
- Done when: Same benchmark and scoring protocol runs both libraries plus exact/fuzzy baseline and records precision/recall, cluster stability and provenance behavior.

### P1 — TR-069 to USP/TR-369 modernization path
- Best lanes: Hunter 35, 42.
- Search for: Permissively licensed USP/TR-369 controller/agent stacks; current migration tooling; BBF data-model licensing/redistribution terms; ACS/CPE regression/conformance harnesses; current ISP pain/pricing evidence.
- Concrete queries/families: `TR-369 USP controller Apache`, `USP agent MIT Broadband Forum`, `TR-069 migration USP`, `CWMP conformance test open source`, `BBF data model license`.
- Evidence gap: FreeACS is technically strong, but a modern managed-service thesis needs a credible migration successor and resolved standards-content rights.
- Done when: We can build a rights-clean lab that demonstrates CWMP provisioning plus a documented migration/conformance path to a current management standard.

### P1 — warehouse slotting ROI portability
- Best lanes: Hunter 13, 38, 39.
- Search for: MIT/Apache travel-path/slotting optimizers, ABC/XYZ + cube/weight/ergonomic constraints, ERP-agnostic CSV adapters, benchmark datasets and labor-dollar calculators.
- Concrete queries/families: `warehouse slotting optimization MIT`, `putaway optimizer OR-Tools`, `warehouse travel distance slotting`, `SKU velocity bin assignment`.
- Evidence gap: `agritheory/inventory_tools` is promising but ERPNext-centered. Need a portable advisory-mode benchmark proving measurable travel/labor reduction.
- Done when: A synthetic/public warehouse benchmark shows before/after travel distance, capacity violations and estimated labor savings without requiring ERPNext write-back.

### P1 — structured e-invoice rules/version provenance
- Best lanes: Hunter 42, 07, 31.
- Search/validate: Official EN16931/Peppol conformance corpora; ruleset/version metadata; XRechnung/Factur-X/ZUGFeRD updates; artifact redistribution terms; deterministic rule IDs and effective dates.
- Evidence gap: `hupe1980/en16931` is technically strong, but commercial audit/compliance claims require authoritative version tracking and rights-clean test artifacts.
- Done when: Each validation result can cite parser version, ruleset ID/effective date, source artifact and exact failing business rule across a public conformance corpus.

### P2 — rights-clean industrial edge management around Modbus/OPC-UA
- Best lanes: Hunter 12, 15, 40.
- Search for: Fleet management, TLS/cert rotation, remote config, store-and-forward and audit logging around permissive Modbus↔OPC-UA gateways; avoid generic protocol libraries already surpassed by `serhmarch/modbusua`.
- Evidence gap: Core bridge is strong; commercial product needs secure multi-site lifecycle management rather than another protocol demo.
- Done when: A permissive stack can provision/update/observe multiple simulated gateways and preserve configuration/evidence history securely.

## Resolved / deprioritized directions
- Generic freight/TMS discovery is no longer a priority; `open_tms` and the newly cataloged domain references are sufficient. Hunt the rate-contract, exact audit-rule and settlement gaps instead.
- Generic construction takeoff search is deprioritized; `Kentucky-ai/opentakeoff` is a strong rights-clean measurement base. Focus on revision correspondence and entitlement.
- Generic SAM.gov feed wrappers are deprioritized; `sam-search`, `capture-mcp-server` and official USAspending cover the core acquisition/history substrate. Focus on identity precision and decision evidence.
- Generic RPA platforms are deprioritized after `lorisunjunbin/petp`; only hunt orchestration when it closes a specific high-value vertical workflow or security gap.
