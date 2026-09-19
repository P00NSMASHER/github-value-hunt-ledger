# GovCon / CaptureBrief

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
### MindPetal/sam-search
- Repository: https://github.com/MindPetal/sam-search
- Commit / revision: 019b31dca0f980e79117a7c559777cb357a2a385
- Date discovered: 2026-09-19
- What it contains: Small but functioning Python SAM.gov opportunity search client with NAICS filtering, date handling, formatting, GitHub Actions execution, Teams posting, generated API client code, configuration, and tests.
- Why it matters: It proves and packages the core SAM.gov opportunity-ingestion loop needed by CaptureBrief, including daily scheduled retrieval and normalization/formatting logic.
- Commercial possibilities: Reuse the ingestion layer inside CaptureBrief while replacing Teams delivery with qualification, evidence linking, scoring, and customer-specific opportunity workflows.
- Build-time savings: Medium-High for reliable SAM.gov ingestion and scheduled search plumbing.
- Evidence inspected: README.md; search.py with SAM API calls, formatting, date/set-aside handling; test_search.py with pytest coverage for API search and formatting behavior.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT terms.
- Scores:
  - Technical value: Medium
  - Commercial value: High as a CaptureBrief component
  - Rarity: Medium
  - Completeness: Medium-High for its narrow purpose
  - Build-time saved: Medium-High
  - Data advantage: Medium
  - High-ticket potential: Medium-High when embedded in a decision product
- Next action: Map its returned SAM fields to CaptureBrief's evidence model and design around the documented non-federal API request limit rather than copying its Teams-oriented output layer.

### capture-intelligence/award-lens
- Repository: https://github.com/capture-intelligence/award-lens
- Commit / revision: a4fb46e53887c7775bd6e4c99bf6bd6870749dc4
- Date discovered: 2026-09-19
- What it contains: A surprisingly complete federal-procurement intelligence stack with USAspending, Grants.gov, and SAM public-extract ingestion; canonical award/vendor/agency/office normalization; deterministic external-ID mapping and atomic upserts; SAM exclusion handling; a Cloudflare Worker API, D1/KV/Vectorize data tier, React dashboard, scoped/user-aware views, CI/deployment workflows, an Oracle sidecar ingestion design, and an optional multi-model natural-language analytics layer.
- Why it matters: This is much more than another SAM search wrapper. It supplies a low-fixed-cost historical award and vendor-intelligence substrate that CaptureBrief could use for incumbent/competitor intelligence, agency buying history, exclusion/vendor-risk context, client-scoped data views, evidence-preserving source hashes, and natural-language procurement analytics. The repository has zero stars/forks despite substantial implementation depth.
- Commercial possibilities: Reuse the normalized ingestion/warehouse layer to add premium CaptureBrief modules for award intelligence, competitor/incumbent maps, vendor/exclusion screening, agency-spend analysis, and white-label per-client intelligence views for GovCon consultants. The strongest wedge is pairing live opportunity qualification with historical award/agency/vendor evidence rather than selling another search dashboard.
- Build-time savings: Very High — plausibly 2-4 months of ingestion, normalization, entity/award modeling, low-cost warehouse/API, scoping, and deployment plumbing.
- Evidence inspected: Repository metadata and latest commit; MIT LICENSE; recursive repository tree; `packages/core/src/adapters/usaspending.ts` with API filtering, pagination, response hashing, defensive source normalization and canonical award mapping; `packages/core/src/adapters/sam-bulk.ts` with ZIP/CSV handling and exclusion normalization; `packages/core/src/db/upsert.ts` with deterministic vendor/org/office/award IDs and atomic prepared-statement upserts; `.github/workflows/ci.yml`; `workers/api/` structure; `docs/architecture/OVERVIEW.md` describing the runtime/data/AI architecture and scoped access model.
- License / rights: MIT code license verified at the inspected revision. Upstream federal datasets/APIs remain subject to their own source terms; SAM.gov API/public-extract behavior should be revalidated before production use.
- Reuse classification: Directly reusable subject to MIT terms and upstream-source terms.
- Scores:
  - Technical value: 9/10
  - Commercial value: 9/10
  - Rarity: 9/10
  - Completeness: 9/10
  - Build-time saved: 9/10
  - Data advantage: 9/10
  - High-ticket potential: 9/10
- Next action: Prototype a CaptureBrief “Award Intelligence” sidecar by reusing the USAspending + SAM exclusion/canonical-upsert pieces first; expose incumbent/vendor/agency history and exclusion context inside an existing opportunity before considering the repo's optional SLM/AI layer.

### manynames3/pursuitdesk
- Repository: https://github.com/manynames3/pursuitdesk
- Commit / revision: bb6bd4530d0e0c8c53d40c8f5193b048e7d28288
- Date discovered: 2026-09-19
- What it contains: A functioning low-star GovCon consulting/capture platform blueprint: live SAM.gov/USAspending/GSA CALC+ ingestion, entity resolution, tenant/client context, readiness and opportunity scoring, P-win normalization, capture workflow state, evidence/source handling, async proposal drafting, pgvector-backed matching, DynamoDB proposal jobs, PostgreSQL migrations, Terraform/AWS serverless infrastructure, Cloudflare Pages frontend, CI, and tests covering API routes, proposal context/citations, P-win behavior, frontend formatting, and an end-to-end smoke path.
- Why it matters: It closely models the product layer CaptureBrief needs after raw ingestion: client readiness -> live opportunity -> evidence-backed fit/scoring -> capture decision -> proposal context. The tested P-win code explicitly caps weak structural-only estimates and labels low-confidence ranges, while proposal-context tests preserve SAM source records, SOW/PWS excerpts, attachments, and citations. That is useful clean-room guidance for avoiding inflated AI-confidence claims in a sellable GovCon workflow.
- Commercial possibilities: Clean-room implementation blueprint for a premium CaptureBrief consultant workspace sold to fractional capture/proposal consultants and small/midsize federal contractors: client onboarding, opportunity decision rooms, evidence-linked go/no-go, pricing/CALC+ context, capture workflow, and proposal-readiness handoff.
- Build-time savings: High as architecture/product research — plausibly 2-4 months of workflow, data-model, scoring-guardrail, async proposal-job, and deployment design if independently reimplemented.
- Evidence inspected: Repository metadata and latest commit; recursive tree and root contents; `src/` showing a ~203 KB API module plus entity resolver, GSA API/CALC+ ingestion and admin/infrastructure code; `tests/` directory with API, proposal-context, P-win and e2e tests; `tests/test_pwin_scoring.py`; `tests/test_proposal_context.py`; `docs/architecture.md` documenting Cloudflare + AWS serverless deployment, RDS/pgvector, SAM/USAspending/CALC+ ingestion, proposal jobs, model routing, source-backed live opportunities and production-auth constraints.
- License / rights: No repository license was detected at the inspected revision (`license: null` in repository metadata and no LICENSE file in root contents). Treat the source code, frontend, docs, and creative assets as copyrighted/inspect-only absent permission. Public government-source concepts/data have separate rights from the repository code.
- Reuse classification: Inspect / learn / clean-room implementation only.
- Scores:
  - Technical value: 9/10
  - Commercial value: 10/10
  - Rarity: 9/10
  - Completeness: 9/10
  - Build-time saved: 9/10
  - Data advantage: 8/10
  - High-ticket potential: 10/10
- Next action: Do not copy code. Translate only the product lessons into CaptureBrief requirements: evidence-backed decision rooms, conservative P-win ranges, SAM/SOW citation maps, async proposal jobs, consultant/client tenancy, and explicit production-auth boundaries; pair those independently implemented ideas with permissively licensed ingestion such as AwardLens/MindPetal.

### GovCon-One/govconone
- Repository: https://github.com/GovCon-One/govconone
- Commit / revision: f698f4eca3055715848315bb13ee94cf8cdea527
- Date discovered: 2026-09-19
- What it contains: A zero-star but unusually complete MIT-licensed federal capture SaaS substrate: live SAM.gov API and bulk-CSV ingestion, scheduled synchronization, D1/R2/Vectorize data and search, auth and organization tenancy, billing and BYOK support, saved solicitations, solicitation hydration with bounded attachment processing, structured package extraction for requirements/key dates/deliverables/evaluation criteria/reps-and-certs/submission instructions, deterministic and AI bid/no-bid analysis with evidence guardrails, compliance-first proposal starters and matrices, document embeddings, proposal editing/export infrastructure, migrations, deployment scripts, and tests.
- Why it matters: This is the strongest directly reusable product-layer accelerator found in this lane so far. Unlike the unlicensed PursuitDesk blueprint, GovCon ONE exposes a permissively licensed implementation of much of the CaptureBrief workflow after raw opportunity retrieval. Its solicitation hydration path treats source documents as untrusted data, validates extracted structures, falls back deterministically, persists source documents, and turns solicitation text into traceable requirements and proposal context instead of a generic summary.
- Commercial possibilities: Reuse or selectively graft the hydration, package-extraction, tenancy, BYOK, proposal-editor, billing, and compliance-matrix pieces into CaptureBrief; pair them with AwardLens for historical award/incumbent intelligence and a pricing layer for a premium pursuit decision room sold to small/midsize federal contractors and fractional GovCon consultants.
- Build-time savings: Very High — estimated 3-6 months of SaaS product, solicitation-ingestion/hydration, compliance extraction, auth/tenancy, billing, proposal workflow, and Cloudflare deployment work.
- Evidence inspected: Repository metadata and exact `prod` commit; root contents; actual MIT `LICENSE`; `package.json` with build/typecheck/test/deploy and D1 migration scripts; `src/domain.ts` deterministic BID/REVIEW/NO_BID scorer, evidence/citation rules, safe JSON normalization, and deadline/clearance risk handling; `tests/domain.test.ts`; `src/ai.ts` provider/BYOK support, embeddings, deterministic proposal fallback and evidence-backed proposal prompt; `src/hydrate.ts` Zod package schema, bounded document hydration, deterministic `shall/must` and evaluation extraction, reps-and-certs gates, injection-resistant extraction prompt, source-document storage and chunk embeddings; `src/sam.ts` search evidence; `tests/security.test.ts` search evidence; migration list through tenancy, hydration, org documents/matching, billing, saved solicitations, proposal editor, and security.
- License / rights: MIT license verified in the repository at the inspected revision. SAM.gov and any external model/API services retain their own terms. Example/development configuration values are not production credentials and were not collected.
- Reuse classification: Directly reusable subject to MIT terms and upstream service/data terms.
- Scores:
  - Technical value: 10/10
  - Commercial value: 10/10
  - Rarity: 10/10
  - Completeness: 9/10
  - Build-time saved: 10/10
  - Data advantage: 8/10
  - High-ticket potential: 10/10
- Next action: Run a narrow CaptureBrief spike using the solicitation hydration/package-extraction and proposal-editor path first, pair it with AwardLens historical evidence, and test the deterministic extraction/compliance matrix against a small current sample of public SAM solicitations before adopting its AI layer wholesale.

### mgifford/federal-contracting-skills
- Repository: https://github.com/mgifford/federal-contracting-skills
- Commit / revision: b40e99728bf35f05c42f9c5d7c6d47158630b246
- Date discovered: 2026-09-19
- What it contains: A dense MIT-licensed acquisition-domain toolkit covering USASpending, GSA CALC+ ceiling rates, BLS OEWS wages, GSA Per Diem, SAM.gov, eCFR, Federal Register, and Regulations.gov, plus orchestration workflows for SOW/PWS creation, FFP/LH-T&M/cost-reimbursement IGCEs, FAR Part 10 market research, Other Transaction cost analysis, and federal grant budgets. The detailed skills include calculation formulas, API paths, known data-quality pitfalls, scope rules, confidence/boundary guidance, and document-production workflows rather than only high-level prompts.
- Why it matters: It supplies much of the missing “Pursuit Economics” domain layer between CaptureBrief's opportunity qualification and an actual price/capture decision. The FFP workflow ages lagged BLS wages, builds fringe/overhead/G&A/profit layers, benchmarks against CALC+ percentiles, and prices travel; the market-research workflow handles agency-vs-government-wide scopes, top-award sample bias, vendor concentration limits, UEI duplication, negative obligations, and comparable-award pulls. Those details are expensive to rediscover correctly.
- Commercial possibilities: Add premium CaptureBrief modules for should-cost and pricing-rationale reports, rate validation, comparable-award and vendor-market analysis, capture-budget scenarios, and evidence-backed price-to-win context. The fastest wedge is an assisted per-pursuit pricing/economics report rather than another opportunity-search subscription.
- Build-time savings: High — estimated 2-4 months of federal pricing, market-research, API-recipe, and acquisition-domain research, even before productizing the workflows.
- Evidence inspected: Repository metadata and exact main commit/tree; actual MIT `LICENSE`; recursive tree containing the API/reference and orchestration skill library; `README.md` architecture/capability map and explicit AI-boundary positioning; `skills/igce-builder-ffp/SKILL.md` with SOW/PWS decomposition, BLS aging, layered wrap-rate formulas, low/mid/high scenarios, CALC+ JSON paths and percentile checks, travel math, and FAR references; `skills/market-research-builder/SKILL.md` with USASpending filter construction, NAICS/PSC validation, government-wide vs agency scoping, count endpoints, prior-award sampling caveats, vendor landscape/concentration logic, negative-obligation handling, and UEI deduplication cautions.
- License / rights: MIT license verified in the repository at the inspected revision. Federal APIs/data and third-party services retain their own terms and freshness constraints. Example burden factors and scenario defaults are workflow defaults, not universal contractor economics and should not be hard-coded as customer truth.
- Reuse classification: Directly reusable subject to MIT terms and upstream-source terms.
- Scores:
  - Technical value: 8/10
  - Commercial value: 10/10
  - Rarity: 9/10
  - Completeness: 9/10 for acquisition-domain workflow coverage
  - Build-time saved: 9/10
  - Data advantage: 9/10
  - High-ticket potential: 10/10
- Next action: Build a CaptureBrief “Pursuit Economics” report that combines AwardLens historical awards/incumbents with these pricing and market-research workflows; make burden assumptions customer-configurable, live-validate current CALC+/BLS response fields, and present benchmarks as evidence/ranges rather than a guaranteed price-to-win.