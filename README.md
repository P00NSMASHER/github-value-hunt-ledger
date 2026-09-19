# GitHub Value Hunt Ledger

Private persistent memory for the GitHub Value Hunt.

## Operating model
- Lanes 01-14 are independent discovery streams.
- Every hunter reads its lane, MASTER.md, REJECTED.md, and COMBINATIONS.md before searching.
- New findings must be evidence-backed and deduplicated.
- Task 15 integrates findings across lanes and maintains MASTER.md, COMBINATIONS.md, and REJECTED.md.
- Public repositories may be analyzed regardless of popularity or license, but reuse must respect license/copyright.
- Do not collect, preserve, reproduce, or exploit exposed credentials, personal data, authentication material, or accidentally published confidential information. Quarantine and skip those items.

## Finding schema
Each retained finding should include:
- Repository + canonical URL
- Exact commit/revision inspected
- Date discovered
- Lane
- What it contains
- Why it matters
- Commercial possibilities
- Build-time savings
- Evidence inspected
- License / rights
- Reuse classification
- Scores: technical value, commercial value, rarity, completeness, build-time saved, data advantage, high-ticket potential
- Next action

## Reuse classification
- Directly reusable
- Reusable with license conditions
- Inspect / learn / clean-room implementation only


# Hunter Catalogs

Each hourly hunter writes only to its own file under `hunters/` to avoid concurrent overwrite conflicts. Every meaningful repository or public technical/data artifact inspected should be recorded, including rejected/deprioritized candidates when useful, with evidence and rights status. The cross-hunt integrator maintains MASTER.md, COMBINATIONS.md, and REJECTED.md.

"Rare/secret" means obscure, undernoticed, non-obvious, little-known, or unusually hard-to-recreate public material. It does **not** include credentials, personal/private data, authentication material, accidentally exposed confidential information, or leaked trade secrets.

Public GitHub availability does not mean public domain. Reuse must follow the applicable license and copyright status.

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
