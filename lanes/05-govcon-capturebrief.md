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