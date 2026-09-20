# GitHub Value Hunt Ledger

Private persistent memory for the GitHub Value Hunt.

## Operating model
- Fourteen active hunter workstreams search across the **47 thematic catalogs** under `hunters/`; catalog numbers are domain indexes, not necessarily one-to-one automation identities.
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
