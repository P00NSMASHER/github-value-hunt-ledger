#!/usr/bin/env bash
set -euo pipefail

git pull --ff-only

if ! grep -q '^### NatLabRockies/disco$' hunters/11.md; then
cat >> hunters/11.md <<'EOF'

### NatLabRockies/disco
- URL: https://github.com/NatLabRockies/disco
- Exact commit / revision: `d95fa671918f3b19181d76ffff52e53569525462`
- Date inspected: 2026-09-19
- Status: strong / Master contender
- What it contains: BSD-3-Clause distribution-system impact and upgrade-cost analysis software around OpenDSS/PyDSS. The inspected workflow accepts transformed SMART-DS models or existing non-standardized OpenDSS models, identifies thermal and voltage violations, determines infrastructure upgrades, prices them from a unit-cost database, aggregates upgrade summaries and supports local/HPC execution through JADE. Thermal logic can select higher-rated lines/transformers from a technical catalog or parallel equipment; voltage logic includes capacitor/regulator/LTC actions.
- Rare or undernoticed value: It closes a commercially important gap in the existing hosting-capacity stack: not only “what constrains this feeder?” but “what physical upgrade resolves the violation and what does that upgrade cost?” That is directly adjacent to interconnection-study economics and project go/no-go decisions.
- Monetization path: Fixed-price authorized feeder impact/upgrade diagnostic followed by recurring portfolio/interconnection screening. A buyer provides an authorized OpenDSS/CYME/CIM-derived model; the product returns limiting violations, recommended upgrades, cost estimate and scenario comparisons.
- Likely buyer / user: Distribution utilities, DER/solar/storage developers, interconnection consultants, utility engineering firms and grid-analytics vendors.
- Build-time or data advantage: Roughly 6–12 months of thermal/voltage remediation logic, equipment-catalog handling, cost-model integration, workflow orchestration and test fixture engineering for a comparable MVP.
- Concrete evidence inspected: Exact current default-branch commit; actual root BSD-3-Clause `LICENSE`; `docs/source/analysis-workflows/upgrade-cost-analysis.rst`; `disco/cli/upgrade_cost_analysis.py`; `disco/extensions/upgrade_simulation/upgrade_simulation.py`; generic input models/configs; `tests/integration/test_generic_upgrade.py`; multiple test configs covering thermal/voltage upgrade parameters. The docs explicitly describe three stages—thermal upgrades, voltage upgrades and upgrade-cost computation—and a generic path for existing OpenDSS models.
- License / rights: BSD-3-Clause for repository software. Customer feeder models, cost catalogs and any third-party OpenDSS/PyDSS/SMART-DS inputs retain their own rights and must be authorized/audited.
- Reuse classification: Direct code reuse subject to BSD-3-Clause and authorized input/dependency rights.
- Value score: A 5/5, B 5/5, C 5/5, D 5/5, E 5/5, F 5/5 = **30/30**. It converts the current hosting-capacity benchmark from a capacity diagnostic into an actionable remediation-and-cost workflow.
- Why it is not already obvious / crowded: DISCO is known in research/utility circles, but the commercial value of its automated thermal/voltage upgrade-cost workflow is easy to miss when viewed as a broader distribution-analysis framework.
- Combination opportunities: `DiTTo → DISCO → DREAMS + probabilistic-pv-hosting-capacity → OpenDER_interface`, benchmarked on SGridworks/SHIFT. CommonGrid + deployment-gap-model can add utility/queue context upstream, while DISCO supplies the missing remediation/cost layer after a feeder constraint is found.
- Next action: Plant known thermal and voltage violations into 10–25 SGridworks/SHIFT feeders, run DISCO’s generic upgrade workflow, and verify that the selected equipment changes actually clear the violations and that cost outputs reconcile to an independently built reference catalog.
EOF
fi

if ! grep -q '^### kardashev-lab/interconnection-queue-tracker — validation update$' hunters/11.md; then
cat >> hunters/11.md <<'EOF'

### kardashev-lab/interconnection-queue-tracker — validation update
- URL: https://github.com/kardashev-lab/interconnection-queue-tracker
- Exact commit / revision: `256b986966cb06e4eff878b2c15d2e10ca14b719`
- Date inspected: 2026-09-19
- Status: watch / clean-room only; updates the earlier catalog entry with exact source validation
- What changed in evidence: Exact source inspection confirmed a Next.js/PostgreSQL application plus Python scheduled ingestion for seven public ISO/RTO queue feeds: ERCOT, MISO, PJM, CAISO, SPP, NYISO and ISO-NE. `services/fetcher` contains a 22KB ingestion worker plus GIS-history/backfill/anomaly-analysis utilities; the README documents `queue_projects`/`queue_market_snapshots`, daily GitHub Actions ingestion and Docker deployment.
- Rights / reuse: No root `LICENSE` exists at the inspected revision, so source remains inspect/learn/clean-room only. Upstream ISO/RTO report rights are source-specific. Do not reuse code or bundled data absent permission.
- Value score: A 4/5, B 5/5, C 4/5, D 4/5, E 5/5, F 1/5 = **23/30**. Useful evidence and source-coverage reference, but the MIT `deployment-gap-model` remains the preferred reusable normalization foundation.
- Combination opportunities: Use only as requirements/source-coverage comparison against `deployment-gap-model`; its historical GIS/backfill ideas may inform a clean-room queue-change ledger.
- Next action: No further source reuse work unless licensing changes; independently test whether deployment-gap-model covers the same seven markets and preserve provenance/version history there.
EOF
fi

if ! grep -q '^### yaramohajerani/spatial-climate-ABM$' hunters/23.md; then
cat >> hunters/23.md <<'EOF'

### yaramohajerani/spatial-climate-ABM
- URL: https://github.com/yaramohajerani/spatial-climate-ABM
- Exact commit / revision: `0f031624b35395edcf303d004e945db2fa950a00`
- Date inspected: 2026-09-19
- Status: strong
- What it contains: BSD-3-Clause spatial climate-economy agent-based model that samples GeoTIFF hazard rasters at firm locations and propagates direct physical losses through supplier relationships, labor markets, prices, firm finance and household consumption. It supports calibrated firm topologies, matched-seed ensembles, node/lane/route shocks, dynamic supplier rewiring and adaptation strategies including capital hardening, backup suppliers, stockpiling and reserved capacity.
- Rare or undernoticed value: Most physical-risk tooling stops at asset damage. This implementation explicitly measures indirect/cascade burden on firms that were never directly hit and can compare resilience strategies under matched hazard seeds. That is valuable for supply-chain/portfolio resilience and business-continuity decision products.
- Monetization path: Fixed-price climate supply-chain stress test for manufacturers, lenders, insurers or infrastructure investors, followed by recurring scenario/risk monitoring. First paid wedge: ingest a customer-authorized supplier/facility graph plus public flood rasters and quantify direct loss, indirect disruption and adaptation benefit under matched scenarios.
- Likely buyer / user: Manufacturers with multi-tier supplier exposure, infrastructure investors, insurers/lenders, business-continuity teams, climate-risk consultancies and critical-infrastructure operators.
- Build-time or data advantage: Roughly 5–10 months of spatial ABM, hazard sampling, stock-flow/supplier logic, adaptation scenarios, reproducibility/provenance and cascade-diagnostic engineering for a comparable research-grade engine.
- Concrete evidence inspected: Exact commit; actual BSD-3-Clause `LICENSE`; README; ODD protocol diff at the exact revision documenting calibrated 100-firm/1000-household quarterly model, IO-calibrated sector coefficients/input recipes, topology-driven suppliers, raster hazard severity, reproducible matched-seed ensembles and self-describing `Meta_*` outputs. The public API exposes `HazardRasterEvent`, `NodeShock`, `LaneShock` and `RouteShock` plus direct `build_model`/`run_model` use.
- License / rights: BSD-3-Clause for repository code. Hazard rasters, JRC damage functions, IO tables and any customer supplier/facility data retain separate rights/confidentiality constraints.
- Reuse classification: Direct code reuse subject to BSD-3-Clause and audited input-data rights.
- Value score: A 3/5, B 5/5, C 5/5, D 5/5, E 5/5, F 5/5 = **28/30**. Revenue starts slower than a simple site score, but the indirect-risk/cascade layer is rare and high-ceiling.
- Why it is not already obvious / crowded: It is framed as academic climate-economy research, while the monetizable capability is a programmable physical-hazard → supplier-network → business-interruption scenario engine.
- Combination opportunities: Add Mazzap/physrisk/OpenGIRA hazard layers upstream and use this model for economic cascade/continuity consequences. It also strengthens the existing compliance/restore-proof cluster by quantifying whether redundancy/backup-supplier investments actually reduce modeled disruption.
- Next action: Build a small synthetic 20–50-firm supply-chain benchmark with planted single-node and route shocks, then verify monotonicity of direct/indirect loss and adaptation benefits before exposing customer-facing scores.
EOF
fi

if ! grep -q '^### henok256/resiliencemap$' hunters/23.md; then
cat >> hunters/23.md <<'EOF'

### henok256/resiliencemap
- URL: https://github.com/henok256/resiliencemap
- Exact commit / revision: `f22578d151c6dc264439045f1563258a262861f7`
- Date inspected: 2026-09-19
- Status: watch
- What it contains: MIT-licensed US hazard/resilience data platform combining FEMA, USGS, NOAA, Census, NIFC/HIFLD and CDC/ATSDR SVI into PostGIS, a FastAPI REST layer and tract-level composite risk scores. The current repository also has scheduled federal-data refreshes and live hazard/alert exposure workflows.
- Rare or undernoticed value: A ready operational ingestion/API shell for fragmented federal hazard data, with a useful census-tract normalization layer and automated refresh. The raw scoring concept is less rare than ERAD/physrisk/OpenGIRA, but the production ingestion plumbing can shorten delivery of public-sector/community resilience tools.
- Monetization path: Managed local-government/critical-facility risk feed, grant-planning diagnostic, or embedded hazard API; strongest use is as ingestion infrastructure inside a more defensible asset/site decision product rather than selling the public dashboard itself.
- Likely buyer / user: Municipalities, emergency-management vendors, insurers, lenders, infrastructure/site-selection teams and resilience consultants.
- Build-time or data advantage: Roughly 2–4 months of federal-source ingestion, PostGIS normalization, API/dashboard and refresh automation.
- Concrete evidence inspected: Exact latest commit is an automated FEMA refresh; actual MIT `LICENSE`; README documents six federal-agency sources, 84k+ tract coverage, FastAPI/PostGIS architecture, tract/county risk APIs, tests, Docker Compose and scheduled refreshes.
- License / rights: MIT for repository code. FEMA/NOAA/USGS/Census/NIFC/HIFLD/CDC source data and marks must be reviewed separately; public-source status does not remove source-specific attribution/usage obligations.
- Reuse classification: Direct code reuse subject to MIT and independent source-data review.
- Value score: A 4/5, B 3/5, C 4/5, D 3/5, E 4/5, F 5/5 = **23/30**. Good build compressor, but substantially less differentiated than the stronger asset-failure/network-consequence engines already retained.
- Combination opportunities: Use its federal ingestion layer to feed Mazzap/ERAD/physrisk/OpenGIRA rather than relying on its simple composite score as the moat.
- Next action: Validate three source adapters and freshness/error handling, then compare its tract score against existing FEMA/NRI-style benchmarks before any buyer-facing use.
EOF
fi

if ! grep -q '^### microsoft/rice-irrigation-mapping-s1s2 (Ricemapper)$' hunters/24.md; then
cat >> hunters/24.md <<'EOF'

### microsoft/rice-irrigation-mapping-s1s2 (Ricemapper)
- URL: https://github.com/microsoft/rice-irrigation-mapping-s1s2
- Exact commit / revision: `e4aebe00a44ad79720096a0420270d8f8cf99da0`
- Date inspected: 2026-09-19
- Status: strong / Master contender
- What it contains: MIT-licensed operational training/inference framework for field-level rice sowing and irrigation-practice classification from Sentinel time series. It uses FTW bi-temporal Sentinel-2 field boundaries, Sentinel-1 VV/VH time-series statistics, handcrafted/Presto/Google satellite embedding features and Random Forest/LightGBM models to classify Direct Seeded Rice vs Puddled Transplanted Rice and Alternate Wetting and Drying vs Continuous Flooding. The repository commits de-identified feature Parquets, trained-model artifacts, field-boundary examples and district-level government-comparison outputs.
- Rare or undernoticed value: It adds a management-practice signal to the existing OpenFarm/FTW/Agribound stack: not just crop/field boundaries or stress, but whether rice plots appear to use water-saving AWD versus continuous flooding and DSR versus transplanted sowing. That can support water-conservation verification, program measurement and targeted field outreach.
- Monetization path: Regional irrigation/water-conservation monitoring service for irrigation agencies, NGOs, sustainability programs or rice supply chains; first paid wedge is a seasonal district/portfolio audit identifying likely AWD/CF and DSR/PTR adoption with field-level confidence and change summaries.
- Likely buyer / user: Irrigation districts/water agencies, rice processors/supply-chain sustainability teams, NGOs, agricultural ministries, carbon/water-credit program operators and agronomy/remote-sensing firms.
- Build-time or data advantage: Roughly 4–8 months of Sentinel preprocessing, field-level time-series extraction, feature engineering, training/inference orchestration and practice-specific validation for a similar focused rice system.
- Concrete evidence inspected: Exact current commit; actual MIT `LICENSE`; README with reproducible training/inference workflow; MODEL-CARD; recursive tree showing committed feature Parquets, trained RF/LightGBM artifacts and GeoJSON field bounds. Model card documents ~1,400 Punjab 2024 PRANA rice plots, 90/10 train/test split, FTW boundary dependency, district-level government comparison and explicit geographic/seasonal transfer limitations.
- License / rights: MIT for repository software/model-card-covered code. The original PRANA ground truth is proprietary and not publicly available; only de-identified coordinate-stripped features are provided. Sentinel-1/2, FTW, Presto, Google/AlphaEarth embeddings, Han et al. masks and any government statistics retain separate terms and must be checked before commercial redistribution/use.
- Reuse classification: Repository code directly reusable subject to MIT; training/embedding/source data require independent rights review. Do not infer that MIT relicenses the proprietary PRANA source labels or third-party imagery/embeddings.
- Value score: A 4/5, B 4/5, C 5/5, D 5/5, E 5/5, F 5/5 = **28/30**. High value because it supplies a concrete water-management practice classifier that plugs directly into the existing field-boundary stack, with unusually clear model limitations and code rights.
- Why it is not already obvious / crowded: It is a recent research release whose commercial wedge is narrower than generic crop mapping but more actionable for water conservation and program verification.
- Combination opportunities: `FTW/Agribound → Ricemapper AWD/CF + DSR/PTR → pyCropWat/AquaCrop/OpenH2O`. Sentinel-1 irrigation-performance findings can provide an independent water-delivery signal while OpenFarm supplies operational field monitoring.
- Next action: Reproduce the provided held-out evaluation, then benchmark transfer on a small independent rice region/year before any production claim; specifically test whether AWD/CF ranking remains stable when FTW boundaries are generated automatically rather than taken from curated examples.
EOF
fi

if ! grep -q '^### mf-celik/multimodal-crop-boundary$' hunters/24.md; then
cat >> hunters/24.md <<'EOF'

### mf-celik/multimodal-crop-boundary
- URL: https://github.com/mf-celik/multimodal-crop-boundary
- Exact commit / revision: `da615272af6cfab205a396da1abcc5ca0c136a9d`
- Date inspected: 2026-09-19
- Status: watch
- What it contains: CC0-1.0 dual-stream U-Net crop-field-boundary implementation combining multitemporal Sentinel-1 SAR and Sentinel-2 optical imagery, with early/feature/late fusion, scSE attention and an edge-aware BCE/Tversky/Sobel loss. The project documents training, validation and inference pipelines and an extended AI4SmallFarms Sentinel-1 dataset on Zenodo.
- Rare or undernoticed value: Radar + optical fusion is useful where clouds or weak optical contrast degrade field-boundary extraction, especially small fragmented farms. It is a valuable challenger to FTW/Agribound rather than a replacement by default.
- Monetization path: Component inside automatic farm/field onboarding for monitoring, insurance or irrigation products; paid value comes from lower manual boundary cleanup in cloudy/smallholder regions.
- Likely buyer / user: Agricultural remote-sensing vendors, insurers, irrigation programs, farm-management platforms and NGOs/smallholder analytics teams.
- Build-time or data advantage: Roughly 2–4 months of multimodal segmentation/fusion/loss engineering plus smallholder-specific benchmarking.
- Concrete evidence inspected: Exact commit; README/project tree with PyTorch model, losses, training/evaluation and data-loader modules; actual root CC0 1.0 dedication; documented IEEE GRSL 2026 method and external AI4SmallFarms/Sentinel-1 datasets.
- License / rights: Repository work is under CC0 1.0. AI4SmallFarms, Zenodo Sentinel-1 extension, Sentinel-1/2 imagery and any paper-associated labels retain their own terms and require separate verification.
- Reuse classification: Repository code/content reusable under CC0 to the extent the contributor can dedicate it; source datasets must be independently rights-checked.
- Value score: A 3/5, B 3/5, C 4/5, D 4/5, E 4/5, F 5/5 = **23/30**. Technically useful and rights-clean, but FTW/Agribound already cover the core boundary problem more broadly.
- Why it is not already obvious / crowded: Small/new research repository; the differentiated value is the S1+S2 smallholder boundary challenger, not a general field platform.
- Combination opportunities: Benchmark against FTW/Agribound and route difficult/cloudy regions to the multimodal model only when it materially reduces boundary error.
- Next action: Run all three fusion modes on the same independent tiles used for the FTW/Agribound benchmark and compare polygon-level IoU/topology/manual-correction minutes, not only pixel metrics.
EOF
fi

if ! grep -q '^### shahriarshad/Boro-rice-yield-prediction-and-smart-advisory$' hunters/24.md; then
cat >> hunters/24.md <<'EOF'

### shahriarshad/Boro-rice-yield-prediction-and-smart-advisory
- URL: https://github.com/shahriarshad/Boro-rice-yield-prediction-and-smart-advisory
- Exact commit / revision: `16cb483ab935300084438407a794669aca7717fb`
- Date inspected: 2026-09-19
- Status: rejected / deprioritized
- What it contains: Large initial-commit Bangladesh Boro-rice yield/advisory project with many district CSVs, model/data artifacts and a local SQLite-oriented workflow.
- Why rejected: The inspected commit mixes apparently labeled and explicitly `SYNTHETIC_FORMAT_ONLY` district files, has only one initial commit, and did not establish a unique remote-sensing/public-data method that beats the existing AquaCrop/pyCropWat/Ricemapper/OpenFarm stack. Dataset provenance and commercial reuse rights were not clear enough for retention as a source-data asset.
- License / rights: No reusable rights grant was established during this inspection; treat code/data as inspect/learn/clean-room only unless a valid license and dataset provenance are verified.
- Reuse classification: Do not reuse bundled datasets/code absent permission and source-rights validation.
- Value score: A 1/5, B 2/5, C 2/5, D 2/5, E 2/5, F 1/5 = **10/30**.
- Next action: Do not revisit unless clear licensing/provenance, independent validation and a genuinely differentiated operational workflow are added.
EOF
fi

git config user.name 'github-actions[bot]'
git config user.email '41898282+github-actions[bot]@users.noreply.github.com'
git add hunters/11.md hunters/23.md hunters/24.md
if ! git diff --cached --quiet; then
  git commit -m 'catalog: add run 11 geo asset intelligence findings'
  git push
fi
