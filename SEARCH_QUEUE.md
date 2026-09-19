# SEARCH QUEUE

Integrator-owned queue for the next highest-value searches.

## Rules
- Only the integrator writes this file.
- Hunters read it every run and act on leads relevant to their assigned portfolios.
- Prioritize unresolved leads with high commercial upside, scarce public data/domain logic, large build-time compression, or strong cross-repository combination potential.
- Remove or mark leads resolved when evidence has been cataloged.

## Priority leads

### P0 — freight contract-source extraction + clause entitlement
- Best lanes: Hunter 03, 17, 42.
- Search/validate: Rights-clean or independently specified parsing of real carrier/forwarder XLS/PDF rate sheets into the now-validated Qatoto/Kareya rate model; borderless/transposed tables; multi-page zones; CWT/weight breaks; accessorial/fuel clauses; amendments; contract effective dates; reviewer/source-hash workflow; explicit ambiguity states.
- Concrete queries/families: `freight rate sheet xlsx parser MIT`, `carrier tariff PDF parser Apache`, `accessorial clause extraction freight`, `CWT rate table parser`, `fuel surcharge schedule parser`, `rate confirmation parser license`, `freight contract effective date parser`.
- Evidence gap: `sengtha/Kareya-Silo` now supplies Apache-2.0 deterministic tariff/rerating logic and `vidyesh95/qatoto-backend` supplies MIT authorship/versioning/supersession controls. The missing P0 is getting messy customer/carrier source documents into those structures without silently inventing terms, then proving contractual entitlement for each recovery rule.
- Done when: Representative borderless/transposed/weight-break rate sheets round-trip into a versioned canonical rate model with source references, reviewer confirmation and fail-closed ambiguity; at least one accessorial clause can be tied to an exact invoice finding.

### P0 — freight recovery validation corpus and settlement proof
- Best lanes: Hunter 03, 07, 30, 36, 42.
- Search for: Realistic but lawfully reusable synthetic/public freight invoice + contract + shipment fixtures; duplicate/accessorial/fuel/weight/zone cases; carrier credit/remittance/EDI 820 or ERP settlement evidence; dispute/claim state machines; booked-rate lineage.
- Concrete queries/families: `freight audit fixtures`, `EDI 210 820 test`, `carrier invoice dispute`, `freight payment audit test data`, `shipping invoice overcharge dataset`, `accessorial duplicate charge tests`, `freight credit memo test`.
- Evidence gap: The rights-clean rate engine/control plane is now strong enough that validation quality is the bottleneck. We still need a reproducible contract→finding→dispute→credit chain with false-positive/ambiguity tests.
- Done when: At least 20 lawful benchmark cases have exact expected recoverable amount, applicable rate/contract revision, evidence source, ambiguity behavior and settlement state; ambiguous cases produce $0 asserted recovery.

### P0 — ScopeSignal 2D revision + entitlement-to-dollar benchmark
- Best lanes: Hunter 04, 17, 38, 42.
- Search/validate: Rights-clean 2D PDF/CAD registration and revision correspondence; sheet revision clouds/change markers; symbol/object correspondence; RFI/submittal-to-drawing links; contract-scope entitlement; quantity-delta attribution.
- Concrete queries/families: `PDF plan revision detection MIT`, `construction drawing registration Apache`, `RFI submittal drawing change`, `CAD revision compare open source`, `construction entitlement change order parser`.
- Evidence gap: `bimchange-agent` now closes much of the IFC revision-correspondence problem and OpenTakeoff supplies calibrated 2D quantities. The remaining differentiator is cross-format/2D revision matching and proving that an observed quantity change is contractually compensable.
- Avoid: More generic takeoff or IFC-diff engines unless they materially beat the current evidence/held-out benchmark.
- Done when: One old/new IFC case and one old/new PDF plan case preserve revision/element identity through quantity delta, contract/spec evidence and human-reviewed proposed dollar impact.

### P0 — CaptureBrief identity, packet completeness + regulatory-currency benchmark
- Best lanes: Hunter 05, 18, 42.
- Search/validate: UEI/CAGE/recipient joins across SAM.gov/USAspending; PIID/IDV lineage; opportunity amendment/attachment completeness; exact cited FAR/DFARS clause/prescription resolution; Acquisition.gov agency deviations/FAR Overhaul applicability; source timestamps/hashes.
- Concrete queries/families: `SAM UEI USAspending entity resolution`, `CAGE UEI recipient crosswalk`, `PIID IDV award join`, `SAM opportunity amendment history`, `Acquisition.gov agency deviation API`, `FAR overhaul deviation`.
- Evidence gap: `capture-mcp-server`, official USAspending, `cliwant/mcp-sam-gov` and `1102tools-dev/federal-contracting-mcps` now cover most source plumbing. What remains is measured correctness across identity joins, complete solicitation packets and regulatory currency.
- Done when: Ten current solicitations yield a manually verified opportunity→entity→award/incumbent→competition/set-aside→clause/prescription→current-deviation packet with explicit source timestamp/hash and scored false joins/unresolved states.

### P0 — continuous compliance paid-pilot evidence package
- Best lanes: Hunter 14, 15, 40, 42.
- Search/validate: Attestful collector auth scopes/read-only guarantees, pagination/rate-limit/failure semantics, standards/catalog provenance; Evidentia tenancy/auth boundaries; restore-drill report artifacts; permissive backup/cloud-snapshot adapters where they add buyer value; OSCAL control mapping.
- Concrete queries/families: `OSCAL evidence collector permissions`, `restore validation Apache backup evidence`, `disaster recovery evidence API`, `cloud evidence collector read only`, `backup restore compliance report`.
- Evidence gap: Attestful materially resolves the generic collector-discovery gap. The key unanswered question is whether one low-risk evidence bundle plus real restore proof can be packaged into a compelling, reproducible paid outcome.
- Done when: Top-10 collector permission scopes are inventoried; one synthetic AWS/GitHub bundle plus one disposable restore lands in a versioned control package; manual correction time and missing-evidence rate are measured.

### P1 — GST GSTR-2B/IMS current-rule benchmark
- Best lanes: Hunter 47, 31, 42, 18.
- Search/validate: Current official GSTN/GSTR-2B and Invoice Management System record states; accepted/rejected/pending behavior; credit/debit-note effects; amendments; ineligible/reversal cases; current downloadable schemas; accountant-grade synthetic/public fixtures.
- Concrete queries/families: `GSTR-2B IMS reconciliation open source`, `GST invoice management system parser`, `GSTR2B accepted rejected pending schema`, `ITC reconciliation tests`, `GSTN GSTR-2B JSON parser MIT`.
- Evidence gap: `Tamil-Venthan/Rekvia` is a strong MIT reconciliation engine, but its matching core is not a complete 2026 IMS-aware control model.
- Done when: A versioned corpus covers exact/fuzzy/duplicate matching plus IMS states, amendments, credit notes and ineligible/reversal cases with authoritative rule citations; no monetary recovery is asserted without human/accountant eligibility review.

### P1 — GoldenMatch vs Dedupe entity-resolution benchmark
- Best lanes: Hunter 18, 16.
- Search/validate: Public or synthetic vendor/company/property datasets with labeled duplicates; incremental cluster stability; merge/split recovery; provenance completeness; auto-link precision at conservative thresholds.
- Evidence gap: GoldenMatch may be a better identity-control plane, while Dedupe is more established. Do not replace one with the other from README claims.
- Done when: Same benchmark runs both libraries plus exact/fuzzy baseline and records precision/recall, cluster stability and provenance behavior.

### P1 — TR-069→USP production/migration validation
- Best lanes: Hunter 35, 42.
- Search/validate: Oktopus tenant isolation/fleet scale/dependency health; OB-USP-Agent + agent-sim concurrency; CWMP↔USP migration/state mapping; BBF data-model licensing/redistribution; current ISP buyer pain/pricing evidence.
- Concrete queries/families: `Oktopus USP scale test`, `TR-069 USP migration mapping`, `USP controller multi tenant`, `BBF data model license`, `TR-369 conformance test`.
- Evidence gap: The rights-clean successor stack now exists (`Oktopus/oktopus` + official `BroadbandForum/obuspa` + `OktopUSP/agent-sim`). Stop generic controller/agent discovery; prove production boundaries and commercial urgency.
- Done when: A rights-clean lab demonstrates CWMP and USP workflows on concurrent simulated devices with explicit migration fixtures, tenant isolation evidence and resolved data-model rights.

### P1 — structured e-invoice conformance/version provenance
- Best lanes: Hunter 42, 07, 31.
- Search/validate: Official EN16931/Peppol conformance corpora; ruleset/version metadata; XRechnung/Factur-X/ZUGFeRD updates; artifact redistribution terms; deterministic rule IDs/effective dates; cross-check `hupe1980/en16931`, `MuhDur/invoicekit` and `attestwire/en16931`.
- Evidence gap: Multiple rights-clean implementations now exist. The priority is correlated-error reduction and authoritative ruleset/version provenance, not another parser.
- Done when: Same public corpus is run through at least two independent implementations/reference validators and each result cites parser version, ruleset/effective date, source artifact and exact failing business rule.

### P2 — lab automation rights/runtime + evidence pilot
- Best lanes: Hunter 20, 21, 40.
- Search/validate: Vendor SDK/runtime licensing for the highest-value `galago-tools` drivers; simulated/public instrument endpoints; GLAS failure/persistence behavior; OpenAPI-to-SiLA2 conformance; Flowcept provenance across instrument + analysis tasks.
- Evidence gap: The permissive stack is unusually strong, but deployment depends on per-instrument rights/hardware validation and one concrete cell-level economics benchmark.
- Done when: One simulated/lawfully accessible instrument plus one OpenAPI service execute a multi-step workflow with reproducible Flowcept lineage, measured integration hours and a rights/runtime matrix.

### P2 — semiconductor equipment interoperability wedge
- Best lanes: Hunter 12, 40, 43.
- Search/validate: Permissive higher-level GEM/E87/E90/E94/E116 workflow layers around MIT `mkjeff/secs4net`; host/equipment simulators; conformance fixtures; standards-content rights; buyer pricing for OEM/fab integration labs.
- Concrete queries/families: `SECS GEM simulator MIT`, `E87 E90 E94 open source`, `SECS II conformance tests`, `GEM equipment simulator Apache`, `semiconductor equipment integration test harness`.
- Evidence gap: `secs4net` supplies a mature rights-clean SECS-II/HSMS base, while the richer higher-level workflow reference found is proprietary. Determine whether a lawful standards/customer-spec path can turn it into a high-ticket interoperability service without recreating too much.
- Done when: A rights-clean host↔equipment harness runs representative sessions/messages and an independently specified higher-level GEM workflow with measurable integration/testing value.

## Resolved / deprioritized directions
- Generic freight/TMS discovery is deprioritized. `open_tms` is sufficient for product context; `Kareya-Silo` now supplies Apache freight rating and Qatoto supplies MIT rate-card provenance/versioning. Hunt source-document extraction, clause entitlement and settlement validation instead.
- The search for a rights-clean freight tariff/rerating core is resolved by `sengtha/Kareya-Silo`; the search for rights-clean rate authoring/supersession controls is resolved by the Qatoto freight subsystem.
- Generic construction takeoff and generic IFC-diff discovery are deprioritized. OpenTakeoff + BIMChange-Agent cover the strongest current rights-clean measurement/revision layers; focus on 2D correspondence and entitlement.
- Generic SAM.gov feed/regulation wrapper searches are deprioritized. `sam-search`, `capture-mcp-server`, official USAspending, `cliwant/mcp-sam-gov` and `1102tools-dev/federal-contracting-mcps` cover the source substrate; focus on correctness benchmarks.
- Generic compliance-collector search is deprioritized after `clay-good/attestful`; focus on minimum scopes, provenance and paid-pilot evidence quality.
- Generic TR-369 controller/agent discovery is deprioritized after Oktopus + OB-USP-Agent + agent-sim. Focus on scale, tenancy, migration fixtures and rights around BBF data models.
- Generic warehouse slotting/layout discovery is deprioritized after `agritheory/inventory_tools` + `gokhanozden/gabak`; the next step is a neutral CSV benchmark with measured travel/labor ROI.
- Generic RPA platforms are deprioritized after `lorisunjunbin/petp`; only hunt orchestration when it closes a specific high-value vertical workflow or security gap.
- Generic academic CVRP/route-optimization hunts are deprioritized. Revisit routing only when tied to a specific buyer dataset and measured advantage over permissive modern baselines.
