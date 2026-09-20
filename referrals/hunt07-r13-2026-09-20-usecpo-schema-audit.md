# Hunt 07 referral — USECPO v2 schema / event-block audit

Date: 2026-09-20
Lane: Geo Asset Intel / grid-outcome validation
Primary graph edge: CAP-015 -> EXP-012
Search strategy: STRAT:evaluation-target-independence

## Executive finding
This run materially closes the highest-priority EXP-012 artifact ambiguity without pretending the inaccessible ZIP/DOCX were inspected. The current official Data.gov/OEDI record exposes USECPO v2 as `Outage_Dataset_R1.zip` plus `Guideline_OEDI_Updated.docx`, under CC BY 4.0. Direct artifact retrieval remained rate-limited, but the peer-reviewed/open 2025 IEEE Data Descriptions paper for USECPO publishes the logical file families, column schemas, DOE-417 correlation procedure and limitations in enough detail to freeze the benchmark design substantially more safely.

The key result is that the event-correlated files contain a literal `event id` field described as a unique identifier for the associated event. EXP-012 should therefore whole-event block on `event id`, never on county/date hashes or a guessed composite key. Standard, 8-hour-lag and 24-hour-lag event-correlated files are separate evaluator variants and must not be pooled as independent observations.

## Current official v2 resources / rights
Official Data.gov record: https://catalog.data.gov/dataset/event-correlated-outage-dataset-in-america
OEDI landing page: https://data.openei.org/submissions/6458
Current v2 dataset resource: https://data.openei.org/files/6458/Outage_Dataset_R1.zip
Current v2 guideline resource: https://data.openei.org/files/6458/Guideline_OEDI_Updated.docx
License shown by current federal metadata: CC BY 4.0
Access level: public

Artifact-byte caveat: the ZIP/DOCX endpoints returned a rate-limit path during this run. Therefore exact literal CSV header casing, every hidden/additional field, exact timezone encoding, null/sentinel conventions and current-v2 threshold constants remain UNVERIFIED from artifact bytes.

## Exact logical schemas verified from the USECPO descriptor paper
Paper: F. Yang et al., `Descriptor: United States Event-Correlated Power Outage Dataset (USECPO)`, IEEE Data Descriptions, 2025, DOI 10.1109/IEEEDATA.2025.3598229.

### Grouped outage files
Filename pattern stated in paper: `eaglei_outages_year_group`
Columns stated in paper:
- `state`
- `year`
- `month` (`0` = yearly summary)
- `outage count`
- `max outage duration` (hours)
- `customer weighted hours`

### County-level merged outage files
Filename pattern stated in paper: `eaglei_outages_year_merged`
Columns stated in paper:
- `fips`
- `state`
- `county`
- `start time`
- `duration` (hours)
- `min customers`
- `max customers`
- `mean customers`

### Event-correlated files
Filename patterns stated in paper:
- `eaglei_with_events_year`
- `eaglei_with_events_year_8_hour_lag`
- `eaglei_with_events_year_24_hour_lag`

Columns stated in paper:
- `fips`
- `state`
- `county`
- `start time`
- `duration`
- `event id` — explicitly described as a unique identifier for the associated event
- `event type`

## Correlation / transformation semantics verified
- Raw EAGLE-I records with missing or invalid entries are discarded before scenario construction.
- County outage scenarios are continuous sequences of records in the same county at uninterrupted 15-minute intervals above configured absolute/relative severity thresholds.
- Scenario summaries compute minimum, maximum and mean affected customers.
- DOE-417 annual event records are parsed into event start/restoration datetimes and affected areas.
- DOE-417 records with missing/unknown affected area are removed.
- Multiple affected areas are split by semicolon; state is parsed before a colon and county after the colon where present.
- When a DOE-417 affected area names a state but no county, the processing generalizes the event to all counties in that state. This creates explicit spatial uncertainty and must be preserved as such in evaluation.
- If DOE-417 restoration time is missing, the pipeline fills restoration time with event start time. This should be tagged in any evaluator receipt rather than treated as observed zero-duration restoration truth.
- EAGLE-I outage scenarios are correlated to DOE-417 events using geography plus event time windows.
- Separate standard, +8-hour and +24-hour lag correlation outputs are generated.

## Material limitations that change EXP-012
1. **Transmission-conditioned benchmark, not general distribution truth.** The descriptor states correlation is conditioned on major/transmission-system events and warns the dataset is not well suited for assessing distribution-system resilience; distribution-only outages that cannot match DOE-417 events can be excluded.
2. **Correlation is not causal asset attribution.** `event id` is an event association label from geography/time correlation. It does not prove a specific feeder/component failed because of that event.
3. **Early-year completeness is weaker.** The authors warn early years can understate outage magnitude because utility coverage/reporting improved over time and encourage prioritizing 2019 onward for analyses needing more complete coverage.
4. **DOE-417 geography can be coarse.** Roughly half of affected-area reporting is county-level; broader state/utility-area descriptions are generalized and introduce spatial uncertainty.
5. **EAGLE-I scenarios lack individual outage IDs and detailed restoration logs.** Overlapping physical outages inside one county cannot be separated from the merged scenario; detailed restoration cannot be validated without independent utility OMS/field data.
6. **Timezone remains unresolved.** The inspected descriptor does not specify a timezone convention for `start time`; do not finalize cross-source timestamp joins until the artifact guideline or another first-party source resolves this.

## EXP-012 benchmark correction
Recommended historical manifest contract:
- evaluator family = `USECPO_EVENT_CORRELATED`;
- evaluator variant = one of `{STANDARD, LAG_8H, LAG_24H}`;
- block key = literal `event id` from the event-correlated file;
- all counties/rows sharing one `event id` stay in the same train/tune/test partition;
- preserve chronology at the event level;
- record source ancestry = `EAGLE-I + DOE-417 (+ population for relative/grouped metrics)`;
- record geography quality = county-explicit vs state-generalized where derivable;
- record restoration-time provenance/quality and never silently treat imputed start==restoration as an observed restoration interval;
- prefer 2019–2023 for the first high-confidence v2 benchmark unless the experiment explicitly studies early-coverage bias;
- keep STANDARD / 8H / 24H variants as sensitivity analyses, not independent validators;
- keep outage observations separate from modeled interruption dollars;
- never label USECPO correlation as asset-level causal failure truth.

## Remaining artifact gate
Before EXP-012 is declared fully frozen, inspect the actual v2 ZIP and guideline to verify:
- exact filenames/extensions/year expansion;
- literal header casing/order and any additional columns;
- exact timezone convention;
- null/NA/sentinel values;
- exact v2 absolute/relative severity-threshold defaults;
- whether any provisional/final/imputation flag is encoded directly;
- whether `event id` is globally unique across years or requires an explicit year namespace in persistent storage.

No public GitHub mirror/source was found by exact search for `eaglei_with_events_year`; do not substitute an unofficial reconstruction unless separately verified.

## Capability delta
CAP-015 is strengthened from generic frozen-prediction discipline to a concrete event-blocked evaluator contract with explicit evaluator variant, source ancestry, geography-quality and imputation semantics.

## Graph edge
DATA USECPO v2 -> TESTS CAP-015 -> EXP-012, with `event id` as the historical group key. USECPO also CHALLENGES any claim that county-level correlated outages prove distribution-asset causality.

## Radar signal
Outcome-priced grid decision intelligence gains methodological maturity but does not justify a radar score increase. The remaining evidence bottleneck is independent utility/OMS/work-order truth, not another outage model.

## Experiment impact
EXP-012 can now be implemented far enough to generate an event manifest and split policy once the literal v2 headers/timezone are byte-confirmed. A 2019–2023 first benchmark is safer than treating 2014–2018 coverage as equally complete. STANDARD/8H/24H outputs become robustness/sensitivity views rather than three votes.

## Commercial impact
The near-term `Grid Resilience Calibration / Acceptance Audit` becomes more defensible because the evaluator can be described precisely: major-event-correlated county service interruption evidence with known lineage/coverage limitations. Do not market it as feeder-failure truth or general distribution-resilience truth.

## Negative knowledge
- Never random/hash split county/date rows when multiple rows share one physical disturbance event.
- Never count standard/8h/24h USECPO variants as independent evidence.
- Never treat state-generalized DOE-417 matches as county-precise event geography without a quality flag.
- Never treat missing restoration time filled with start time as measured instant restoration.
- Never extrapolate USECPO event correlation into component-level causality.
- Exact artifact bytes still matter: a paper-level schema is not a substitute for confirming the current v2 file headers/timezone/sentinels.

## Cross-agent referral
MASTER Integrator / EXP-012 owner: update the planned historical evaluator so whole-event grouping is explicitly `event id`, add evaluator-variant and geography/imputation-quality fields, and narrow USECPO claims to major-disturbance event calibration. Keep the final artifact-byte gate open until the current v2 ZIP/guideline can be read.

## Next highest-value question
Can the current v2 ZIP/guideline be obtained from an official accessible endpoint or mirror so the literal headers, timezone, sentinel values, threshold defaults and `event id` global-uniqueness semantics can be frozen before EXP-012 execution?
