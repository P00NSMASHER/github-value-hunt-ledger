# SEARCH QUEUE

Integrator-owned queue for the next highest-value searches. Keep this list short: hunters should close evidence gaps, not repeatedly rediscover solved infrastructure.

## Rules
- Only the integrator writes this file.
- Hunters read it every run and act on leads relevant to their assigned portfolios.
- Prioritize unresolved leads with high commercial upside, scarce public data/domain logic, large build-time compression or strong cross-repository combination potential.
- Remove or mark leads resolved when evidence has been cataloged.

## Priority leads

### P0 — freight contract-source extraction + clause entitlement (last major technical blocker)
- Best lanes: Hunter 03, 17, 42, 47.
- Search/validate: Rights-clean freight-specific parsing of real carrier/forwarder XLS/PDF rate sheets into Qatoto/Kareya structures; borderless/transposed tables; multi-page zones; CWT/weight breaks; container-size columns; accessorial/fuel clauses; amendments; effective dates; exact source-cell/page references; reviewer corrections; explicit ambiguity states.
- Known progress: `sutasmantas/invoice-extraction-pipeline@337cac1fc43af32652683b353cb1cab3c765eb8b` gives MIT provenance/correction plumbing, while no-license `drkcutie/kahayag@15fdcc1d85dce404b1c20de84cab0d4694c85c2f` exposes useful ocean-rate table cases only as clean-room requirements. Kareya and Qatoto already solve deterministic rating/version control.
- Concrete queries/families: `freight rate sheet xlsx parser MIT`, `carrier tariff PDF parser Apache`, `ocean freight rate table parser`, `CWT rate table parser`, `fuel surcharge schedule parser`, `accessorial clause extraction freight`, `rate confirmation parser license`.
- Done when: Representative borderless/transposed/weight-break/container-rate sheets round-trip into the canonical rate model with source references and reviewer confirmation, and at least one accessorial entitlement is tied to an exact clause. Any unresolved source or clause ambiguity produces $0 asserted recovery.

### P0 — freight 20-case contract→EDI→settlement benchmark
- Best lanes: Hunter 03, 07, 30, 36, 42, 47.
- Build/validate rather than keep searching generically: `yurii1exe/freight-dispatch-board@5128cd9af0e2dbacc37d3030ad8fc605da42168d` can generate a rights-clean synthetic 204/status/210 freight lifecycle; `apimeister/x12-types@e8238385d9f4a8a21b6e4525f5ab3acc7bed3978` adds tested 210/820 parsing; `europeanplaice/subset_sum@62fe41b4c8f5d287d1904f573a9594cac254d340` and `Etherlabs-dev/multi-processor-reconciliation@2f9397fbe56a76abeee42a01a37536ad1811a806` add conservative settlement allocation.
- Evidence gap: Verify provenance/redistribution rights for any standards-derived X12 definitions/fixtures; map BPR/TRN/RMR/ADX and credit-memo evidence to specific findings without false many-to-many matches; prove duplicate and near-tie ambiguity behavior.
- Required cases: 204→214/status→210; exact billed-vs-contracted variance; duplicate charge; accessorial; fuel; weight/zone/rate-break boundary; superseded contract; ambiguous clause; 820 payment/adjustment; one-to-many and many-to-many credit; duplicate/near-tie remittance; partial settlement; unsupported/ambiguous mapping.
- Done when: At least 20 lawful cases have exact expected recoverable amount, contract revision, source evidence, claim/dispute state and settlement state. Ambiguous parsing, entitlement or allocation must produce $0 asserted recovery.

### P0 — ScopeSignal 2D revision + entitlement-to-dollar benchmark
- Best lanes: Hunter 04, 17, 38, 42, 45.
- Search/validate: Rights-clean 2D PDF/CAD registration and revision correspondence; revision clouds/change markers; symbol/object correspondence; RFI/submittal-to-drawing links; contract-scope entitlement; quantity-delta attribution.
- Known progress: BIMChange-Agent covers rights-clean IFC correspondence and OpenTakeoff covers calibrated 2D quantities. Do not hunt more generic takeoff/IFC-diff engines unless they materially beat those benchmarks.
- Done when: One old/new IFC case and one old/new PDF-plan case preserve revision/element identity through quantity delta, contract/spec evidence and human-reviewed proposed dollar impact.

### P0 — CaptureBrief identity, packet completeness + regulatory-currency benchmark
- Best lanes: Hunter 05, 18, 42.
- Validate: UEI/CAGE/recipient joins across SAM.gov/USAspending; PIID/IDV lineage; opportunity amendment/attachment completeness; exact FAR/DFARS clause/prescription resolution; Acquisition.gov deviations/FAR Overhaul applicability; source timestamps/hashes.
- Known progress: sam-search, capture-mcp, official USAspending, cliwant/mcp-sam-gov and 1102tools cover the source substrate. Stop generic SAM/regulatory wrapper search.
- Done when: Ten current solicitations yield manually verified opportunity→entity→award/incumbent→competition/set-aside→clause/prescription→current-deviation packets with explicit timestamps/hashes and measured false joins/unresolved states.

### P0 — continuous-compliance paid-pilot evidence package
- Best lanes: Hunter 14, 15, 40, 42, 47.
- Validate: Attestful collector scopes/read-only guarantees, pagination/failure semantics, Evidentia tenancy/auth boundaries, restore-drill/RestoreLab evidence artifacts, fail-closed recovery reporting and exact OSCAL control mapping.
- Search only when it closes a concrete gap: PostgreSQL/PITR/content-fidelity proof, evidence freshness/expiry, cryptographic binding of evidence to tool/config/environment, or a buyer-required backup provider.
- Done when: One synthetic AWS/GitHub bundle plus one disposable PostgreSQL restore lands in a versioned control package; an injected restore failure and missing-evidence case both stay non-pass; manual correction time and missing-evidence rate are measured.

### P1 — PermitPlate national permit/public-source normalization benchmark
- Best lanes: Hunter 06, 18, 42.
- Validate: `harlanljones/urban-signal@f3ac0e1141ddfed286a704652087e85d9803c060` as a source-normalization layer across Socrata/ArcGIS/CKAN/CARTO/CSV; city coverage, schema drift, permit-value/unit normalization, geocoding/entity linkage and source-by-source rights/terms.
- Commercial question: Whether normalized permit velocity/capex signals materially improve lead precision over PermitPlate's current city-specific logic.
- Done when: A lawful multi-city benchmark scores source freshness, schema breakage, duplicate/property linkage and lead yield on at least three materially different municipal systems.

### P1 — GST GSTR-2B/IMS current-rule benchmark
- Best lanes: Hunter 47, 31, 42, 18.
- Validate: Current official GSTN/GSTR-2B and Invoice Management System states; accepted/rejected/pending behavior; credit/debit-note effects; amendments; ineligible/reversal cases; current schemas; accountant-grade synthetic/public fixtures.
- Known progress: Rekvia is a strong MIT matching engine but is not a complete 2026 IMS-aware control model.
- Done when: A versioned corpus covers exact/fuzzy/duplicate matching plus IMS states, amendments, credit notes and ineligible/reversal cases with authoritative rule citations and human/accountant eligibility review before monetary claims.

### P1 — TR-069→USP production/migration validation
- Best lanes: Hunter 35, 42.
- Validate: Oktopus tenant isolation/fleet scale/dependency health; OB-USP-Agent + agent-sim concurrency; CWMP↔USP migration/state mapping; BBF data-model rights; current ISP buyer pain/pricing.
- Done when: A rights-clean lab demonstrates CWMP and USP workflows on concurrent simulated devices with migration fixtures, tenant-isolation evidence and resolved data-model rights.

### P1 — structured e-invoice conformance/version provenance
- Best lanes: Hunter 42, 07, 31.
- Validate: Official EN16931/Peppol conformance corpora; ruleset/version metadata; XRechnung/Factur-X/ZUGFeRD updates; artifact redistribution terms; cross-check `hupe1980/en16931`, `MuhDur/invoicekit` and `attestwire/en16931`.
- Done when: The same public corpus runs through at least two independent implementations/reference validators and each result records parser version, ruleset/effective date, source artifact and exact failing business rule.

### P2 — lab automation runtime/rights + evidence pilot
- Best lanes: Hunter 20, 21, 40.
- Validate: Vendor SDK/runtime rights for the highest-value Galago drivers; simulated/public instrument endpoints; GLAS failure/persistence behavior; OpenAPI-to-SiLA2 conformance; Flowcept provenance across instrument + analysis tasks.
- Done when: One simulated/lawfully accessible instrument plus one OpenAPI service execute a multi-step workflow with complete Flowcept lineage, measured integration hours and a rights/runtime matrix.

### P2 — semiconductor equipment interoperability wedge
- Best lanes: Hunter 12, 40, 43, 45.
- Search/validate: Permissive higher-level GEM/E87/E90/E94/E116 workflows around MIT `mkjeff/secs4net`; host/equipment simulators; conformance fixtures; standards-content rights; buyer pricing for OEM/fab integration labs.
- Done when: A rights-clean host↔equipment harness runs representative sessions/messages and an independently specified higher-level workflow with measurable integration/testing value.

## Resolved / deprioritized directions
- Generic freight/TMS/rating discovery is resolved enough for launch work: Open TMS + Kareya + Qatoto are the current base. Hunt source-document/entitlement correctness, not another TMS.
- Generic X12 204/210/214/820 parser discovery is deprioritized after `freight-dispatch-board` + `x12-types` + `edi-x12-toolkit`. Verify standards-content provenance and build the benchmark instead.
- Generic payment-reconciliation/subset-sum discovery is deprioritized after `subset_sum` + Etherlabs. Work domain constraints, ambiguity/false-match tests and settlement evidence linkage.
- Generic construction takeoff and generic IFC-diff discovery are deprioritized after OpenTakeoff + BIMChange-Agent.
- Generic SAM.gov feed/regulation wrappers are deprioritized; work identity/packet/currency correctness.
- Generic compliance collectors are deprioritized after Attestful; generic restore tools are also lower priority after restore-drill/RestoreLab. Hunt only concrete proof gaps or required providers.
- Generic TR-369 controller/agent discovery is deprioritized after Oktopus + OB-USP-Agent + agent-sim.
- Generic warehouse slotting/layout discovery is deprioritized after inventory_tools + GABAK; next step is measured ROI.
- Generic RPA platforms are deprioritized after PETP; only hunt orchestration that closes a specific high-value vertical/security gap.
- Generic academic CVRP/route-optimization hunts are deprioritized unless tied to a buyer dataset and measured advantage over permissive modern baselines.
