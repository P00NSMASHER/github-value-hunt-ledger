# GitHub Value Hunt Ledger

Private persistent memory for the GitHub Value Hunt.

## Operating model
- Start operational runs with [`intelligence/WORKER_RUNBOOK.md`](intelligence/WORKER_RUNBOOK.md). It points to the current assignment, claim, evidence and telemetry contracts. The [2026-09-21 strategy upgrade](intelligence/STRATEGY_UPGRADE_2026-09-21.md) explains the latest changes and their evidence limits.
- Fifteen scheduled hunter roles are used: **14 research workers plus Hunt 15 / MASTER Integrator**. The 14 research workstreams search across the **47 thematic catalogs** under `hunters/`; catalog numbers are domain indexes, not necessarily one-to-one automation identities.
- Every hunter reads the relevant thematic catalog(s), `MASTER.md`, `SEARCH_QUEUE.md`, `REJECTED.md`, and `COMBINATIONS.md` before searching.
- Every materially inspected candidate should leave durable evidence in the appropriate hunter catalog as strong/watch/rejected so sibling work does not repeat it.
- New findings must be evidence-backed and deduplicated by **repository + exact revision + capability**, not repository name alone.
- Hunt 15 / MASTER Integrator owns cross-lane synthesis: `MASTER.md`, `COMBINATIONS.md`, `REJECTED.md`, `SEARCH_QUEUE.md`, `DATASETS.md`, `COMPONENTS.md`, `OPPORTUNITIES.md`, and `EXPOSURES_INDEX.md`.
- MASTER is intentionally elite. A candidate normally needs **24+/30** on A speed to revenue, B plausible ACV/ceiling, C build/domain compression, D rarity/technical advantage, E evidence/completeness, and F rights/reuse clarity; lower scores require a uniquely important role in a stronger stack.
- Standing user assertion dated 2026-09-19: the user states they hold separate commercial permission/license for repository-owned code/content in every PUBLIC GitHub repository discovered in this hunt. Therefore public license category is provenance metadata, not a search-value penalty. Record the actual published license exactly. Do not extend this assumption to independently owned datasets, model weights, standards/specifications, trademarks, patents, bundled assets, commercial APIs/services, or customer data.
- Safety overrides commercial-rights assumptions. Never collect, preserve, reproduce, test, exploit or monetize exposed credentials, authentication material, private/personal data, accidentally published confidential information, leaked trade secrets, vulnerabilities or unauthorized-access material. Record only redacted non-sensitive exposure metadata when necessary.

## Shared indexes
- `MASTER.md` — elite repository/software leaders and uniquely important components.
- `COMBINATIONS.md` — multi-repository product stacks with named buyers and falsifiable validation paths.
- `SEARCH_QUEUE.md` — current complementary search directions, unresolved evidence gaps and stop-list guidance.
- `REJECTED.md` — cross-lane dead ends, dominated finds, misleading surfaces and safety/rights traps likely to be rediscovered.
- `DATASETS.md` — elite datasets, authoritative public-data pipelines, schemas and hard-to-recreate data advantages.
- `COMPONENTS.md` — reusable infrastructure/components that compress stronger products.
- `OPPORTUNITIES.md` — prioritized monetizable offers, services and product combinations.
- `EXPOSURES_INDEX.md` — **redacted metadata only** for accidental sensitive-material encounters; never raw values.

## Finding schema
Each retained finding should include:
- Repository + canonical URL
- Exact commit/revision inspected
- Date discovered
- Thematic catalog / lane
- Category: Repository / Dataset / Reusable Component / Business Opportunity
- What it contains
- Why it matters / rare value
- Buyer and painful problem
- First paid wedge / monetization path
- Build-time or data advantage
- Evidence inspected beyond README where practical
- Actual published license / rights metadata
- Standing separate-commercial-permission posture and any separately governed third-party dependencies
- A–F score where meaningful
- Combination opportunities
- Next action / validation gap

## Reuse / evidence posture
- Repository-owned code/content may be treated as commercially authorized under the standing user assertion while preserving actual public license provenance.
- Third-party standards, datasets, model weights, media/assets, trademarks, patents, APIs/services and customer data require their own authority/terms.
- Unknown or contradictory evidence stays unknown/review. In money-bearing audit/recovery stacks, unresolved authority, entitlement, identity or outcome defaults to **$0 asserted recovery**.
- “Rare/secret” means obscure, undernoticed, non-obvious, little-known or unusually hard-to-recreate lawful public material. It does **not** mean accidental secrets or confidential/private material.

# Hunter Catalogs

Hunters write materially inspected results into the relevant files under `hunters/` and preserve sibling content. The cross-hunt integrator performs promotion/demotion and cross-lane indexing without using MASTER as a long archive.

## Hunter index
- 01: Abandoned SaaS & forgotten products
- 02: Enterprise B2B workflows
- 03: Freight, logistics & transportation
- 04: Construction, estimating & change orders
- 05: GovCon, procurement & contracting
- 06: Permits, property & real-estate intelligence
- 07: Finance, AP audit & recovery
- 08: Insurance, claims & risk operations
- 09: Legal, compliance & public-record workflows
- 10: Healthcare operations & admin tooling (no PHI)
- 11: Energy, utilities & grid operations
- 12: Manufacturing & industrial operations
- 13: Supply chain, inventory & warehouse systems
- 14: Defensive security & compliance tooling
- 15: DevOps, infrastructure & reliability
- 16: Data engineering, ETL & lineage
- 17: OCR, document intelligence & extraction
- 18: Entity resolution, deduplication & matching
- 19: AI model tooling, evaluation & inference
- 20: Scientific software & computational research
- 21: Biotech, laboratory & instrumentation automation
- 22: Geospatial, mapping & location intelligence
- 23: Climate, weather & environmental data systems
- 24: Agriculture, food & field operations
- 25: Education, assessment & learning systems
- 26: Games, virtual goods & consumer engagement
- 27: E-commerce, marketplace & merchant tooling
- 28: Sales, marketing & revenue operations
- 29: Pricing, yield & revenue-management engines
- 30: Payments, billing, subscriptions & invoicing
- 31: Tax, accounting & regulatory automation
- 32: HR, workforce & scheduling operations
- 33: Facilities, maintenance & property operations
- 34: Mobility, routing & fleet optimization
- 35: Telecom, networking & service operations
- 36: Procurement, vendor & spend management
- 37: Customer support, contact center & service ops
- 38: Optimization, scheduling & operations research
- 39: Forecasting, anomaly detection & decision systems
- 40: Workflow automation, RPA & orchestration
- 41: Vertical CRM, ERP & line-of-business systems
- 42: Public datasets, APIs, schemas & standards parsers
- 43: Obscure academic prototypes with commercial potential
- 44: Archived enterprise-grade open-source systems
- 45: No-license reference architectures & clean-room ideas
- 46: Rare algorithms, benchmarks & unusual technical methods
- 47: Wildcard cross-domain opportunity hunter
- 48: Cross-hunt integrator


# Knowledge-to-Value Layer

The hunt is not complete when a repository is found. The system must convert research into reusable capability, a ranked commercial opportunity, a falsifiable experiment and eventually a recorded outcome.

## Additional shared indexes
- `CAPABILITIES.md` — canonical inventory of reusable abilities the system can now credibly perform.
- `TECHNOLOGY_RADAR.md` — emerging capability categories, evidence signals and commercial implications.
- `KNOWLEDGE_GRAPH.md` — edges linking repositories/data -> capabilities -> opportunities -> experiments -> outcomes.
- `EXPERIMENTS.md` — prioritized falsifiable tests that convert research into technical or economic evidence.
- `OUTCOMES.md` — completed experiment/customer/value results used to train future search priority.
- `SEARCH_SKILLS.md` — reusable discovery methods that have produced evidence-backed value.
- `intelligence/COORDINATION_PROTOCOL.md` + `COORDINATION_BOARD.md` — immutable cross-hunter handoffs and the integrator-owned compact view of unresolved shared learning.
- `intelligence/NETWORK_PRIORS.md` — compact generated memory for live hunters: current constraints, gaps, duplicate/provenance pressure, learned move priors and recall rules.
- `intelligence/SEARCH_MOVE_REPORT.md` + `SEARCH_MOVE_POLICY.md` — observe-first learning/curriculum for individual retrieval moves rather than only whole-hunt strategies.
- `intelligence/EFFICIENCY_REPORT.md` — duplicate-preflight savings and effort denominators, without rewarding shallow work.

## Closed-loop operating model

RESEARCH
-> VERIFIED FINDING
-> CAPABILITY
-> COMBINATION
-> OPPORTUNITY
-> EXPERIMENT
-> OUTCOME
-> SEARCH-POLICY UPDATE

A new finding is more valuable when it:
1. creates or materially strengthens a reusable capability;
2. closes a missing edge in a high-value combination;
3. improves a top opportunity;
4. creates a cheaper/faster falsifiable experiment;
5. changes an existing experiment's success criteria;
6. explains a recorded success or failure.

## Hunter value handoff
Every hunter run should report, when applicable:
- CAPABILITY DELTA — what can the system now do that it could not do before?
- GRAPH EDGE — which existing capability/opportunity/experiment becomes stronger or weaker?
- RADAR SIGNAL — what emerging category gains or loses evidence?
- EXPERIMENT IMPACT — which current experiment should change?
- COMMERCIAL IMPACT — does this alter buyer, wedge, economics, build compression or moat?
- NEGATIVE KNOWLEDGE — what should not be searched/built again?

Hunters keep durable evidence in their assigned catalogs. They should not race one another editing the central value files.

## Integrator duties
Hunt 15 / MASTER Integrator owns central synthesis and should update, when evidence changes:
- `MASTER.md`
- `DATASETS.md`
- `COMPONENTS.md`
- `CAPABILITIES.md`
- `TECHNOLOGY_RADAR.md`
- `KNOWLEDGE_GRAPH.md`
- `COMBINATIONS.md`
- `OPPORTUNITIES.md`
- `EXPERIMENTS.md`
- `OUTCOMES.md`
- `REJECTED.md`
- `SEARCH_QUEUE.md`
- `SEARCH_SKILLS.md`

The integrator should promote capability knowledge rather than repository count, and use recorded experiment/outcome evidence to raise or lower future search priority.

## Portfolio KPIs
Track over time:
- validated reusable capabilities;
- capabilities reused across two or more products;
- experiments completed;
- experiments surviving adversarial tests;
- opportunities reaching authorized external validation;
- opportunities reaching paid validation;
- realized revenue/customer value traced to the research system;
- build-time compression actually observed;
- MASTER findings that materially change an experiment;
- search skills producing successful outcomes;
- search strategies repeatedly producing dead ends.

## Stage-gate rule
Do not launch another product simply because a new repository is exciting. First ask whether it:
- strengthens an existing experiment;
- creates a better experiment;
- materially changes a capability/opportunity;
- or invalidates an existing assumption.

The desired endpoint is not a larger repository ledger. It is a self-improving private technology-intelligence and venture-discovery system.


## Production architecture
The next-generation verifier-gated system is staged under `production/`:
- `production/ARCHITECTURE.md` — authority boundaries and state machines.
- `production/ROLE_CONTRACTS.md` — typed hunter/verifier/red-team/integrator contracts.
- `production/PROMPTS.md` — production role prompts.
- `production/prototype.py` + `test_prototype.py` — deterministic promotion, evidence, skill and lease prototype.
- `production/schema.sql` — reference authoritative-state schema.
- `production/SHADOW_PILOT.md` — post-benchmark three-hunter shadow protocol.
- `production/STATUS.md` — what is live versus staged.
- `production/SECURITY_TEST_PLAN.md` — required fail-closed launch tests.

The frozen benchmark remains unchanged and must finish before fleet-wide cutover.


## Machine-readable technology-intelligence loop

The durable Markdown research record is now paired with a structured empirical-learning layer under `intelligence/`.

For the Freight business, start with the [September 21 business audit](freight/BUSINESS_AUDIT_2026-09-21.md), [commercial playbook](freight/COMMERCIAL_PLAYBOOK.md), and [Hunter connection](freight/HUNTER_CONNECTION.md). The connection maps registry capabilities into reviewed freight applications and a change queue. The [recovered marketing source](freight/site/README.md) requires a verified business inbox and a repaired deployment before public launch; it is separate from customer-data processing.

Every materially completed hunt cycle must:
1. keep the detailed evidence in the appropriate `hunters/*.md` catalog;
2. submit one immutable prospective record to `intelligence/search_run_spool/` for validated single-writer ingestion into `intelligence/search_runs.jsonl`;
3. identify the stable `STRAT:...` strategy used and the reusable query family;
4. record candidate/deep-inspection/retention/promotion denominators without inventing missing values;
5. link any created/strengthened `CAP-###` nodes and affected `EXP-###` experiments;
6. when an experiment or buyer validation finishes, append the result to `intelligence/outcomes.jsonl` with explicit originating search-run IDs.

The machine graph uses stable node/edge IDs and is validated by `tools/ti_validate.py`. `tools/ti_report.py` computes search-strategy/query-family yield with minimum-sample safeguards and Wilson intervals. The generated report lives at `intelligence/LEARNING_REPORT.md`.

**Policy:** do not reduce exploration based on anecdotal performance. Automatic expand/retire decisions require at least 5 measured runs and 20 deep inspections for the relevant strategy/query family. Realized technical/customer outcomes outrank predicted value scores.


## Empirical hunt instrumentation

The hunt now has an adaptive measurement layer under `intelligence/`.

Before a costly deep inspection, check prior repository evidence using `python tools/ti_lookup.py owner/repo` when a checkout is available, or inspect the corresponding hunter catalogs through GitHub.

Every materially completed prospective hunt must submit one immutable record through `intelligence/search_run_spool/` for canonical ingestion using the current [`intelligence/SEARCH_RUN_TEMPLATE.json`](intelligence/SEARCH_RUN_TEMPLATE.json) and the provenance requirements in the [worker runbook](intelligence/WORKER_RUNBOOK.md). Record actual denominators and do not estimate missing historical counts. Candidate dispositions should use the standardized reason taxonomy in `intelligence/reason_codes.json` where applicable. Historical records retain their original schema version; a newer schema is not permission to fabricate missing historical fields.

The generated reports answer different questions:
- `REGISTRY_REPORT.md`: how much has already been hunted and where duplication is occurring;
- `DATA_QUALITY_REPORT.md`: whether search instrumentation is trustworthy enough to learn from;
- `GRAPH_HEALTH.md`: which capabilities are under-supported or disconnected from experiments;
- `LEARNING_REPORT.md`: empirical strategy/query-family yield;
- `SEARCH_POLICY.md`: cautious next-cycle allocation balancing measured yield and exploration.

The allocation policy is advisory and deliberately keeps an exploration floor so low-attention, strange and cross-domain discoveries are not optimized away.


### Measurement controls

The machine-learning layer now distinguishes exact queries, canonical query families, broader search objectives and search strategies. It also normalizes search-surface labels, controlled candidate disposition reasons and exact-revision debt.

Matched strategy comparisons use the frozen benchmark task set and `benchmark/STRATEGY_MEASUREMENT_PROTOCOL.md`. These comparisons are deliberately separate from commercial opportunity search so strategy measurement does not distort the active product roadmap.

The current run template is authoritative for new-record schema and fields. Current evidence counts and learning modes belong in the generated reports, not duplicated prose: see [`LEARNING_REPORT.md`](intelligence/LEARNING_REPORT.md), [`ALLOCATOR_LEARNING_REPORT.md`](intelligence/ALLOCATOR_LEARNING_REPORT.md) and [`ROUTING_LEARNING_REPORT.md`](intelligence/ROUTING_LEARNING_REPORT.md). Generated priorities are scheduling recommendations; they do not establish strategy superiority or override experiment stop conditions.

## Adaptive hunter learning engine

The staged production layer now includes `production/LEARNING_ENGINE.md` and `production/learning_engine.py`.

Every build can derive `intelligence/LEARNING_STATE.json` from canonical search runs and linked outcomes. It maintains outcome-weighted utility for strategies/query families/search moves while preserving the existing exploration and evidence thresholds. Only priors that clear the 5-run / 20-deep train gate and an independent confirm gate are exposed to hunters through `NETWORK_PRIORS.md`; confirm assignment is bound to validated pre-hunt generated claim provenance, not a worker-chosen run ID. The learning state never overrides assignment, STOP, verifier, benchmark, safety or promotion rules.

Reproducible defects in hunter skills/tools/prompts/workflows can be submitted as immutable packets under `intelligence/learning_failure_spool/`. They must include evidence, reproduction steps and a proposed regression test. Queueing a defect does not authorize an automatic repair or global skill change.

### Repair workbench

The adaptive learning layer now generates `intelligence/REPAIR_QUEUE.json` and `intelligence/REPAIR_QUEUE.md`.

Confirm overfit/regression signals enter as `NEEDS_REPRODUCTION` and cannot authorize mutation. Only a non-sensitive, non-benchmark-contaminated immutable learning-failure packet with reproduction steps, evidence and a concrete regression test can become `READY_FOR_REPAIR`. Even then, the workbench permits only one bounded candidate repair; it cannot edit a live/global skill, route itself to a worker, change verifier/evaluator/controller logic, or bypass held-out/canary promotion gates.

### Repair candidate intake

Candidate fixes are submitted through `intelligence/repair_candidate_spool/` using `REPAIR_CANDIDATE_TEMPLATE.json`. A candidate must match the exact current repair task and SHA-256, declare exactly one authorized logical target, freeze baseline/candidate artifact refs and the full diff hash, and supply the exact required regression test plus evidence.

Passing intake produces only `READY_FOR_SKILL_EVAL` in `REPAIR_CANDIDATE_INTAKE.json` / `SKILL_EVAL_QUEUE.md`. It cannot write the live skill or bypass the independent evaluation/canary/global gates.

### Skill evaluation result intake

Independent evaluator results are submitted through `intelligence/skill_eval_result_spool/`. They must bind to the exact current skill-evaluation task and candidate hashes, use distinct frozen mutate-dev/promotion-test set fingerprints, preserve evaluator/holdout isolation, and provide durable evidence.

Passing evaluation produces only `STAGED_MUTATION` in `SKILL_EVAL_RESULT_INTAKE.json` and an entry in `SKILL_PROMOTION_QUEUE.md`. It cannot deploy or globally promote the candidate.

