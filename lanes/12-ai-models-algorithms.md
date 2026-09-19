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
