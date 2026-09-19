# REJECTED

Repositories, ideas, and combinations investigated and rejected or deprioritized.

## Entry format
### Name
- Repository / source:
- Date:
- Reason rejected:
- Evidence:
- Revisit trigger:

## Seeded rejected / deprioritized — 2026-09-19

### Tetrixx-SG/freight-audit-intelligence
- Repository / source: https://github.com/Tetrixx-SG/freight-audit-intelligence
- Date: 2026-09-19
- Reason rejected: Not a functioning software asset in the inspected root; the repository is primarily methodology, use-case, competitive-landscape, integration, ROI, and positioning documents. No license detected. Do not treat marketing claims such as accuracy figures as validated product capability.
- Evidence: Root contents contain README.md, methodology/, use-cases/, integrations/, competitive-landscape/, resources/, and roi-framework.md rather than an application/codebase.
- Revisit trigger: Use only as market/research context if a future run independently verifies specific claims from primary sources.

### rosshettel/permit_scraper
- Repository / source: https://github.com/rosshettel/permit_scraper
- Date: 2026-09-19
- Reason rejected: The name is misleading for PermitPlate purposes; it monitors recreation.gov permits and Washington ferry reservations, not municipal building/construction permits.
- Evidence: README explicitly describes recreation/enchantment permits and ferry reservations.
- Revisit trigger: Only if we need generic availability-monitoring patterns, not building-permit lead generation.

### pengyulong/InvoiceAuditAgent as direct-reuse engine
- Repository / source: https://github.com/pengyulong/InvoiceAuditAgent
- Date: 2026-09-19
- Reason rejected: Direct-reuse priority is low because its README marks core functionality, AI integration, tests, and deployment as incomplete, and no license was detected. It remains a design/reference candidate.
- Evidence: README development checklist plus root project structure.
- Revisit trigger: Backend inspection reveals substantial functioning audit logic not reflected in the README, or a license is added.

## Integrator rejection memory — 2026-09-19

### icdev-ai/icdev GovCon modules — quarantine
- Repository / source: https://github.com/icdev-ai/icdev
- Date: 2026-09-19
- Reason rejected: The repository root is Apache-2.0, but an inspected GovCon source file carried explicit U.S. Department of Defense CUI / SP-CTI restricted-distribution marking. A repository license does not nullify controlled-information handling concerns. The hunt must not preserve, propagate or build from potentially controlled material.
- Evidence: Hunter 05 stopped substantive inspection after the file-level marking was observed in the GovCon module.
- Revisit trigger: Only authoritative evidence from the rights-holder/government establishes that the markings are erroneous or the material is cleared for unrestricted public reuse.

### freightbill/freightbill as a software component
- Repository / source: https://github.com/freightbill/freightbill
- Date: 2026-09-19
- Reason rejected: Search results look code-heavy because the articles embed detailed freight-audit snippets, but the inspected repository is a static Eleventy documentation site, not a functioning audit product. No license was found.
- Evidence: Root/site structure and article content on rerating/accessorial/EDI methods; latest commit describes the static site.
- Revisit trigger: Revisit only if executable, tested audit software is added with clear reuse rights. Otherwise use independently verified concepts only as checklist material.

### sinchana-g7/RateDrift as an implemented freight-audit engine
- Repository / source: https://github.com/sinchana-g7/RateDrift
- Date: 2026-09-19
- Reason rejected: Compelling “rate creep” positioning, but the inspected repository contains frontend/README material while the described n8n/model/memory workflow is external and not committed. No license was found.
- Evidence: Root/package/application inspection plus README architecture description.
- Revisit trigger: Backend workflow code, tests, durable historical comparison logic and a clear license are committed.

### ihoward40/SintraPrime-Unified deadline engine
- Repository / source: https://github.com/ihoward40/SintraPrime-Unified
- Date: 2026-09-19
- Reason rejected: Although MIT-licensed and surrounded by substantial application code, the legal deadline subsystem uses hard-coded generic federal-rule offsets, a simplistic holiday table and deadline arithmetic that is not sufficiently authoritative/jurisdiction-aware for consequential legal use.
- Evidence: Hunter 09 inspected `docket/deadline_tracker.py`, related monitoring structures and tests.
- Revisit trigger: A future revision replaces deadline math with authoritative, versioned rules including court/local-rule applicability and rigorous calendaring tests.

### CodeCatalyst-nx/Code_Catalyst as a routing product foundation
- Repository / source: https://github.com/CodeCatalyst-nx/Code_Catalyst
- Date: 2026-09-19
- Reason rejected: The functioning OR-Tools CVRP script is useful as a compact example but has no detected license, no test suite and little differentiated value beyond directly using permissively licensed OR-Tools with a domain-specific model.
- Evidence: Hunter 34 inspected `route_optimizer.py` and searched for tests without finding pytest/unittest coverage.
- Revisit trigger: A license, meaningful real-world constraint set, benchmark advantage or tested dispatch workflow is added.

### qa-audit-portal current revision
- Repository / source: https://github.com/mdjahidhasansst-pixel/qa-audit-portal
- Date: 2026-09-19
- Reason rejected: MIT rights are clean, but the current repository is only early Next.js/Prisma setup; README merge-conflict remnants and a “Sprint 1 environment setup” commit do not support claims of a functioning contact-center QA product.
- Evidence: Hunter 37 inspected latest commit, README and project structure.
- Revisit trigger: Real QA scorecards, sampling/calibration, adjudication/appeals or analytics are implemented and tested.

### TNRIS/weather-alerts-parser for new product work
- Repository / source: https://github.com/TNRIS/weather-alerts-parser
- Date: 2026-09-19
- Reason rejected: Rights are friendly, but the implementation is a Python-2-era legacy weather-alert parser whose API/format assumptions are obsolete relative to current NWS/CAP/GeoJSON tooling.
- Evidence: Hunter 23 inspected metadata/history and staleness.
- Revisit trigger: Only for legacy format archaeology; do not spend active search time on it for a new system.

### dsalgador/master-thesis as a near-term inventory-routing product foundation
- Repository / source: https://github.com/dsalgador/master-thesis
- Date: 2026-09-19
- Reason rejected: The joint inventory-routing formulation is academically interesting, but the implementation is an older TensorFlow/Gym research stack under GPL-3.0 and does not provide near-production build compression compared with modern forecasting plus deterministic optimization baselines.
- Evidence: Hunter 43 inspected the exact revision, thesis/experiment structure, environment dependency and GPL status.
- Revisit trigger: A specific buyer supplies an inventory-routing dataset/problem where joint replenishment-and-routing materially outperforms simpler modern deterministic baselines and GPL use is acceptable or the method is independently reimplemented.

### paulkastel/JobShopPRO as a product/code foundation
- Repository / source: https://github.com/paulkastel/JobShopPRO
- Date: 2026-09-19
- Reason rejected: Useful legacy job-shop workflow reference, but no license was detected, the desktop/Tkinter implementation is old, and its FIFO/LIFO/SPT/LPT scheduling heuristics are not differentiated enough to justify active product search when modern permissive optimization stacks exist.
- Evidence: Hunter 45 inspected the terminal revision, launch path and documented orders/machines/Gantt/heuristic workflows.
- Revisit trigger: Revisit only for clean-room UX/domain discovery after a real small-manufacturer scheduling buyer is identified; do not reuse source absent permission.
