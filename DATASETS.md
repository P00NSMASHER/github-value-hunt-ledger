# Datasets & Data Pipelines

Cross-lane index maintained by Hunt 15 MASTER Integrator.

Use this file for high-value public datasets, data pipelines, APIs, reference tables, historical archives, schemas, normalization/entity-resolution assets, and hard-to-recreate lawful data advantages discovered by the hunters.

For each entry record:
- Repository / source
- Canonical URL
- Exact revision / date inspected
- Dataset or pipeline description
- Coverage / freshness / format
- Evidence inspected
- Actual published license / rights metadata
- User-asserted separate commercial authorization posture
- Buyer / problem
- Monetization or product use
- Build-time / data advantage
- Value score
- Combination opportunities
- Next action

Do not store credentials, tokens, private/personal data, or raw accidental secrets.

## Elite indexed sources — 2026-09-20

### GSA/srt-fbo-scraper — solicitation packet/history acquisition pipeline
- Repository / source: https://github.com/GSA/srt-fbo-scraper
- Exact revision: `fbdfa86a2bce4323a5afacda04f083698cab02e1`.
- Dataset / pipeline: official GSA implementation that pages SAM Opportunities v2, canonicalizes agency/office context, downloads solicitation attachments including malformed-link cases, extracts DOC/RTF/DOCX/PDF text and maintains solicitation/history state.
- Coverage / format: opportunity metadata + attachment packet/history acquisition and normalized extracted text; live SAM/source-system freshness and terms remain external.
- Evidence inspected: implementation, attachment/history behavior and extraction paths as recorded in MASTER.
- Published rights: CC0-1.0 for repository work; SAM/source data terms/status remain separate.
- Standing permission posture: repository-owned content treated as commercially authorized under the user's standing assertion; third-party/source-system data remains separately governed.
- Buyer / problem: federal capture/proposal teams need the controlling packet and amendment history, not just an opportunity summary.
- Product use: CaptureBrief packet-completeness and source-evidence layer.
- Build/data advantage: removes substantial attachment/history edge-case engineering and provides a first-party operational lineage.
- Value score: **28/30** — A4 B4 C5 D5 E5 F5.
- Combination: GSA FAR + USAspending + DATA Act broker + FAR Overhaul/deviation evidence.
- Next action: 10-live-solicitation packet-completeness benchmark with exact source artifact/hash and amendment-history verification.

### GSA/GSA-Acquisition-FAR — machine-readable FAR authority corpus
- Repository / source: https://github.com/GSA/GSA-Acquisition-FAR
- Exact revision: `da52ccbbe114e1f031a7f4c59195c508dbfa485f`.
- Dataset / pipeline: official Acquisition.gov FAR DITA with clause/provision structure, fill-in metadata, FAC revision markers, FAR Case identifiers and change provenance.
- Coverage / format: machine-readable FAR regulatory source; agency deviations and solicitation-specific fill-ins remain separate evidence.
- Evidence inspected: structured clause/provision and revision metadata as recorded in MASTER.
- Published rights: official FAR/regulatory text is authoritative public-law/regulatory material; no blanket permissive software license was established for every packaging artifact.
- Standing permission posture: repository-owned code/content is treated as commercially authorized under the user's standing assertion; this does not expand rights in separately owned standards/assets.
- Buyer / problem: capture/proposal teams need exact current clause text, revision and fill-ins instead of stale summaries.
- Product use: CaptureBrief clause reconstruction and rule-currency baseline.
- Build/data advantage: replaces ad-hoc scraping/search with a first-party structured regulatory source.
- Value score: **29/30** — A5 B5 C5 D5 E5 F4.
- Combination: solicitation packet/history + FAR Overhaul agency deviations + SAM/USAspending/DATA Act identity/award lineage.
- Next action: validate deviation applicability and supersession on 10 live solicitations.

### fedspendingtransparency/usaspending-api — federal award/procurement evidence pipeline
- Repository / source: https://github.com/fedspendingtransparency/usaspending-api
- Exact revision: `1692d484b38c66361c54faa221548527cae29964`.
- Dataset / pipeline: official USAspending server/ETL schemas and implementation for award, procurement, recipient and spending data.
- Coverage / format: federal award/procurement/recipient/spending semantics and ETL; upstream source-system caveats remain external.
- Evidence inspected: server/ETL schemas, implementation and tests as recorded in MASTER.
- Published rights: CC0-1.0 for the official repository; source-system caveats separate.
- Standing permission posture: repository-owned material treated as commercially authorized; underlying source data remains governed by its authoritative source terms/status.
- Buyer / problem: GovCon teams need defensible incumbent, award and spend lineage without reverse-engineering semantics.
- Product use: CaptureBrief historical award/incumbent/spend evidence.
- Build/data advantage: official upstream schemas/lineage materially reduce false award and incumbent joins.
- Value score: MASTER-promoted authoritative source; no separate /30 was recorded in the current source entry.
- Combination: DATA Act broker identity + SAM opportunity/packet + FAR/deviation evidence.
- Next action: validate PIID/referenced-IDV and parent-entity joins against live solicitation samples.

### fedspendingtransparency/data-act-broker-backend — federal identity/procurement normalization
- Repository / source: https://github.com/fedspendingtransparency/data-act-broker-backend
- Exact revision: `76dcae4ccbf6951223608bc1d8fd0c5b03da5d68`.
- Dataset / pipeline: official DATA Act broker semantics for UEI/DUNS/legal/DBA/parent identities, addresses/business types and procurement/referenced-IDV identifiers.
- Coverage / format: normalized federal award/recipient/identifier semantics and validation logic.
- Evidence inspected: schemas/validation/identity semantics recorded in MASTER.
- Published rights: CC0-1.0; downstream/source-system caveats separate.
- Standing permission posture: repository-owned material commercially authorized under the standing assertion; source-system data separately governed.
- Buyer / problem: false entity/parent/PIID joins can invalidate capture conclusions.
- Product use: CaptureBrief identity/award normalization and contradiction checking.
- Build/data advantage: hard-to-recreate first-party identity/procurement semantics.
- Value score: **29/30** — A4 B5 C5 D5 E5 F5.
- Combination: USAspending + SAM packet + FAR/deviation layer.
- Next action: benchmark parent/PIID/referenced-IDV conflict cases and require unresolved conflicts to remain unresolved.

### owgreen-dev/grid-crunch — leakage-safe interconnection-queue outcome pipeline
- Repository / source: https://github.com/owgreen-dev/grid-crunch
- Exact revision: `5f0c9a074d928b79caa792a84e8e92de1b2df3f2`.
- Dataset / pipeline: reproducible competing-risks/survival pipeline over independently acquired LBNL interconnection-queue history with fixed-horizon labels, strict `as_of <= entry_date` leakage contracts, temporal/out-of-cohort evaluation, calibration/lift, within-ISO testing and EIA-860M built-project corroboration.
- Coverage / freshness / format: historical U.S. interconnection-queue evidence; the repository intentionally does not redistribute the full LBNL workbook. Post-2021/post-FERC-Order-2023 cohorts are not yet fully observable at five-year horizons, so regime transfer is explicitly unproven.
- Evidence inspected: exact tree/commit, model/label/decision-log architecture, benchmark methodology, tests/CI and documented negative-feature experiments in hunter 11. Published benchmark values remain repository evidence until independently reproduced.
- Published rights: MIT for repository software. LBNL Queued Up, EIA-860M, HIFLD, gridstatus/ISO feeds and other upstream datasets retain independent rights/redistribution terms.
- Standing permission posture: repository-owned code/content commercially authorized; no extension to upstream public datasets.
- Buyer / problem: renewable/BESS developers, lenders/investors, equipment vendors and data-center/site teams need evidence-backed project-materialization ranking rather than queue counts or leakage-prone predictions.
- Product use: Queue Materialization Intelligence portfolio screen and historical validation backbone.
- Build/data advantage: roughly 4–8 months of censoring/label design, leakage controls, temporal validation, calibration and cross-source verification; negative results also prevent wasted feature engineering.
- Value score: **29/30** — A5 B5 C5 D5 E5 F4.
- Combination: historical scorer -> prospective snapshot/prediction ledger -> expected-MW/competition layer -> site/hosting engineering.
- Next action: reproduce from independently downloaded current lawful LBNL/EIA inputs; freeze an out-of-time scorer and keep all buyer-facing claims explicit about the pre-Order-2023 evidence regime.

### savabs/queue_attrition — content-addressed live queue archive + prospective prediction ledger
- Repository / source: https://github.com/savabs/queue_attrition
- Exact revision: `daf180778383b8675e252346e771a4e754f0558d`.
- Dataset / pipeline: daily/content-addressed multi-ISO queue snapshots, normalized request identities, historical cohorts/base rates, prospective prediction registry with fixed resolution deadlines, health/diff tooling and shared-frailty portfolio uncertainty.
- Coverage / freshness / format: live/recurring queue-state archive and append-only future-outcome ledger. Important inspected caveat: evaluation uses isotonic calibration while the current production `predict_active.py` path appeared to write raw pipeline probabilities; parity is not yet proven.
- Evidence inspected: source tree, snapshot data, model/predict/registry/frailty/CI code and exact revision recorded in hunter 11.
- Published rights: no root public LICENSE established at the inspected revision; repository-owned code covered by the user's separate-permission posture. ISO/gridstatus/source data retain independent terms.
- Standing permission posture: repository-owned code/content commercially authorized; no extension to captured upstream queue data.
- Buyer / problem: same Queue Materialization Intelligence buyers need immutable live history and prospectively falsifiable calls that cannot be rewritten after outcomes arrive.
- Product use: prospective evidence layer after grid-crunch historical validation; not yet production probability authority.
- Build/data advantage: roughly 4–7 months of queue snapshotting/versioning, identity resolution, prediction registry and portfolio-dependence design.
- Value score: **26/30** — A5 B5 C5 D5 E3 F3 at inspection because live calibration parity and upstream data-rights diligence remain unresolved.
- Combination: grid-crunch historical scorer -> queue_attrition live snapshots/prediction ledger -> correlated expected-MW/tail-risk reporting.
- Next action: force the live scorer to use the exact estimator/calibration contract validated out of time, freeze model/version/features and allow the append-only registry to accumulate genuinely prospective evidence before marketing calibrated live probabilities.

### HopkinsICARUS/ICARUS-PJM-Dataset — large synthetic PJM-like grid testbed
- Repository/source: https://github.com/HopkinsICARUS/ICARUS-PJM-Dataset
- Exact revision: `0cb6a1af86e2bdfc1d160f44b6e4a7518ca3ffe3`.
- Category: Dataset / simulation testbed.
- Capability: 17,467-bus synthetic PJM-like network and associated planning/resilience/queue/large-load analysis surfaces suitable for reproducible regional stress and infrastructure studies without using a customer production grid model.
- Rights: repository software MIT and repository data CC BY 4.0 as recorded in hunter 23/related grid lane; upstream/source-derived assumptions and any external standards remain separately governed.
- Score: **29/30** at inspection.
- Product use: falsifiable large-load/DER/queue/resilience benchmark before customer feeder/system models; useful for testing whether algorithms preserve electrical constraints at meaningful scale.
- Next action: define planted congestion/voltage/contingency/large-load scenarios with expected engineering outcomes; do not market the synthetic network as a utility's actual grid.

### garretlking1-commits/jobwalk — synthetic construction evidence archive
- Repository/source: exact repository/revision recorded in hunter 04 (`fdcb507...`).
- Category: Synthetic benchmark / evidence archive.
- Capability: rights-clean synthetic construction evidence corpus spanning project/change/payment/waiver-style records useful for testing document linking and claim-state logic without customer/private records.
- Score: **27/30** at inspection.
- Product use: ScopeSignal acceptance tests around evidence continuity, payment/waiver ambiguity and change-state joins.
- Integrity rule: synthetic records are regression fixtures, not empirical construction-market evidence; conditional waiver effectiveness remains UNKNOWN without cleared payment/remittance proof.
- Next action: add deliberately contradictory and missing-evidence cases and require fail-closed output.

### xiazeyu/FireDataForge — historical wildfire event feature factory
- Repository/source: https://github.com/xiazeyu/FireDataForge
- Exact revision: `4328d4f6bdbec5a3ab30bf786718d759fc4fb84c`.
- Category: Dataset pipeline / benchmark infrastructure.
- Capability: harmonizes perimeter/fireline, VIIRS, terrain, fuels/canopy, weather, recent burn, building/land-cover, Sentinel-2 and WUI-style context onto consistent projected event grids with caching, batch work, skip/failure reasons and validation tooling.
- Rights: MIT repository code; every underlying public/hosted source retains its own terms/provenance.
- Score: **27/30**.
- Product use: historical backtest corpus for STORCITO and infrastructure/utility wildfire-risk systems.
- Next action: build a source-rights matrix and a 20-event benchmark with deliberate missing-layer degradation tests.

### Saki et al. harmonized utility outages + NWS VTEC warnings — fresh outage/recovery outcome benchmark
- Source: https://zenodo.org/records/22651795 ; Zenodo record v2, DOI `10.5281/zenodo.22651795`.
- Exact version / date inspected: **v2**, published 2026-09-08; hunter inspection records a peer-reviewed *Scientific Data* Data Descriptor published 2026-09-19.
- Dataset: 2015–2024 CONUS event archive joining utility-reported EAGLE-I outage observations with NWS VTEC watches/warnings/advisories, including event IDs, outage peaks/durations, warning types, source-availability diagnostics and sensitivity artifacts for missing data, temporal aggregation and recovery-persistence assumptions.
- Coverage / freshness / format: national historical outage-warning/recovery evidence suitable for frozen historical replay and held-out event validation. It is observational outcome evidence, not causal proof that a warning or weather variable caused an outage.
- Evidence inspected: Zenodo v2 inventory and DOI metadata, peer-reviewed descriptor as recorded by hunter 23, plus upstream EAGLE-I documentation describing 15-minute public-utility-map observations and known source gaps/ambiguity. External web retrieval was attempted during integration but the fresh record was not yet accessible through the available web index, so this central entry preserves the hunter's inspected evidence rather than upgrading it.
- Rights: **unresolved for the harmonized v2 record at integration time**; the inspected Zenodo license field was not populated. Upstream EAGLE-I is separately described as CC BY 4.0 by the hunter, while NWS/Census/geometry sources retain their own terms. The standing GitHub commercial-permission assertion does not apply to this non-GitHub dataset.
- Buyer / problem: utilities, insurers/reinsurers, infrastructure owners and resilience analytics teams need operational outage/recovery truth to falsify hazard and crew-preposition models rather than validating only against simulations.
- Product use: historical storm/outage model calibration, frozen portfolio risk ranking, prospective forecast verification and recovery-sensitivity analysis. Do not sell raw redistribution rights until the harmonized-record terms are confirmed.
- Build/data advantage: hunter estimate **4–8 months** of EAGLE-I/VTEC harmonization, event construction, missingness diagnostics and recovery-sensitivity work.
- Value score: **27/30 — A4 B5 C5 D5 E5 F3**; rights clarity is the explicit gating dimension.
- Combination: `STORCITO / WeatherNext-style risk forecast -> frozen prediction -> later harmonized outage/recovery outcome`, with physrisk/ERAD/SIRA/OpenGIRA or pyrecodes providing consequence/recovery models where inputs are lawfully sourced.
- Next action: confirm harmonized-v2 reuse terms first; then reproduce a frozen 2019–2023 development replay and held-out 2024 benchmark with county/event calibration, lead-time lift, false-negative cost and missing-data sensitivity. Keep causal claims separate from observational association.

## Demoted / negative-control data assets

### aiparallel0/freight-audit — retain only as adversarial freight fixtures
- Repository / source: https://github.com/aiparallel0/freight-audit
- Exact revision: `e7869162cf9cb23f6d520a0cd71f87cf973d8c28`.
- Published rights: MIT for code and committed synthetic/PII-free fixtures; external benchmark assets retain separate attribution/rights.
- Revised status: **DEMOTED from elite/gold-truth use.** Later source-level adversarial inspection showed that the application's audit/value semantics are unsafe as a benchmark oracle: missing authority can become zero/default expected money, missing RateCon can still emit default-rate detention value, overlapping findings can be additively double-counted, and provisional/review-pending values can enter aggregate/usage/billing surfaces.
- Safe residual use: selected synthetic documents/cases can be retained as **negative-control fixtures** to test whether a candidate rejects missing authority, overlapping-economic-claim duplication and pre-review value leakage. Do not inherit the repository's aggregate savings/recovery labels as gold truth.
- Value posture: **not scored as an elite dataset/evaluation pipeline after demotion**; prior 28/30 promotion is superseded for authoritative evaluation use.
- Next action: independently hand-author expected dollars/authority states for any retained fixture before reuse in EXP-001. Re-promote only if the repository implements explicit authority tri-state, claim-level dedupe, adjudication-to-realization states, and tests proving only confirmed/realized claims enter aggregate/billing outputs.