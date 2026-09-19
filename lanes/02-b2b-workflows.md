# B2B Workflows

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
### microsoft/RulesEngine
- Repository: https://github.com/microsoft/RulesEngine
- Commit / revision: 5650f93f843865610240e0498b26b68b477a3920
- Date discovered: 2026-09-19
- What it contains: Production-oriented .NET rules engine that stores business rules/workflows outside core application logic, compiles/evaluates expressions, caches rules, supports actions, and returns structured rule-result trees.
- Why it matters: Deterministic, explainable rules are critical for audit/recovery, compliance, eligibility, pricing, approvals, and exception workflows where a pure LLM approach is hard to defend.
- Commercial possibilities: Reusable decision layer for freight audit, AP recovery, permit lead qualification, GovCon eligibility/qualification, and any B2B workflow requiring customer-editable policies.
- Build-time savings: High for rule storage, compilation, execution, result trees, actions, caching, and extensibility.
- Evidence inspected: README.md; src/RulesEngine/RulesEngine.cs showing workflow loading, rule cache/compiler, expression parsing, action factory, and async rule execution.
- License / rights: MIT.
- Reuse classification: Directly reusable subject to MIT terms.
- Scores:
  - Technical value: High
  - Commercial value: High as shared infrastructure
  - Rarity: Medium
  - Completeness: Very High
  - Build-time saved: High
  - Data advantage: Low by itself
  - High-ticket potential: High indirectly
- Next action: Compare .NET integration cost against language-native alternatives, but preserve the architecture pattern of explicit deterministic rules plus explainable results.
