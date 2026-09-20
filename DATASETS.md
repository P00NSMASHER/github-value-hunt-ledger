# Datasets & Data Pipelines

Integrator-owned current index of unusually valuable lawful datasets, authoritative public-data pipelines and benchmark infrastructure. Repository-owned code may use the user's separate commercial-permission posture; non-GitHub datasets, source-system data, standards and external services keep their own rights. Detailed history remains in hunter catalogs and Git history.

## Government acquisition / public authority

### GSA/srt-fbo-scraper@fbdfa86a2bce4323a5afacda04f083698cab02e1
- Rights: CC0-1.0 repository work; SAM/source terms separate.
- Value: first-party opportunity paging, attachment acquisition, malformed-link handling, text extraction and solicitation/history state.
- Use: CaptureBrief packet/history plane. Current search output is not complete history by itself.

### GSA/GSA-Acquisition-FAR@da52ccbbe114e1f031a7f4c59195c508dbfa485f
- Rights: official regulatory material; no blanket permissive license assumed for every packaging artifact.
- Value: machine-readable FAR DITA with clause/provision structure, fill-ins, FAC revision markers and FAR Case provenance.
- Use: CaptureBrief rule-currency baseline; agency deviations/applicability remain separate.

### fedspendingtransparency/usaspending-api@1692d484b38c66361c54faa221548527cae29964
- Rights: CC0-1.0 repository; upstream caveats separate.
- Value: official award/procurement/recipient/spending backend and ETL semantics.
- Use: incumbent/award/spend lineage.

### fedspendingtransparency/data-act-broker-backend@76dcae4ccbf6951223608bc1d8fd0c5b03da5d68
- Rights: CC0-1.0.
- Value: official UEI/DUNS/legal/DBA/parent/procurement/referenced-IDV normalization and validation semantics.
- Use: evidence-grade entity/award joins.

### GSA SAM Contract Opportunities version/history planes
- Source evidence: `GSA/open-gsa-redesign@494b1312e9c6436474840befe6e1964da15932b3` documentation and Data Services/history semantics plus live public SAM observations.
- Value: official public opportunity search is latest-active, not all versions. Complete packets need separate history/action and attachment planes.
- Live fixture: Notice ID `W50S8B-26-Q-A016` showed two different Product Description objects sharing the same filename but different `resourceId`s/sizes, and one deleted resource was recoverable from historical action manifests while absent from the latest `excludeDeleted=false` manifest. Re-querying an older action later exposed later tombstone state.
- Identity/time rule: filename is not source-object identity; action membership and observation-time source state are separate. Historical action endpoints are not immutable publication-time snapshots.
- Deletion boundary: official Opportunity Management semantics expose `excludeDeleted` and `deleteAll`; resources deleted with destructive semantics can vanish from later manifests.
- Use: EXP-006. Preserve action UUID + append-only observation identity + resourceId + source state + immutable artifact hash; maintain local snapshots even when historical endpoints remain queryable.

### GSA SAM Acquisition Subaward Reporting public API
- Source: same official GSA lineage.
- Value: Published/Deleted subcontract reports with PIID/prime/referenced-IDV filters, UEI/legal-name/parent lineage, amount/date and pagination.
- Use: CaptureBrief team/incumbent evidence. Published default never proves absence of Deleted records or universal reporting coverage.

### DHS Acquisition Planning Forecast System (APFS) — official live service
- Working score: **29/30 evidence artifact**.
- Value: stable forecast IDs plus source-native dated Change Log old→new events, cancellations/No Longer Required, dates, NAICS, vehicle/program and incumbent/contract context.
- Use: pre-solicitation forecast-to-actual lineage. Planning evidence is not a commitment and may not map 1:1 to SAM.

### SAM.gov Alerts
- Value: official dated incidents can state that opportunity/award/report surfaces are incomplete/delayed.
- Rule: query success during an affected interval is not proof of completeness; absence of an alert is also not proof of health.

## Grid / infrastructure outcome datasets

### owgreen-dev/grid-crunch@5f0c9a074d928b79caa792a84e8e92de1b2df3f2
- Rights: MIT software; LBNL/EIA/HIFLD/ISO/gridstatus inputs keep separate terms.
- Score: **29/30**.
- Value: leakage-safe competing-risks/survival pipeline with fixed-horizon labels, `as_of <= entry_date`, temporal/out-of-cohort validation, calibration/lift and EIA-860M corroboration.
- Use: historical Queue Materialization Intelligence. Post-Order-2023 regime transfer remains unproven.

### savabs/queue_attrition@daf180778383b8675e252346e771a4e754f0558d
- Rights: no root LICENSE established; upstream ISO data separate.
- Score: **26/30** at inspection.
- Value: content-addressed live queue snapshots and append-only prospective prediction ledger.
- Limitation: evaluation used isotonic calibration while inspected live prediction path appeared to emit raw pipeline probabilities; production calibration parity remains unproven.

### HopkinsICARUS/ICARUS-PJM-Dataset@0cb6a1af86e2bdfc1d160f44b6e4a7518ca3ffe3
- Rights: MIT software; CC BY 4.0 repository data as recorded by hunter.
- Score: **29/30**.
- Value: 17,467-bus synthetic PJM-like network for reproducible regional stress/constraint testing without customer production models.
- Rule: synthetic engineering benchmark, not a utility's actual grid.

### PNNL Event-correlated Outage Dataset in America (USECPO) v2
- Official records: Data.gov/OEDI, public access, **CC BY 4.0**; current resource names recorded by hunter as `Outage_Dataset_R1.zip` and `Guideline_OEDI_Updated.docx`.
- Working score: **27/30**.
- Coverage: 2014–2023 EAGLE-I county outage scenarios correlated to DOE-417 events, with grouped/merged/event-correlated derivatives.
- Peer-reviewed logical schema verified from F. Yang et al., IEEE Data Descriptions 2025, DOI `10.1109/IEEEDATA.2025.3598229`:
  - grouped: `state, year, month, outage count, max outage duration, customer weighted hours`;
  - county merged: `fips, state, county, start time, duration, min customers, max customers, mean customers`;
  - event-correlated: `fips, state, county, start time, duration, event id, event type`;
  - variants: STANDARD, +8h lag and +24h lag.
- Evaluator contract: literal `event id` is the associated-event group key. Keep every row for one event in one train/tune/test partition and preserve event chronology. STANDARD/8H/24H are sensitivity variants, **not independent observations**.
- Provenance/quality: record ancestry `EAGLE-I + DOE-417`; county-explicit vs state-generalized geography; missing DOE-417 restoration time imputed to event start; early coverage weaker, so prefer **2019–2023** for first high-confidence benchmark.
- Critical scope limits: transmission/major-event conditioned, not general distribution-outage truth; correlation is not feeder/component causality; overlapping county physical outages may be merged; detailed restoration requires independent OMS/field truth.
- New external witness: Mendeley DOI `10.17632/r4csg2h2ps.1`, version 1, exposes two byte-identical aliases of one 12,980,662-byte reproducibility package, outer SHA-256 `3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67`.
- Witness boundary: the two aliases are one witness, not two independent sources. The outer package SHA is **not** the embedded USECPO ZIP SHA. The package reportedly contains a source/download manifest with source URL/release/size/SHA, but that exact USECPO row has not yet been extracted/verified.
- Artifact-byte gate: obtain the Mendeley package in a binary-capable runtime, verify the outer SHA, extract only the source manifest, then independently compare the exact USECPO row against first-party OEDI bytes or a first-party digest. Until then exact current headers/timezone/nulls/thresholds/event-ID namespace and source digest remain UNKNOWN.
- Use: EXP-012 historical evaluator only after the byte gate; related EAGLE-I-derived datasets do not count as independent validators.

### PNNL OWL-I USA v1
- Source: Zenodo DOI `10.5281/zenodo.20433558`, 2026-08-25; EarthArXiv method preprint 2026-08-28.
- Score: **25/30**; rights clarity weak.
- Value: nightly CONUS 2012–2024 ~1 km outage-fraction/uncertainty estimates from nighttime lights calibrated against EAGLE-I.
- Rule: useful high-resolution challenger only after rights/circularity diligence; not feeder-level OMS ground truth and not independent of EAGLE-I.

### Saki et al. harmonized EAGLE-I + NWS VTEC v2
- Source: Zenodo v2 DOI `10.5281/zenodo.22651795`, published 2026-09-08; hunter records peer-reviewed Scientific Data descriptor published 2026-09-19.
- Score: **27/30 — A4 B5 C5 D5 E5 F3**.
- Value: 2015–2024 CONUS outage/warning/recovery archive with source-availability and sensitivity diagnostics.
- Rights: harmonized-v2 reuse terms unresolved at integration time; upstream sources separate. Do not redistribute/embed commercially until confirmed.
- Rule: observational outcome evidence, not causal proof; EAGLE-I ancestry limits independence versus EAGLE-I-trained models.

### EAGLE-I 2025 observations — out-of-time candidate
- Released 2026-02-19 and temporally later than common 2015–2024 histories.
- Rights not established for commercial embedding at inspection; keep unresolved.

### California OES Power Outage Incidents
- Working score: **24/30 live acceptance source**.
- Public-domain current feed refreshed roughly every 15 minutes from major California utility public outage maps.
- Use: prospective/current ingestion spot checks, not retrospective archive.

### Michigan MPSC outage evidence / NYC 311
- MPSC: strong independent regulator challenger but commercially rights-constrained.
- NYC 311: rights-clean construct-validity negative control, not utility-outage truth.

## Other benchmark/data assets

### xiazeyu/FireDataForge@4328d4f6bdbec5a3ab30bf786718d759fc4fb84c
- Rights: MIT code; underlying sources separate.
- Score: **27/30**.
- Value: harmonized wildfire perimeter/fireline/VIIRS/terrain/fuels/weather/recent-burn/building/Sentinel/WUI feature factory with caching and failure diagnostics.
- Use: rights-audited historical wildfire model benchmark.

### garretlking1-commits/jobwalk (`fdcb507...` recorded in Hunter 04)
- Score: **27/30** synthetic benchmark.
- Value: rights-clean synthetic construction evidence archive for change/payment/waiver regression.
- Rule: synthetic fixture, not empirical market evidence; payment/waiver effectiveness remains UNKNOWN without cleared settlement.

## Demoted / negative-control assets

### aiparallel0/freight-audit@e7869162cf9cb23f6d520a0cd71f87cf973d8c28
- **DEMOTED from elite/gold-truth use.** Missing authority can become default expected money; missing RateCon can still emit detention value; overlapping findings can double-count; review-pending values can enter aggregate/billing surfaces.
- Safe residual use: selected synthetic documents/cases as negative-control fixtures only, with independently authored authority/expected-dollar truth.

## Dataset promotion rule
Promote a dataset/pipeline centrally only when its provenance, rights posture, coverage/construct, missingness and evaluation role are explicit. Public visibility alone is neither commercial reuse permission nor evidence independence.