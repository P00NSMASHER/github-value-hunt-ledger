# COMBINATIONS

Cross-repository product and capability combinations.

## Entry format
### Combination
- Components:
- Combined capability:
- Why the combination is stronger:
- Likely buyer / user:
- Build-time saved:
- Rights / license constraints:
- Validation step:
- Status:

## Seeded combinations — 2026-09-19

### Evidence-first freight recovery stack
- Components: DominicFinn/open_tms + getomni-ai/zerox + microsoft/RulesEngine + dedupeio/dedupe.
- Combined capability: Logistics/shipment domain + document ingestion + deterministic audit rules + entity/carrier/vendor matching.
- Why the combination is stronger: It supplies much of the generic product and evidence infrastructure needed for a freight audit/recovery engine while keeping core billing-error rules explainable.
- Likely buyer / user: Shippers, 3PLs, manufacturers, distributors, or freight-payment teams with enough shipment volume to justify audit/recovery.
- Build-time saved: Potentially very high for non-differentiating infrastructure.
- Rights / license constraints: All four are MIT in the revisions inspected.
- Validation step: Find/implement the missing freight-specific rate-contract and accessorial audit rules, then benchmark on lawful synthetic/public invoice and shipment cases.
- Status: High-priority combination for deeper validation.

### CaptureBrief evidence stack
- Components: MindPetal/sam-search + getomni-ai/zerox + dedupeio/dedupe + microsoft/RulesEngine.
- Combined capability: SAM.gov opportunity retrieval + solicitation/document extraction + entity resolution + explainable qualification rules.
- Why the combination is stronger: Converts raw opportunities into structured, evidence-linked, customer-specific qualification rather than a simple feed.
- Likely buyer / user: Small and midsize federal contractors that need faster opportunity triage.
- Build-time saved: High for ingestion, document processing, matching, and deterministic policy logic.
- Rights / license constraints: All four are MIT in the revisions inspected.
- Validation step: Map SAM fields and attached documents into a single opportunity evidence schema and run against a small sample of current opportunities.
- Status: High-priority enhancement to CaptureBrief.

### ScopeSignal change-to-change-order pipeline
- Components: getomni-ai/zerox + microsoft/RulesEngine + clean-room concepts from Fajendagba/Construction-Change-Order-Engine.
- Combined capability: Extract scope/document changes, evaluate deterministic triggers, and route accepted changes through a construction-specific approval/budget-impact state model.
- Why the combination is stronger: Connects upstream document intelligence to an operationally credible downstream change-order workflow.
- Likely buyer / user: General contractors and specialty subcontractors that lose margin when scope changes are identified late or documented poorly.
- Build-time saved: High for document ingestion/rules plus substantial architecture guidance.
- Rights / license constraints: Zerox and RulesEngine are MIT. Construction-Change-Order-Engine has no license, so only independently reimplemented concepts may be used absent permission.
- Validation step: Find permissively licensed RFI/submittal/document-diff components and test one end-to-end synthetic scope-change case.
- Status: Strong concept; upstream detection component still incomplete.

### Field-onboarding + crop-monitoring stack
- Components: superzero11/OpenFarm + RS-iCM/RSCM.
- Combined capability: Automatically derive/ingest field boundaries and crop/non-crop masks, then run recurring vegetation-index, soil, weather and alert workflows inside a deployable field-operations platform.
- Why the combination is stronger: RSCM attacks the expensive label/bootstrap problem, while OpenFarm supplies the missing operational system around it: PostGIS field records, workers, Sentinel-2 processing, boundary detection, alerts and field workflows. Together they can turn a region with weak customer field data into a monitorable portfolio much faster than building both model and platform from scratch.
- Likely buyer / user: Crop insurers, agricultural lenders, agronomy firms, specialty-crop managers, ag retailers/input distributors and land-use monitoring programs.
- Build-time saved: Potentially 9–15 months of remote-sensing, geospatial-backend, worker and field-onboarding scaffolding for a focused MVP.
- Rights / license constraints: OpenFarm is BSD-3-Clause and RSCM is MIT at the inspected revisions. Sentinel-2/STAC endpoints, FTW checkpoint/model, example datasets and other third-party data/model terms require separate verification.
- Validation step: Select a lawful 50–100-field benchmark, compare generated boundaries/crop masks against known polygons, then measure whether the combined system produces stable per-field index histories and useful alert precision without manual field setup.
- Status: Strong new agriculture combination; best immediate differentiator is automatic portfolio onboarding followed by exception-driven scouting rather than another generic farm dashboard.
