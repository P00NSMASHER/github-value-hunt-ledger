# Research & Science

## Hunter instructions
Before searching, read this file plus ../MASTER.md, ../REJECTED.md, and ../COMBINATIONS.md.

Search public GitHub repositories for unusually valuable functioning software, data pipelines, algorithms, workflows, datasets, integrations, or product infrastructure relevant to this lane. Include obscure, abandoned, low-star, and no-license repositories in discovery. Respect license/copyright for reuse.

Do not collect, reproduce, preserve, or exploit exposed credentials, personal data, authentication material, or accidentally published confidential information. Skip/quarantine those items and continue searching for legitimate technical or commercial value.

## Finding template
### Repository name
- Repository:
- Commit / revision:
- Date discovered:
- What it contains:
- Why it matters:
- Commercial possibilities:
- Build-time savings:
- Evidence inspected:
- License / rights:
- Reuse classification:
- Scores:
  - Technical value:
  - Commercial value:
  - Rarity:
  - Completeness:
  - Build-time saved:
  - Data advantage:
  - High-ticket potential:
- Next action:

## Findings
### PyLabRobot/pylabrobot
- Repository: https://github.com/PyLabRobot/pylabrobot
- Commit / revision: c3c59eebf45c4f6bb2fc78dbfd30f6e458653494
- Date discovered: 2026-09-19
- What it contains: Hardware-agnostic Python SDK for laboratory automation spanning liquid handlers, plate readers, pumps, scales, heater-shakers, centrifuges, thermocyclers, storage, barcode scanners, and many vendor-specific backends.
- Why it matters: The repository compresses a large amount of specialized device-integration work behind a common software interface and is actively maintained.
- Commercial possibilities: Protocol automation layer for specialized lab workflow products, remote execution/control, reproducibility tooling, lab-operations orchestration, or vertical services that sit above existing robots.
- Build-time savings: Very high for cross-vendor device control and lab-instrument abstractions.
- Evidence inspected: README.md; repository metadata updated 2026-09-18; MIT LICENSE; source tree contains many vendor/device modules plus liquid_handling backends, testing infrastructure, and broad hardware adapters.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT terms.
- Scores:
  - Technical value: Very High
  - Commercial value: Medium-High, depending on access to lab customers/hardware
  - Rarity: High
  - Completeness: Very High
  - Build-time saved: Very High
  - Data advantage: Medium
  - High-ticket potential: High
- Next action: Search for narrow, expensive lab workflows where PyLabRobot already supports the installed hardware and where software/orchestration is the bottleneck rather than hardware procurement.

### aws-samples/sample-allotrope-as-a-service
- Repository: https://github.com/aws-samples/sample-allotrope-as-a-service
- Commit / revision: a0aa5337778fc1f03f8d863480aed42968d79625
- Date discovered: 2026-09-19
- What it contains: A zero-star, deployable AWS reference stack for laboratory-instrument data normalization to Allotrope Simple Model JSON. It includes a React/Cloudscape dashboard; CDK deployment; Lambda services for deterministic multi-instrument conversion, AI fallback, custom converters, validation/certification, history, auth and converter registry; S3/DynamoDB persistence; tests; sample data; and an intelligent routing layer that prefers registered/custom or Allotropy converters before AI fallback.
- Why it matters: This is much closer to a sellable lab-data interoperability product than a parser library alone. The deployment guide provisions 14 Lambda functions, 5 API Gateway endpoints, 4 DynamoDB tables, 3 S3 buckets, shared Lambda layers, JWT-based API authorization, and a CloudFront dashboard. The code has explicit traceability/field-mapping outputs and a rule engine, while unit tests exercise converter sandbox restrictions, routing, ASM validation and rule checks. It collapses much of the plumbing needed for an instrument-data gateway.
- Commercial possibilities: White-label instrument-data normalization gateway for biotech/pharma labs; managed onboarding of legacy instrument exports into LIMS/ELN/data lakes; validation/traceability service around scientific data migrations; paid implementation plus annual support/hosting. Strongest wedge is a fixed-fee pilot that converts a customer's highest-friction instrument exports into normalized JSON with source-to-output traceability, then expands instrument by instrument.
- Build-time savings: Roughly 3-6 months versus building the service shell, registry, validation layer, routing, dashboard, deployment and auth from scratch; potentially more when combined with Allotropy's parser coverage.
- Evidence inspected: Repository metadata (0 stars, MIT-0); README.md; DEPLOYMENT.md; services/unified-converter/lambda_function.py; services/tests/test_custom_converter.py; services/tests/test_rule_engine.py; latest commit metadata. The unified converter implements custom-converter selection, deterministic Allotropy conversion, AI fallback and optional S3/DynamoDB storage. Tests explicitly block dangerous imports/builtins in custom converter execution and exercise multiple validation-rule types. Deployment documentation also warns that further CORS/API-key/VPC hardening is required for production.
- License / rights: Repository code is MIT-0. Its Allotropy dependency is MIT. Allotrope Foundation ASM schemas/models/data have separate licensing terms and must be reviewed for the intended commercial use; permissive code licenses do not automatically grant rights to every external schema/content dependency.
- Reuse classification: Directly reusable code subject to MIT-0 and dependency notices; external ASM schema/data rights require separate verification before commercial redistribution/use.
- Scores:
  - Technical value: Very High
  - Commercial value: Very High
  - Rarity: Very High (0-star repository with full deployable stack)
  - Completeness: High
  - Build-time saved: Very High
  - Data advantage: High when combined with Allotropy parser coverage
  - High-ticket potential: Very High
- Next action: Build a no-integration-required paid-pilot demo around 3-5 common instrument exports, keeping deterministic parsers as the default and human review around AI-generated/custom converters; separately verify the Allotrope schema/content license needed for the target buyer/use case.

### Benchling-Open-Source/allotropy
- Repository: https://github.com/Benchling-Open-Source/allotropy
- Commit / revision: ecc574986b74f91eb84cd0ee14756cd8dc5e1b7e
- Date discovered: 2026-09-19
- What it contains: A production-oriented Python conversion library that auto-detects many laboratory instrument export formats and emits Allotrope Simple Model JSON. At the inspected revision the supported-instrument matrix lists 53 instrument-software entries across chromatography, plate readers, cell counting, flow cytometry, liquid handling, qPCR/dPCR, spectrophotometry and other categories; 52 are marked Recommended and one Working Draft. The parser factory maps those vendor/software types to concrete parsers and supports auto-discovery by extension plus parser-specific sniffing.
- Why it matters: Recreating dozens of vendor-specific scientific export parsers is slow, brittle integration work. This library already contains the specialized parsers, schemas/mappers, auto-detection logic and a large fixture/test corpus. The latest inspected commit fixes a real Agilent OpenLab CDS edge case and reports 13 affected parser tests plus 327 vendor-discovery tests passing, evidence of active production-style maintenance rather than a static demo.
- Commercial possibilities: Core engine for an instrument-normalization SaaS or managed integration service; migration utility that standardizes historical laboratory files; data-ingestion layer feeding LIMS/ELN/warehouse/AI systems; foundation for fixed-fee per-instrument onboarding and enterprise support contracts.
- Build-time savings: Approximately 6-18 months of specialized parser/instrument-format work for comparable breadth, depending on required instrument mix and validation depth.
- Evidence inspected: Repository metadata; README.md; SUPPORTED_INSTRUMENT_SOFTWARE.adoc; src/allotropy/parser_factory.py; LICENSE.txt via code search; tests/discover_vendor_test.py via code search; latest commit metadata for Agilent OpenLab CDS single-injection handling and test verification.
- License / rights: Code is MIT (LICENSE.txt, copyright Benchling, Inc.). README explicitly notes Allotrope is a registered trademark and that ASM schemas are published separately; downstream use should still respect any separate terms on the ASM schema/data artifacts consumed by a commercial product.
- Reuse classification: Directly reusable subject to MIT terms; separately review rights for external Allotrope schema/data content bundled or redistributed by a product.
- Scores:
  - Technical value: Very High
  - Commercial value: High
  - Rarity: High
  - Completeness: Very High
  - Build-time saved: Very High
  - Data advantage: High (broad cross-vendor parser/fixture coverage)
  - High-ticket potential: High
- Next action: Pair with the AWS Allotrope-as-a-Service stack and validate a buyer-facing demo using representative exports from the most common instruments in a target lab segment; avoid claiming universal format coverage and surface parser release-state/confidence explicitly.

### aws-samples/sample-laboratory-data-transformation-mcp
- Repository: https://github.com/aws-samples/sample-laboratory-data-transformation-mcp
- Commit / revision: 38180b90a45098f8546b50d9af42d1b1f4b3e96c
- Date discovered: 2026-09-19
- What it contains: A 4-star MIT-0 MCP server plus guided AI workflow for discovering Allotrope models, fetching allowed ASM documents, validating ASM JSON against schemas, and validating source-to-ASM field maps. The repository also includes a Kiro Power and an agent skill that guide an AI coding tool through schema discovery, converter creation and validation for unsupported instrument formats.
- Why it matters: The long-tail problem in laboratory interoperability is onboarding an unsupported instrument export. This repo supplies a concrete "converter factory" workflow rather than just a runtime parser: discover target model, create mapping/converter, validate schema, then compare every source value to the generated ASM value. The field-map tests include real fixtures plus Hypothesis property-based tests (100 examples per property) covering result completeness, value equality and mismatch structure.
- Commercial possibilities: Assisted onboarding workbench for unsupported instruments; internal converter-generation tool for an instrument-data SaaS; paid conversion/migration projects where each new instrument format becomes a reusable approved adapter after validation. It combines especially well with sample-allotrope-as-a-service's converter registry and sandbox.
- Build-time savings: Roughly 1-3 months for model discovery, schema validation, field-map verification and guided converter-onboarding workflow; more valuable as a force multiplier for each subsequent unsupported instrument.
- Evidence inspected: Repository metadata and MIT-0 license classification; README.md; allotrope_mcp_server/server.py via code search; tests/test_validate_field_map.py; latest commit metadata. The field-map validator is actually registered as an MCP tool and tests cover missing/invalid files, fixture mismatches and property invariants.
- License / rights: Repository code is MIT-0. README explicitly states that Allotrope Foundation ASM and related data have separate licensing regimes depending on intended usage/membership status, so those content rights must be reviewed independently.
- Reuse classification: Directly reusable code under MIT-0, with separate review required for external ASM/schema/data content.
- Scores:
  - Technical value: High
  - Commercial value: High as an onboarding accelerator rather than standalone SaaS
  - Rarity: High
  - Completeness: High
  - Build-time saved: High
  - Data advantage: Medium-High
  - High-ticket potential: High in combination with the service stack
- Next action: Prototype a controlled unsupported-instrument onboarding loop where generated converters cannot enter production until schema validation and source-to-output field-map review pass; use this as the long-tail adapter factory behind the deterministic Allotropy parsers.

### NatLabRockies/ALchemist
- Repository: https://github.com/NatLabRockies/ALchemist
- Commit / revision: 02c7a6eaa5a8e75bb65d0292b9b8d9a5e08301cf
- Date discovered: 2026-09-19
- What it contains: A low-attention but unusually complete active-learning and Bayesian-optimization platform for chemical/materials experiments. It has a headless Python session API, BoTorch/scikit-learn surrogate models, qEI/qPI/qUCB and variance-oriented acquisition strategies, multi-objective/Pareto tooling, a broad DoE suite, a FastAPI REST layer, React web UI, desktop GUI, WebSocket live monitoring, interoperable JSON sessions, and a staged experiment work queue for autonomous reactor/lab workflows.
- Why it matters: It supplies the missing experiment-selection/orchestration layer above hardware-control systems such as PyLabRobot. The inspected revision contains a real ordered/thread-safe ExperimentQueue with per-item state/reason/completion/failure, REST endpoints, web monitoring, unit tests, and durable suggested-vs-actual provenance. The latest commit specifically added per-experiment provenance joined by ProvenanceId; model code excludes that provenance metadata from the feature matrix, reducing a subtle data-leakage risk.
- Commercial possibilities: Closed-loop experimental optimization product for chemical, catalysis, battery, materials, and biotech R&D; paid deployment that connects a customer's existing instruments to an auditable optimization queue; campaign-optimization service; or an optimization layer paired with PyLabRobot/device adapters and the existing instrument-normalization stack. High-value buyers can justify implementation fees when each experiment is expensive or slow.
- Build-time savings: Roughly 4-9 months for Bayesian optimization/DoE, session management, API/UI, autonomous queueing, provenance, and monitoring infrastructure; potentially more when paired with existing hardware integrations.
- Evidence inspected: Repository metadata (8 stars, BSD-3-Clause); exact latest commit metadata; README.md; recursive source tree; alchemist_core/queue.py and queue-related code search; api/routers/experiments.py; alchemist_core/session.py; audit/provenance code search; tests/unit/core/test_experiment_queue.py, test_session_queue_delegation.py, test_provenance.py; React queue/monitoring hooks/tests. The repository is packaged to PyPI and has CI/test workflows.
- License / rights: BSD-3-Clause.
- Reuse classification: Directly reusable subject to BSD-3-Clause notice/attribution conditions and third-party dependency licenses.
- Scores:
  - Technical value: Very High
  - Commercial value: Very High
  - Rarity: High
  - Completeness: Very High
  - Build-time saved: Very High
  - Data advantage: Medium
  - High-ticket potential: Very High
- Next action: Connect ALchemist's staged experiment queue to a PyLabRobot simulator or supported instrument workflow and demonstrate one closed-loop optimization campaign with suggested-vs-actual provenance and a reproducible audit trail.

### Noel-Research-Group/Robochem_Flex
- Repository: https://github.com/Noel-Research-Group/Robochem_Flex
- Commit / revision: 672240f184846af3e2014802aea29645de562fb2
- Date discovered: 2026-09-19
- What it contains: A modular self-driving chemistry laboratory stack covering physical device designs plus control/optimization software. The control framework combines a Streamlit UI, OmniPlatypus hardware control for pumps/valves/sensors/analytics, RoBrains Bayesian/evolutionary optimization, and LAMAS spectral analysis. The repository also includes CAD/firmware/PCB resources, example campaign configs, a dry-run mode, package-level LICENSE/NOTICE files, and substantial unit-test code.
- Why it matters: This is not just an optimizer or robot SDK; it is a permissively licensed reference for the whole autonomous chemistry loop from hardware through analytics and optimization. RoBrains contains single/multi-objective BoTorch optimization, batched BO, categorical embeddings, multi-fidelity and multi-task optimization, human-in-the-loop communications, custom surrogates/acquisitions, and explicit tests for platform/HITL/assistant paths. LAMAS adds tested spectroscopy/deconvolution code. Recreating this vertical integration would be slow and hardware-specific.
- Commercial possibilities: Implementation/support offering for academic and industrial flow-chemistry labs; low-cost autonomous reaction-optimization deployments; a reference hardware/software kit for process-development groups; or selected Apache-licensed optimization/analytics components reused in a narrower validated laboratory product. It can also inform hardware adapters beneath ALchemist or other optimization layers.
- Build-time savings: Approximately 6-12+ months of hardware/software integration, experiment-control, optimization, spectral-analysis, and GUI work if the target workflow aligns with the supported modules.
- Evidence inspected: Repository metadata (43 stars, Apache-2.0); exact latest commit metadata; root README and Apache licensing statement; Control Software/README.md; recursive tree; RoBrains README; RoBrains source search for SingleBayesianOptiBackend and multi-fidelity/batched variants; tests/test_bayes_opti_Platform.py, test_bayes_opti_HITL.py, test_bayes_opti_ASSISTANT.py, test_dummy_HITL.py; LAMAS implementation/test tree. README documents a CS0_dryrun campaign for testing without hardware.
- License / rights: Apache-2.0 with NOTICE files present in inspected software subpackages.
- Reuse classification: Directly reusable subject to Apache-2.0/NOTICE requirements and third-party dependency/hardware-component licenses.
- Scores:
  - Technical value: Very High
  - Commercial value: High
  - Rarity: Very High
  - Completeness: High
  - Build-time saved: Very High
  - Data advantage: Medium
  - High-ticket potential: Very High
- Next action: Run the documented dry-run campaign and isolate the smallest commercially useful stack (optimization + one analytics/device path) before considering real hardware; separately review physical safety/validation requirements for any automated chemical execution.

### BattModels/ElyteAgent
- Repository: https://github.com/BattModels/ElyteAgent
- Commit / revision: 415ddd6b3b29bef324b1f10d8fc0ac3feb4f3569
- Date discovered: 2026-09-19
- What it contains: A zero-star MIT-licensed autonomous battery-electrolyte experimentation stack. ElyteOS coordinates device control, inventory, scheduling, database storage and visualization, while ElyteAgent uses four LangGraph agents for natural-language design-space creation, inventory/solubility feasibility checking, hardware execution/error recovery, and closed-loop experiment selection. The repository includes real pump/valve/balance/potentiostat/thermometer/camera control modules and a candidate optimizer that ranks compositions by a UCB-like nearest-neighbor surrogate before passing them through the inventory/feasibility solver.
- Why it matters: Battery-electrolyte R&D is a narrow, expensive vertical where experiment throughput and formulation feasibility directly affect development cost. This repository provides both a commercially interesting orchestration pattern and substantial device/domain code rather than a generic agent demo. The inspected optimizer enforces solvent simplex/salt bounds and inventory feasibility; the experiment tool layer performs connection checks, solvent mixing, balance/density measurement, conductivity measurement, temperature measurement, retries/stateful resumption, and result storage.
- Commercial possibilities: Battery R&D electrolyte optimization workbench; paid automation/integration for labs using compatible hardware; clean separation of formulation proposal, feasibility, execution and recovery for a high-value vertical; or reuse of MIT-licensed planning/orchestration concepts inside a safer simulator-first optimization service. Best fit is a high-ticket implementation/pilot rather than mass-market SaaS.
- Build-time savings: Roughly 3-6 months of battery-specific orchestration, formulation-feasibility, device-control, and closed-loop optimization work; more if the buyer's hardware overlaps the provided Clio/SALSA-style stack.
- Evidence inspected: Repository metadata (0 stars, MIT); exact revision; README.md; recursive source tree; src/Agent/BeysianOptimization.py; src/Agent/Experiment_Tools.py. The optimizer implements candidate generation, normalization, UCB ranking and pulp_solve_sorted feasibility checks. The experiment tools call actual Equipment_Control modules for pumps, valves, balance, potentiostat, thermometer and camera. Important limitation: the inspected viscosity routine has the real measurement block commented out and currently assigns a placeholder value, so viscosity automation must not be treated as production-ready. No dedicated pytest suite was found in the inspected code search. Bundled database/log/generated-session artifacts were deliberately not inspected or retained.
- License / rights: MIT for repository code. Hardware/vendor SDK or instrument bindings may carry their own terms and must be checked separately before redistribution/deployment.
- Reuse classification: Directly reusable code subject to MIT terms, with third-party hardware/SDK rights and physical-lab validation handled separately.
- Scores:
  - Technical value: Very High
  - Commercial value: High
  - Rarity: Very High (0-star functioning vertical stack)
  - Completeness: Medium-High
  - Build-time saved: High
  - Data advantage: Medium
  - High-ticket potential: Very High
- Next action: Isolate the planner/feasibility/orchestration path from physical hardware and validate it on a fully synthetic electrolyte campaign; only then audit each hardware routine and safety interlock before any real-world execution.

### ulfsri/lab-etl
- Repository: https://github.com/ulfsri/lab-etl
- Commit / revision: a45d56849a924f8ce9034b15085c704118777252
- Date discovered: 2026-09-19
- What it contains: A one-star MIT laboratory ETL library focused on materials-property and fire-science instruments. It converts heterogeneous instrument exports into Apache Parquet while preserving file-level and column-level metadata. The inspected revision has concrete parsers for Bruker FTIR, Deatak cone calorimetry, FAA microscale combustion calorimetry, FOX heat-flow meter, and NETZSCH STA formats, plus CI, docs and parser tests.
- Why it matters: It is a standards-neutral complement to the Allotrope-based stack. Each parser emits schema-enforced Arrow/Parquet data while retaining instrument-specific metadata, units and source hashes, avoiding dependence on Allotrope ASM content for these workflows. The code's metadata helper stores table/column metadata directly in Arrow schemas, and tests write parsed tables to Parquet. This is useful for materials/safety labs whose instruments fall outside the biotech-heavy parser coverage found earlier.
- Commercial possibilities: Fixed-fee instrument-data migration/normalization for materials, fire-safety and industrial labs; Parquet-based scientific data lake ingestion; legacy thermal/FTIR/calorimetry archive conversion; or an alternate output backend behind the existing lab-data gateway when customers want open Parquet rather than ASM JSON.
- Build-time savings: Roughly 1-3 months for the represented instrument parsers, metadata conventions and Parquet/schema plumbing; potentially more for customers with historical archives in exactly these formats.
- Evidence inspected: Repository metadata (1 star, MIT); exact latest default-branch revision; README.md; recursive source tree; parser modules and sizes; src/labetl/util.py metadata helper via code search; parser uses of set_metadata; tests/test_faa_mcc_parser.py and tests/test_netzsch_sta_parser.py showing Parquet writes; CI/LICENSE files in tree.
- License / rights: MIT. Instrument file formats, vendor trademarks, and any bundled fixtures should still be reviewed independently if redistributed.
- Reuse classification: Directly reusable subject to MIT terms; separately confirm rights for any third-party sample/fixture data used outside testing.
- Scores:
  - Technical value: High
  - Commercial value: Medium-High
  - Rarity: High
  - Completeness: High for its narrow instrument set
  - Build-time saved: High
  - Data advantage: Medium-High
  - High-ticket potential: High in targeted industrial/materials labs
- Next action: Add these parsers as a Parquet-oriented branch of the existing instrument-normalization pilot and test whether they cover a buyer segment not well served by the Allotropy/ASM route.
