# AI / Models / Algorithms

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

### ashita-ai/conduit
- Repository: https://github.com/ashita-ai/conduit
- Commit / revision: `e93981c0d9304fc7fbff21b3771a77d81429ec2b`
- Date discovered: 2026-09-19
- What it contains: A functioning Python adaptive LLM-routing stack that learns cost/quality/latency tradeoffs. The inspected revision includes a Router wired to analysis, execution, evaluation and feedback; multiple online-learning/bandit engines (Thompson Sampling, contextual Thompson Sampling, LinUCB, UCB, epsilon-greedy, dueling and baselines); hybrid routing; model/provider execution; optional Redis caching; PostgreSQL/Alembic persistence; API and CLI surfaces; Docker assets; observability; and unit/integration/regression tests.
- Why it matters: The repository is archived and had only 4 stars / 5 forks when inspected, yet contains substantially more working decision-learning infrastructure than its visibility suggests. Unlike a static "cheapest model" gateway, it already implements the feedback loop needed to learn which model is economically best for different request contexts while respecting quality/cost/latency objectives. This collapses much of the difficult experimentation and state-management work behind an adaptive inference-cost product.
- Commercial possibilities: An "AI Spend Autopilot" / adaptive inference gateway for B2B AI products: route each workload to the lowest-cost model that satisfies tenant-specific quality and latency SLOs, learn from observed outcomes, report savings versus a fixed-model baseline, and price as enterprise SaaS or a share of verified inference savings. A second wedge is per-workflow model optimization for companies running large multi-model agent/evaluation fleets.
- Build-time savings: Estimated 8–14 weeks for an experienced team to recreate the adaptive routing, contextual-bandit implementations, feedback plumbing, persistence, API/CLI, cache/database integration and test harness to a comparable starting point.
- Evidence inspected: `conduit/engines/router.py`; `conduit/engines/hybrid_router.py`; `conduit/engines/bandits/` implementations including Thompson Sampling, contextual Thompson Sampling, LinUCB, UCB, epsilon-greedy, dueling and baselines; `tests/integration/test_feedback_loop.py` confirming route -> outcome -> reward/update behavior; integration tests for API routes, persistence, cache, concurrent updates, database integration, graceful shutdown, hybrid transition and LiteLLM learning; `.github/workflows/ci.yml`, which runs lint/format/type checks plus unit/integration/regression suites with PostgreSQL 16/Alembic and an 80% coverage floor; Docker/Alembic/API project structure. Repository metadata and MIT license were also inspected at this revision.
- License / rights: MIT License, copyright 2025 Evan Volgas. Commercial use, modification, distribution, sublicensing and sale are permitted subject to preservation of the copyright and license notice.
- Reuse classification: Directly reusable.
- Scores:
  - Technical value: 9/10
  - Commercial value: 9/10
  - Rarity: 9/10
  - Completeness: 9/10
  - Build-time saved: 9/10
  - Data advantage: 6/10
  - High-ticket potential: 9/10
- Next action: Benchmark the adaptive router against fixed strongest-model, fixed cheapest-model and static-rule baselines on a representative evaluation suite. Measure cost per successful task, quality-gate pass rate, latency and bandit regret; refresh current provider/model pricing and priors; then audit multi-tenant isolation, auth, rate limiting and exploration guardrails before hosted commercialization. The project is archived, so provider/model drift and dependency maintenance must be treated as first-class hardening work.

### airbnb/agent-harness-optimizer
- Repository: https://github.com/airbnb/agent-harness-optimizer
- Commit / revision: `0d7652b42296c8df07532fa3787fc956250741e7`
- Date discovered: 2026-09-19
- What it contains: A benchmark-agnostic Python framework for automatically optimizing LLM agent harnesses, including both system prompts and tool-call middleware. The inspected revision includes abstract Benchmark/Optimizer interfaces; BFCL and tau-bench adapters; PRISM, BetterHarness, GEPA and MIPROv2 optimization paths; train/holdout evaluation; Pareto acceptance; failure clustering/history; mutation and crossover loops; generation persistence and resume; reporting/diffs; reproducibility configs; a CLI; and a self-contained mock-benchmark test path. PRISM is substantive rather than a stub: its loop performs root-cause-driven prompt/middleware mutation, parallel train/holdout scoring, conditional crossover on complementary failures, Pareto-frontier updates, failure-state labeling (FIXED/NEW/PERSISTENT/RECURRING), checkpoint persistence and resume.
- Why it matters: The repository had only 3 stars / 0 forks when inspected despite being a substantial Airbnb release. It addresses a different optimization layer from adaptive model routing: instead of merely choosing a model, it searches the agent harness itself, including executable middleware around tool calls. That makes it a rare build-time compressor for teams whose expensive problem is agent reliability, tool-use accuracy and regression control rather than raw model selection. It combines unusually well with the existing `ashita-ai/conduit` finding: optimize the harness offline, then optimize model choice online.
- Commercial possibilities: An "Agent Reliability Optimizer" for B2B AI teams: ingest an existing agent plus a customer-specific evaluation suite or sanitized production-derived cases, search system-prompt and constrained middleware variants, prove improvement on held-out cases, and return reviewable diffs before deployment. A high-ticket wedge is outcome-based agent performance engineering for support, internal operations, sales operations or other tool-using agents where failed actions have measurable labor/revenue cost. A second product is a continuous regression/optimization service that re-runs after model, tool-schema or workflow changes.
- Build-time savings: Estimated 10–18 weeks for an experienced team to recreate the optimizer abstractions, evolutionary/Pareto search loops, failure matrix, mutation/crossover workflow, benchmark adapters, checkpoint/resume behavior, reporting, CLI and test harness to a comparable starting point.
- Evidence inspected: Repository metadata and commit `0d7652b42296c8df07532fa3787fc956250741e7`; `.github/workflows/ci.yml` showing Python 3.12 lint/format/tests with a 20% coverage floor; `CONTRIBUTING.md` describing the benchmark/optimizer architecture and self-contained mock-benchmark tests; `pyproject.toml` showing the Apache-2.0 package, CLI, core dependencies, pinned tau-bench dependency and optional MIPROv2/GEPA extras; `agent_harness_optimizer/optimizers/` containing BetterHarness, GEPA, MIPROv2 and PRISM; `agent_harness_optimizer/optimizers/prism/loop.py` and the substantive PRISM evolutionary/Pareto implementation; `tests/test_prism_loop.py` verifying generation creation, stats/report output, cache artifacts and resume behavior; the broader `tests/` tree including acceptance, middleware-surface, PRISM ablation, split and framework tests; and `agent_harness_optimizer/benchmarks/` containing substantial BFCL and tau-bench adapters. BFCL case data are explicitly not redistributed by the repo and must be obtained under their own terms.
- License / rights: Apache License 2.0 for the repository code, with the normal notice/license and patent conditions. External dependencies, benchmarks and datasets retain their own licenses/terms; notably BFCL case data are not bundled. No private data, credentials or accidental disclosures were used.
- Reuse classification: Directly reusable, subject to Apache-2.0 obligations and separate rights for external benchmark data/dependencies.
- Scores:
  - Technical value: 9/10
  - Commercial value: 9/10
  - Rarity: 9/10
  - Completeness: 8/10
  - Build-time saved: 9/10
  - Data advantage: 4/10
  - High-ticket potential: 9/10
- Next action: Build one customer-style benchmark adapter from a lawful sanitized helpdesk/order-management or internal-operations agent trace set, then compare PRISM against BetterHarness and a prompt-only baseline on held-out task pass rate, tool-error rate, cost per successful task and latency. Before any commercial auto-optimization, sandbox middleware execution, constrain editable code surfaces (for example via allowlisted files/AST patterns), require human code review before deployment, and test the combined pattern with `ashita-ai/conduit`: offline harness optimization first, adaptive model routing second.
