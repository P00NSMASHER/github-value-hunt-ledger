# DevOps & Infrastructure

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

### SyncVey
- Repository: https://github.com/MR-TABATA/SyncVey
- Commit / revision: `e37a73333f7489d663db0caa9a8622139b65ab44` on `main`
- Date discovered: 2026-09-19
- Lane: 07 — DevOps & Infrastructure
- What it contains: A functioning self-hosted AWS asset ledger and Terraform/live-cloud drift system built with Django, PostgreSQL, boto3 and Docker Compose. The inspected source includes cross-account AssumeRole scanning, normalized scanners for numerous AWS resource types, tfstate/live-state comparison, centralized changed/added/removed/autoscaling/unchanged drift classification, drift history, deleted-resource handling, application/middleware and EOL tracking, audit-oriented models, optional CLI/blast-radius functionality, and a LocalStack demo path. The repository includes substantive unit/integration/E2E tests and CI across Python 3.12/3.13 plus Playwright.
- Why it matters: Extremely high functioning-software-to-attention ratio: GitHub showed 0 stars and 0 forks when inspected, yet the repository contains a real deployable product with AWS scanning, persistent state, UI, drift semantics, migrations/models, tests, CI and a published-container deployment path. The drift implementation explicitly addresses false positives from tfstate/live scanner shape differences and distinguishes autoscaling churn from real drift. It also avoids treating failed service scans as mass resource deletion.
- Commercial possibilities: Strong foundation for a managed AWS drift / asset hygiene / EOL / compliance-evidence service aimed at MSPs, cloud consultancies, and smaller infrastructure teams that do not want to operate a broad enterprise CNAPP/IDP stack. A higher-value wedge is a managed multi-account “cloud change ledger” that turns drift, risky manual changes, stale middleware and resource ownership into recurring reports and remediation work rather than selling a generic inventory UI.
- Build-time savings: Estimated 4–8 months versus building the AWS scanner set, tfstate normalization, drift-state semantics, persistent history/UI, cross-account support, auth, tests and containerized demo/deployment scaffolding from scratch.
- Evidence inspected: Repository metadata; `README.md`; actual `LICENSE`; `asset_manager/drift.py`; `asset_manager/scanner.py`; `asset_manager/models/*`; `asset_manager/tests/*` including drift/autoscaling/blast-radius/core/E2E coverage; `.github/workflows/ci.yml`; `docker-compose.yml`; exact branch head commit. No exposed credentials or private/confidential data were retained or used.
- License / rights: Actual repository `LICENSE` is MIT (Copyright 2026 SyncVey). Code is permissively reusable subject to preserving the MIT copyright/license notice. Third-party dependencies and external data/services retain their own terms.
- Reuse classification: Directly reusable.
- Risks / constraints: AWS-centric; cloud API/resource normalization requires ongoing maintenance. The inspected Docker Compose command uses Django `runserver`, so a commercial deployment should add production WSGI/ASGI, hardened secrets/configuration, backups and operational controls rather than treating the demo compose file as production-ready.
- Scores:
  - Technical value: 9.3/10
  - Commercial value: 9.0/10
  - Rarity: 9.8/10
  - Completeness: 9.3/10
  - Build-time saved: 9.5/10
  - Data advantage: 7.5/10
  - High-ticket potential: 8.8/10
- Next action: Run the pinned commit against its LocalStack fixture path and a synthetic tfstate, execute the full CI suite, then map the minimum read-only IAM permissions needed for a managed multi-account deployment. If those pass, prototype a white-labeled recurring drift/EOL/compliance report rather than rebuilding the underlying scanner/ledger.

### ForgePortal
- Repository: https://github.com/forgeportal/forgeportal
- Commit / revision: `fb574e233099d1b4c7bb760e69fb6ac34e85707a` on `master`
- Date discovered: 2026-09-19
- Lane: 07 — DevOps & Infrastructure
- What it contains: A substantial internal developer platform monorepo built with Fastify, TypeScript, React, PostgreSQL and a worker process. The inspected tree contains an API, UI, worker, OIDC/auth/RBAC package, GitHub/GitLab-backed software catalog, search/docs packages, PostgreSQL job-queue primitives, a scaffolder/template engine, audit-log storage, scorecards, plugin SDK, migrations, Docker Compose and Helm deployment assets. The scaffolder source has persistent action-run state, routes, action registry/runner, input redaction and audit logging; its tests cover runner behavior, audit logging, template parsing/engine/orchestration and repository state. API integration tests cover catalog/auth/action/docs flows. CI provisions PostgreSQL and runs lint, build and test, and the default branch is protected by the `Lint · Build · Test` status check.
- Why it matters: GitHub showed only 3 stars and 0 forks when inspected despite a surprisingly complete developer-portal/platform-engineering codebase. This collapses a large amount of undifferentiated work involved in building a Backstage-style catalog, golden-path scaffolder, scorecard/fix workflow, plugin system, auth layer and deployable UI/API/worker stack.
- Commercial possibilities: Better as a high-ticket implementation accelerator than as another undifferentiated developer-portal SaaS. Potential products include a white-labeled “platform-in-a-box” for mid-market engineering organizations, verticalized golden paths for regulated teams, or a managed developer portal deployment/service that connects existing GitHub/GitLab/Kubernetes/ArgoCD/Grafana estates and sells implementation plus ongoing operations.
- Build-time savings: Estimated 6–12 months for a team that would otherwise need to implement catalog discovery, auth/RBAC, template execution, PR-generating actions, scorecards, plugins, audit logging, search, job processing and deployment scaffolding.
- Evidence inspected: Repository metadata; exact default-branch commit; actual `LICENSE`; recursive repository tree; `README.md`; `apps/api/src/*` and API integration-test tree; `packages/scaffolder/src/*`; scaffolder test suite; `.github/workflows/ci.yml`; Docker Compose deployment. No secrets, private data or accidental disclosures were collected or used.
- License / rights: Actual repository `LICENSE` is MIT (Copyright 2026 bendaamerahmed). Code is permissively reusable subject to the MIT notice. External plugins/dependencies/services retain separate terms.
- Reuse classification: Directly reusable.
- Risks / constraints: Developer-portal market is crowded, so commercial value depends on a sharp implementation/vertical wedge rather than cloning the generic product. Production use still requires a security review of SCM credentials, OIDC/RBAC boundaries, template/action execution and tenant isolation. The inspected README contains at least one minor feature-count inconsistency, so executable behavior should be treated as authoritative and validated end-to-end before promising coverage.
- Scores:
  - Technical value: 9.4/10
  - Commercial value: 8.8/10
  - Rarity: 9.5/10
  - Completeness: 9.4/10
  - Build-time saved: 9.8/10
  - Data advantage: 6.5/10
  - High-ticket potential: 9.2/10
- Next action: Boot the pinned Docker Compose stack, run the repository CI locally, and validate one full GitHub/GitLab catalog-import → golden-path template → generated PR → scorecard/fix-action path. If that path works, test a “developer portal deployed and branded in one week” service offer rather than spending time recreating the platform core.
