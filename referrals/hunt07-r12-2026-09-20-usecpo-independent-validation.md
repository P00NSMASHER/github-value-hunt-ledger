# Hunt 07 referral — USECPO independent-validation boundary

Date: 2026-09-20
Lane: Geo Asset Intel / grid-outcome validation
Primary graph edge: CAP-015 -> EXP-012
Search strategy: STRAT:evaluation-target-independence

## Executive finding
No new MASTER-caliber repository was found. The valuable result is a sharper falsification boundary for EXP-012: USECPO v2 is a rights-clear historical benchmark, but the best historical independent utility/regulator challenger located in this run (Michigan MPSC outage history) is not commercially reusable under Michigan.gov's general terms without separate permission, while the strongest clearly reusable independent public signal located (NYC 311) measures a different construct and cannot serve as utility-grid outage truth. California OES is public-domain utility-map output but has no history, so it is useful only for prospective/live challenge.

This means EXP-012 should use a two-plane validation design rather than pretending one source can do everything:
1. historical model-development/evaluation plane: USECPO v2, whole-event blocked and chronology-preserving;
2. independent challenge plane: regulator/utility records where terms permit analysis, plus prospective public-domain feeds after the prediction is frozen.

## USECPO v2 — executable benchmark substrate, exact schema still needs artifact inspection
Official source: https://catalog.data.gov/dataset/event-correlated-outage-dataset-in-america
OEDI landing page: https://data.openei.org/submissions/6458
Current metadata last updated: 2026-07-27
License: CC BY 4.0
Access level: public

Current federal metadata states that USECPO integrates EAGLE-I county outage observations (2014-2023, 15-minute interval), DOE-417 disturbance reports, and county population estimates. The correlated layer matches outages to DOE-417 events using geography plus event start/end time. V2 resources are explicitly listed as `Outage Dataset v2.zip` (`Outage_Dataset_R1.zip`) and `Data Guidelines v2.docx` (`Guideline_OEDI_Updated.docx`). The v2 ZIP is described as containing aggregated outage data, merged outage data, and event-correlated data.

Important limitation: during this run the direct OEDI ZIP/DOCX downloads could not be programmatically fetched because the file endpoint returned/routed through a rate-limited path. Therefore exact v2 column names, event-key fields, and missing/final-value flags were NOT verified from the artifact. Do not implement a guessed manifest schema. The conceptual event-block split is supported, but the deterministic manifest remains blocked on exact v2 artifact inspection.

## Best new external challenger — Michigan MPSC Customer Outage History
Official source: https://www.michigan.gov/mpsc/consumer/electricity/customer-outage-history
Status: WATCH / independent regulator outcome challenger
Working score: A3 B5 C4 D4 E5 F2 = 23/30

What is verified:
- Utilities report outage status and estimated customers affected to the Michigan Public Service Commission when threshold conditions are met.
- Consumers Energy and DTE events above 20,000 customers are listed; other utilities are listed above 5% of company customers.
- Initial reports are visibly marked with `*`; MPSC states values are updated when final utility filings arrive.
- Historical outage links cover 2019-2025, with current 2026 events also listed.
- The same MPSC page describes expanded utility reporting that includes outage counts, restoration times, customers interrupted, storm duration/restoration days, storm spend, outage-credit dollars, mutual-aid requests/expense, and desired ZIP/census-tract granularity.

Why it matters:
This is a materially more independent challenger to EAGLE-I/USECPO than another EAGLE-I derivative: the reporting lineage is utility -> state regulator, with explicit provisional-vs-final semantics.

Rights gate:
Michigan.gov's general Terms of Use explicitly prohibit commercial use/resale of data derived from the site absent a separate written agreement or data-specific terms that allow it. Therefore this source may be used as an external public-reference challenger under the applicable terms, but should NOT be embedded, redistributed, or made part of a commercial product dataset without separate permission. This rights constraint is why it remains 23/30 rather than a MASTER/data promotion.

## Rights-clean negative control — NYC 311 + reproducible research code
Official data rights: https://www.nyc.gov/opendata/get-started/FAQs
Paper: https://www.nature.com/articles/s41370-025-00767-1
Repository: https://github.com/ajnorthrop/redlining-electricity-inaccessibility
Exact repository revision inspected: `417f6597f04815f23e05e482afafc298abef117c`
Public repository license: none declared; standing user commercial permission applies to repository-owned code, not external NYS DPS data.
Status: WATCH / negative-control implementation, not outage oracle
Working score: A2 B4 C4 D4 E4 F3 = 21/30

Verified beyond README:
- `code/3c_311_call_holc_aggregation.R` reads 311 records, filters `descriptor == "POWER OUTAGE"`, requires coordinates, restricts to 2017-2019, spatially allocates calls and computes per-1,000-household outage rates.
- `code/3a_nyspo_saifi.R` reads the separately sourced/imputed NYS outage data and computes a POL-level interruption metric from `customers_out` and customer counts.
- NYC Open Data's official FAQ says there are no restrictions on use of Open Data.
- The peer-reviewed paper explicitly distinguishes 311 outage calls as household/building-level reported outages from NYS DPS system-level utility interruptions and reports no correlation between SAIFI and 311 calls per 1,000 households.

Implication:
311 is useful precisely because it is NOT interchangeable with utility outage truth. It is a rights-clean independent negative/control signal that can expose a model whose claimed 'outage prediction' is actually tracking household reporting/housing conditions rather than utility-system interruption. It must not be scored as an oracle for USECPO/EAGLE-I county outage magnitude.

## Prospective independent plane — California OES Power Outage Incidents
Official source: https://lab.data.ca.gov/dataset/power-outage-incidents
License: public domain

Verified scope:
- Pulled directly from PG&E, SCE, SDG&E and SMUD public outage maps.
- Updated every 15 minutes.
- Point incidents, PG&E outage polygons, and county summaries are exposed.
- The source explicitly says it contains only the most recent outages and NO historical data.

Implication:
California OES cannot backfill 2014-2023 USECPO validation, but it is a strong rights-clean prospective falsifier: freeze predictions first, then resolve them against later independently observed public-domain outage-map state.

## EXP-012 correction
Use the following evidence hierarchy:
1. `USECPO v2` = historical event-correlated outcome benchmark, CC BY 4.0, but lineage includes EAGLE-I; use whole-event blocked chronological evaluation and track source ancestry.
2. `Michigan MPSC` = historical independent utility/regulator challenger with provisional/final semantics; external-reference only unless commercial reuse permission is obtained.
3. `NYC 311` = rights-clean independent household/building outage/reporting signal; negative control / construct-validity test only, never utility-grid ground truth.
4. `California OES` = public-domain live utility-map challenge plane; prospective only because no history exists.

A model must not receive 'independent validation' credit merely because multiple evaluator datasets descend from EAGLE-I or because a household-reporting proxy agrees with it. Keep policy score, evaluator outcome, and claimed business target separate under Evaluation-Target Independence.

## Capability delta
CAP-015 is strengthened from 'freeze future predictions' into 'freeze predictions AND record evaluator ancestry/construct so proxy agreement cannot masquerade as independent utility-outcome evidence.'

## Graph edge
- USECPO v2 -> TESTS CAP-015 / EXP-012 historical calibration.
- Michigan MPSC -> CHALLENGES USECPO/EAGLE-I lineage on a historical regulator plane, rights-constrained.
- NYC 311 -> NEGATIVE CONTROL for construct validity; household/building outage reporting is not grid SAIFI truth.
- California OES -> PROSPECTIVE INDEPENDENT CHALLENGER for frozen future predictions.

## Radar signal
Outcome-priced grid decision intelligence gains methodological evidence, not a score increase. The limiting edge is no longer another outage model; it is independent, rights-clear outcome truth plus asset/work-order/restoration linkage.

## Experiment impact
Before running EXP-012:
- inspect the actual v2 guideline/ZIP and derive the event key from the artifact, not metadata assumptions;
- freeze whole DOE-417 disturbance groups into one split each;
- preserve chronology;
- record source ancestry for every evaluator;
- score observed outage outcome separately from modeled interruption dollars;
- reserve a prospective California OES-style feed for post-freeze external checks;
- never use 311 agreement as proof of system-level outage accuracy.

## Commercial impact
The near-term sellable wedge remains a Grid Resilience Calibration / Acceptance Audit, but claims should be limited to historical calibration and explicitly modeled consequence until customer-authorized asset/work-order/restoration truth or a commercially reusable independent historical utility oracle is obtained.

## Negative knowledge
- Rights-clean + independent + historical utility-grade outage truth remains the missing conjunction.
- A regulator webpage can be excellent evidence yet commercially restrictive.
- Citizen outage reports are not interchangeable with utility interruption metrics; the NYC study found no correlation between 311 outage-call rate and SAIFI.
- Public-domain California OES utility-map data are live-only and cannot retroactively validate USECPO's historical period.
- Do not guess USECPO event IDs/columns from dataset prose; exact v2 artifact schema remains unverified this run.

## Cross-agent referral
MASTER Integrator / grid experiment owner: preserve USECPO as the executable historical benchmark, add an explicit evaluator-ancestry field to EXP-012, treat Michigan MPSC as a rights-constrained independent challenger, treat NYC 311 as a negative control, and use California OES for prospective post-freeze validation.

Exact unanswered technical question: can the current USECPO v2 ZIP/guideline be accessed from an official mirror or later successful download so that the exact event key, event membership, missingness and final/provisional semantics can be frozen into a deterministic manifest without inference?

## Next highest-value question
Can we locate an explicitly public-domain or permissively licensed HISTORICAL utility/regulator outage feed with event/restoration semantics that is genuinely independent of EAGLE-I, so EXP-012 can include a reusable independent historical falsifier rather than relying on rights-constrained regulator pages or non-equivalent complaint data?
