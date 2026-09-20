# Hunt 07 referral — outage outcome + economic consequence intelligence

Date: 2026-09-20
Node: 07 Geo Asset Intel
Purpose: durable cross-agent handoff for newly verified outage-outcome/economic-consequence findings. Integrator should merge qualifying entries into the relevant catalog/index; this sidecar avoids unsafe whole-file replacement of large concurrently edited hunter catalogs.

## BEST NEW FIND — PNNL Event-correlated Outage Dataset in America (USECPO)
- Canonical source: https://catalog.data.gov/dataset/event-correlated-outage-dataset-in-america
- Data landing page: https://data.openei.org/submissions/6458
- Exact dataset state inspected: Data.gov catalog checked 2026-09-10; dataset modified 2026-07-27; current resource `Outage Dataset v2.zip`.
- Category: Dataset / Validation Component / Business Opportunity
- Status: strong / integrator promotion candidate
- Concrete capability: national event-correlated outage benchmark built from EAGLE-I county outages (2014–2023, 15-minute), DOE-417 major disturbance events, and county population; correlates outage trajectories to DOE-417 events by geography and event start/end and emits event-level metrics.
- Why unusual: converts raw outage rows + formal disturbance reports into an event-aligned outcome surface suitable for frozen risk/pre-position/restoration benchmarks; saves substantial event-window/harmonization work.
- Evidence inspected: first-party Data.gov/OEDI metadata, current resource inventory, modification date, source lineage, access/use metadata. Data.gov records `license=https://creativecommons.org/licenses/by/4.0/` and `accessLevel=public`.
- Rights/provenance: dataset metadata explicitly CC BY 4.0. EAGLE-I, DOE-417, Census source lineage remains separately attributable; derived-commercial use still should preserve exact-source provenance and avoid assuming causal attribution from event correlation alone.
- Buyer/problem: utilities, resilience consultancies, insurers, infrastructure/site teams that need defensible historical outage-event outcomes rather than another hazard layer.
- First paid wedge: fixed-price portfolio/grid resilience calibration report — freeze risk ranking before event windows, resolve against USECPO outage outcomes, report event-level calibration, false negatives, lead-time lift and consequence-weighted misses.
- Build/data advantage: approximately 4–8 months of national outage/event correlation, cleaning, event metrics and documentation for a comparable benchmark.
- Score: A4 B5 C5 D4 E5 F4 = **27/30**.
- Strongest objection: it is EAGLE-I-derived and DOE-417/event-threshold biased, so it is not independent truth for an EAGLE-I-trained model and will underrepresent smaller/local events.
- Combination: `frozen forecast/site risk -> USECPO event outcome -> ICE 2.2 interruption cost -> OpenIPDM/GIAMS intervention economics -> inspection/restoration action`.
- Next action: reproduce a 2019–2023 development split and reserve 2025 EAGLE-I as a later out-of-time challenger; add an independent live/regulator spot-check source to measure circularity.

## STRONG TECHNICAL ARTIFACT — ORNL ODIN public-outage profile
- Canonical docs: https://odin.ornl.gov/downloadables/CIM/PubOutages.html
- Category: Standard/Profile / Operational Schema / Reusable Component
- Status: strong component
- Concrete capability: operational outage state model distinguishing `outageKind` verified vs estimated, `metersAffected`, `originalMetersAffected`, `customersRestored`, `reportedStartTime`, actual/estimated periods, ETR, incident linkage, outage area, crew status and cause.
- Evidence inspected: ORNL profile documentation plus current CIM-aligned implementation evidence in `zepben/ewb-grpc@f9cbf46d72617001e56e2076b7ecb28dd16b0311`, specifically `spec/TC57CIM/IEC61968/Operations/Outage.yaml`, which also associates outages with faults, equipment, usage points, crews, switch actions and switching plans.
- Rights/provenance: `zepben/ewb-grpc` is MPL-2.0. Underlying IEC CIM / MultiSpeak standards and specifications are independently governed; repository/public documentation does not silently grant rights to reproduce controlled standards text.
- Buyer/problem: utility/outage/resilience systems that currently collapse observed, estimated, crew and restoration state into one untyped outage row.
- First paid wedge: use the profile as the acceptance schema for authorized outage integrations and resilience evidence reports, preserving measured/estimated/operational state explicitly.
- Score: A4 B5 C5 D4 E4 F3 = **25/30**.
- Strongest objection: schema interoperability is not proof of source completeness, timeliness or utility adoption.
- Next action: map USECPO/EAGLE-I + one authorized/live utility feed into a reduced ODIN/CIM state model and require provenance-preserving round-trip tests.

## WATCH COMPONENT — eau-claire-energy-cooperative/simple-multispeak
- URL: https://github.com/eau-claire-energy-cooperative/simple-multispeak
- Exact revision: `dc5698f2237668cbc53da645b4d5c18a8335ede6`
- Status: watch component
- What was verified: LGPL-3.0 Java library with real source, generic MultiSpeak method calls, runtime `GetMethods` discovery, `PingURL`, v3/v4.1 header/auth handling, XML endpoint loading and failure tests. README/source explicitly account for vendor endpoints implementing only subsets of methods.
- Evidence inspected: `src/main/java/com/ecec/rweber/multispeak/MultiSpeakService.java`; `src/test/java/com/ecec/rweber/multispeak/MultiSpeakUtilityTest.java`; repository metadata/license/current revision.
- Limitation: no outage-specific end-to-end workflow, live vendor-conformance corpus or broad protocol regression suite was verified.
- Score: A3 B3 C4 D3 E3 F4 = **20/30**.
- Combination: practical adapter/reference behind the ODIN operational schema when a buyer has an authorized MultiSpeak endpoint.
- Next action: do not elevate unless a real utility-authorized endpoint benchmark shows materially lower integration effort or catches vendor-specific semantic differences.

## REJECT / NEGATIVE KNOWLEDGE — pnnl/ms-speak
- URL: https://github.com/pnnl/ms-speak
- Exact revision: `2dc5e99b113c4fe0568bd658de3fd55822ed90ae`
- Status: reject/deprioritize
- Evidence: current archived revision contains a Windows installer, a short README and a video; no current source/test tree was present. GitHub reports no public license. Latest commit is an archive notice/merge.
- Negative knowledge: DOE/PNNL affiliation plus a promising repository name is not evidence of reusable code. Inspect the current tree before assuming a standards/integration asset exists.
- Score: **12/30** (low evidence/completeness and deployment/reuse clarity).

## OUT-OF-TIME DATA UPDATE — EAGLE-I 2025
- Canonical metadata: https://doi.ccs.ornl.gov/dataset/c09fce3f-5faa-54ef-878a-cb0af6851cb6
- DOI: `10.13139/ORNLNCCS/3012826`
- Release date: 2026-02-19
- Capability delta: county-level 2025 outage observations at 15-minute intervals create a later outcome year beyond the 2015–2024 histories commonly used for model development.
- Companion customer-denominator dataset: DOI `10.13139/ORNLNCCS/3022751`, released 2026; combines 2023 EIA-861 customers, 2021 HIFLD territories/LandScan, and 2025 EAGLE-I data with modeled/collected/mixed customer-count type.
- Experiment impact: for any model frozen using data through 2024 or earlier, prefer 2025 as the untouched final temporal holdout rather than another random/hash split.
- Rights: exact dataset reuse/redistribution terms were not established from the inspected ORNL metadata; confirm before commercial embedding. Use only as permitted until rights are explicit.

## RIGHTS-CLEAN LIVE ACCEPTANCE SOURCE — California OES Power Outage Incidents
- Canonical source: https://sandbox.data.ca.gov/dataset/power-outage-incidents
- Current metadata inspected: updated 2026-09-10; license public domain.
- What it contains: automatically refreshed every 15 minutes from PG&E, SCE, SDG&E and SMUD public outage maps; points for all four and rough polygons for PG&E.
- Important limitation: only current/recent state, no historical archive.
- Use: rights-clean prospective/live spot-check and ingestion acceptance surface, not retrospective model-development truth.
- Score: A4 B4 C4 D3 E4 F5 = **24/30**.

## ECONOMIC CONSEQUENCE LAYER — ICE Calculator 2.2 + ORNL outage-cost analysis
- Canonical tool: https://icecalculator.com/
- Current versions: `interruption.2.2.0` and `reliability.2.2.0`, released 2026-02-19.
- Evidence: LBNL reports version 2.2 pools 15 independent surveys across 30 distribution service territories and nearly 10,000 customer responses; includes 90% confidence intervals. Phase 1+2 final report published 2026-02.
- Independent recent signal: ORNL analysis updated 2026-09-01 reports average annual major-outage burden above $67B over 2018–2024, $121B in 2024, and average 2024 commercial/industrial loss of $6,031 per outage; major-outage count rose from 4,666 (2018) to 6,533 (2024) and average duration from 9.6h to 11.8h.
- Capability delta: converts outage outcomes into buyer-relevant economic consequence so inspection/restoration policies can be scored on expected avoided interruption dollars rather than only outage counts/AUC/miles.
- Rights/operational caveat: ICE is an external service/API; its API/service/model terms and any key/access requirements are separate from repository permissions. Public reports are evidence, not an automatic right to embed proprietary model internals.
- Score as reusable technical/economic artifact: A4 B5 C5 D4 E5 F3 = **26/30**.
- Combination: `USECPO/EAGLE-I outcome -> ICE 2.2 consequence -> GIAMS/OpenIPDM intervention economics -> route/crew policy`.
- Next action: create an economic scorecard with uncertainty ranges and compare policies on expected avoided interruption dollars per crew-hour while keeping model uncertainty and observed outage truth separate.

## WATCH — LBNL PRESTO
- URL: https://presto.lbl.gov/
- Capability: simulates customer-level interruption timing/duration for any CONUS county over 1,000–20,000 synthetic years, trained on hourly county PowerOutage.US data from 2017–2021; API supports batch simulation.
- Status: watch / stress-test component, not observed truth.
- Value: useful for rare-event/counterfactual stress testing and experiment power analysis.
- Caveat: synthetic and trained on a commercial/proprietary-derived outage history; do not use as independent empirical validation of a model trained on overlapping outage sources.
- Score: **22/30**.

## ACTIVE HYPOTHESIS
STATUS: strengthened.
HYPOTHESIS: the defensible commercial moat is shifting from `hazard/risk score` to `outcome-priced operational evidence`: frozen prediction -> typed outage observation -> event correlation -> interruption-dollar consequence -> action -> later recovery/outcome.
SUPPORTING EVIDENCE: USECPO CC BY event benchmark; 2025 EAGLE-I later holdout; ODIN/CIM operational outage state; California public-domain live feed; ICE 2.2 economic valuation; existing OpenIPDM/GIAMS/inspection/restoration components.
CONTRARY EVIDENCE: substantial circularity remains because many public outage products ultimately derive from EAGLE-I/public utility maps; asset-level failure/work-order truth is still scarce; standards/API rights and operational adoption vary.
NEXT TEST: freeze a pre-2025 risk/policy stack, score on 2025 outages by event block, spot-check a subset against independent regulator/live utility sources, and compare simple vs optimized policies on expected avoided interruption dollars per crew-hour.
CONFIDENCE: high that this is the highest-value next experiment; moderate that public data alone will support buyer-grade asset-level claims.

## VALUE HANDOFF
1. CAPABILITY DELTA — adds a rights-clean major-disturbance/outage benchmark (USECPO), a canonical operational outage schema (ODIN/CIM), a later 2025 outcome year, and a modern interruption-dollar valuation layer (ICE 2.2).
2. GRAPH EDGE — strengthens `CAP-015 prospective prediction evidence -> observed outage outcome -> economic consequence -> inspection/restoration decision`.
3. RADAR SIGNAL — supports an emerging category of **outcome-priced grid decision intelligence**, where proof and later service outcomes matter more than another hazard model.
4. EXPERIMENT IMPACT — replace random/hash splits with storm/event-blocked chronological holdout; reserve 2025 where possible; score false negatives and policies in dollars and crew-hours; add independent spot checks to quantify EAGLE-I circularity.
5. COMMERCIAL IMPACT — strongest first wedge is a fixed-price Grid Resilience Calibration / Acceptance Audit for a site/portfolio/utility territory, with recurring monitoring only after outcome accuracy and source rights are established.
6. NEGATIVE KNOWLEDGE — EAGLE-I-derived datasets are not independent truth for EAGLE-I-trained systems; satellite inference is not OMS truth; current repo names/affiliation do not prove source depth; standards text and external APIs remain separately governed.

## CROSS-AGENT REFERRAL
- MASTER Integrator: evaluate USECPO for DATASETS/MASTER-equivalent promotion and add an experiment for event-blocked 2025 validation + interruption-dollar scoring.
- Utility/inspection/restoration lanes: exact unanswered question — **does risk-priced inspection/restoration materially improve expected avoided interruption dollars per crew-hour versus scheduled, nearest-route and highest-risk-first baselines on the same event/asset population?**

## RUN-11 FOLLOW-UP — OWL-I rights gate + EXP-012 benchmark hardening
- Date/time: 2026-09-20 10:06 ET automation run.
- **OWL-I rights gate resolved fail-closed, not positively licensed:** the current Zenodo v1 record `10.5281/zenodo.20433558` renders a `Rights -> License` heading with no license value. Zenodo's own licensing documentation says the license field is required and defaults new records to CC BY 4.0, while Zenodo policy says use/reuse is subject to the license actually specified for the deposited object. The empty rendered OWL-I field is therefore an artifact-level inconsistency; do **not** infer that the data files carry CC BY 4.0 merely from Zenodo's platform default. The EarthArXiv manuscript is CC BY-NC-ND 4.0, but that manuscript license does not establish a license for the 51.4 GB dataset files.
- **Operational consequence:** retain OWL-I as a high-value research/validation candidate but keep commercial redistribution/embedding permission `UNKNOWN/BLOCKED` until the depositor or corrected machine-readable metadata explicitly supplies the dataset license. Upstream NASA/LandScan/EAGLE-I terms do not cure a missing grant on the derivative OWL-I artifact.
- **USECPO remains executable now:** Data.gov/OEDI explicitly exposes `license=https://creativecommons.org/licenses/by/4.0/`, public access, current `Outage Dataset v2.zip` (29.81 MB), and `Data Guidelines v2.docx`; dataset modified 2026-07-27. This is the correct current historical benchmark for EXP-012 while OWL-I remains rights-blocked.
- **WeatherNext challenger rechecked beyond README:** `biplovbhandari/weathernext-outage-forecasting@e2ddf4850ec26202530003cc9488727eaa63f14d` is Apache-2.0 and builds a 6-hour county training table from WeatherNext features plus EAGLE-I outage ratios. However `sql/ml/01_bqml_training_data.sql` labels its split 'date-based to avoid temporal leakage' while actually hashing `county_fips + DATE(valid_ts)` modulo five into TRAIN/TEST. Dates are therefore distributed across both partitions; this is not a future-only temporal holdout and cannot support a prospective-performance claim.
- **EXP-012 corrected benchmark contract:**
  1. Freeze source/model/policy version before seeing each evaluation block; preserve forecast initialization/vintage where forecasts are used.
  2. Keep every county observation associated with the same DOE-417 disturbance in one event block; never split one storm/event across train/test merely because county/date hashes differ.
  3. Prefer chronological development/evaluation. With USECPO's 2014–2023 EAGLE-I lineage, a practical first pass is development through 2021, tuning on 2022, untouched event-blocked test on 2023. Use 2025 EAGLE-I only after its exact reuse terms are resolved; do not silently mix it into development.
  4. Primary observed outcomes: peak outage fraction/customers, customer-hours out, restoration duration/recovery curve where present. Primary predictive metrics: calibration/Brier score, precision-recall under class imbalance, false-negative customer burden, and recall at a fixed operational action budget.
  5. Economic consequence is a separately governed modeled layer, not observed avoided cash: report interruption-cost ranges separately from observed outage outcomes. Never label modeled ICE consequence as realized savings.
  6. If the evaluated model was trained on EAGLE-I labels, USECPO is **not independent external truth** because it derives from EAGLE-I. USECPO can still enforce event blocking and later-time evaluation, but promotion requires an independent regulator/authorized utility/live spot-check plane.
  7. Do not claim routing/crew-hour superiority from county outage data alone. Nearest-route/scheduled/optimized crew baselines require an explicit authorized asset/depot/crew population; until then, evaluate only forecast/risk ranking and action-budget allocation.
- **Capability delta:** converts the current grid experiment from 'use more outage data' into an auditable acceptance test with source ancestry, event blocking, forecast-vintage freezing, observed-vs-modeled outcome separation and an explicit independent-validation gate.
- **Graph edge:** strengthens `CAP-015 -> EXP-012` and challenges the WeatherNext repository's historical evidence claim without rejecting its operational product shell.
- **Radar signal:** strengthens proof-carrying / prospective-prediction practice; it does not justify a new radar score because no independent held-out buyer result has yet been produced.
- **Commercial impact:** the paid wedge remains a Grid Resilience Calibration / Acceptance Audit, but claims must be limited to observed outage calibration and modeled consequence until authorized asset/work-order/restoration truth exists.
- **Negative knowledge:** platform default licenses are not substitutes for artifact-level grants; 'date-based' comments are not evidence of chronological evaluation; event-correlated EAGLE-I derivatives cannot serve as independent truth for EAGLE-I-trained models.
- **Next exact question:** can the current USECPO v2 files/guidelines support a deterministic event-block manifest and observed-outcome scorecard without relying on any ambiguous upstream field interpretation, and which one independent rights-clean source can falsify a subset of those event outcomes?