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

### Jinotaer/Multi-Tenant-Laundry-Shop-Management-System as direct code foundation
- Repository / source: https://github.com/Jinotaer/Multi-Tenant-Laundry-Shop-Management-System
- Date: 2026-09-19
- Reason rejected: Despite a broad multi-tenant laundry SaaS implementation, the README explicitly labels the application proprietary and “All rights reserved.” The fact that Laravel is MIT does not grant reuse rights to the application source. Its likely ACV is also lower than the current top opportunities.
- Evidence: Hunter 01 inspected the repository metadata, exact revision and README covering tenant isolation, roles, orders, payments, invoices, subscriptions, analytics and the explicit proprietary-software notice.
- Revisit trigger: Only if the rights-holder grants a commercial/open-source license or a materially higher-value B2B linen/route-service wedge is validated independently; otherwise use only non-copyrightable clean-room workflow ideas.

### taskfleetai/fieldfleet as a competing hosted SaaS foundation
- Repository / source: https://github.com/taskfleetai/fieldfleet
- Date: 2026-09-19
- Reason rejected: Technically exceptional construction/restoration field-operations breadth, but the project is under Elastic License 2.0 and explicitly prohibits offering FieldFleet itself to third parties as a hosted or managed service without a commercial agreement. It is therefore unsuitable as the code base for a competing proprietary SaaS under the current hunt assumptions.
- Evidence: Hunter 02 inspected the exact revision and README feature/deployment/license matrix, including the hosted/managed-service restriction.
- Revisit trigger: A separate commercial license is obtained, or only independently reimplemented workflow requirements are needed for a lawful clean-room product.

### Em1lyK/ctrebate_recon — safety quarantine
- Repository / source: https://github.com/Em1lyK/ctrebate_recon
- Date: 2026-09-19
- Reason rejected: During source inspection a credential-like/authentication query value was observed embedded in a source URL. Inspection was stopped. The value was not retained, reproduced, tested or used. No repository license was detected independently of the safety issue.
- Evidence: Hunter 47 logged the quarantine without preserving the sensitive-looking value.
- Revisit trigger: Only if the owner publishes a sanitized revision and explicit reuse rights are established; review must restart from the clean revision rather than historical content.

### VeeamHub/veeam-vscan-security as a reusable implementation
- Repository / source: https://github.com/VeeamHub/veeam-vscan-security
- Date: 2026-09-19
- Reason rejected: The public repository is useful documentation/product evidence for scanning mounted backup restore points, but source-level inspection found docs/examples/assets rather than the application source/test suite implied by the product description. MIT applies only to what is actually published; it does not make unpublished product source reusable.
- Evidence: Hunter 14 inspected exact revision `ded6d26d26065a76cbd22234af7c6ff0536bf63b`, root/tree contents and release material describing Veeam Data Integration API plus Trivy/Grype/Jadi behavior.
- Revisit trigger: A real source adapter/test suite is published under permissive terms, or a separate permissive Veeam restore-mount implementation is found.

### rabbittrix/BSS-OSS-Rust-Ecosystem as ordinary Apache-2.0 product substrate
- Repository / source: https://github.com/rabbittrix/BSS-OSS-Rust-Ecosystem
- Date: 2026-09-19
- Reason rejected: Per-crate metadata can look permissive, but the root licensing adds commercial authorization/donation requirements for TMF crates and a proprietary commercial license for other components. It should not be treated as normal Apache-2.0 reusable code for a competing commercial product.
- Evidence: Hunter 35 inspected exact revision `7ad417c2590d5a843302f7dbfa163e5e774ed63d`, the root license and concrete TMF638/641/640/702/639 implementation surfaces.
- Revisit trigger: Explicit commercial authorization/license is obtained. Until then, prefer Apache-2.0 `netweave`/Oktopus or independently reimplement requirements.

### kundanvarma/genalpha-bss as current competing hosted-SaaS code base
- Repository / source: https://github.com/kundanvarma/genalpha-bss
- Date: 2026-09-19
- Reason rejected: The codebase is broad and active, but BSL 1.1 Additional Use terms explicitly exclude offering a paid hosted/embedded competing product. Individual versions change to Apache-2.0 after their stated two-year change period, so current code is not a rights-clean immediate hosted foundation.
- Evidence: Hunter 35 inspected exact revision `8fd5286dd676753bb37324eb395be0df14980356`, root licensing and live workflow/capability docs that also distinguish mocked/thin activation from implemented state logic.
- Revisit trigger: Revisit a specific old revision after its Apache change date or obtain commercial permission; otherwise use only lawful clean-room workflow comparisons.

### ediflow-lib/core bundled X12 definitions as automatically MIT-cleared standards data
- Repository / source: https://github.com/ediflow-lib/core
- Date: 2026-09-19
- Reason rejected: The repository's parser/infrastructure software is MIT, but the bundled X12 004010 package contains standards-derived transaction structures, code lists and syntax rules. This run did not establish independent provenance or redistribution authorization for those standards-derived data assets. A repository-level MIT license is not enough evidence to assume third-party standards content is cleared for commercial redistribution.
- Evidence: Hunter 03 inspected exact revision `9a631a4104711bf5ac81c96d4b725c8698b4d799`, the root MIT license and the bundled X12 package describing broad 004010 transaction coverage including 204/210/214/990/810/820/824/997.
- Revisit trigger: An explicit provenance/license statement establishes lawful redistribution of the generated/bundled X12 definitions. Until then, parser infrastructure may be evaluated separately, but the standards-definition corpus must remain rights-unresolved and outside the commercial dependency chain.

## Run 11 additions / demotions

### Fajendagba/Construction-Change-Order-Engine — demoted from MASTER
- Repository / source: https://github.com/Fajendagba/Construction-Change-Order-Engine
- Date: 2026-09-19
- Reason rejected/deprioritized: No license was detected. Its change-order state/budget concepts remain useful clean-room requirements, but rights-clean OpenTakeoff + BIMChange-Agent now provide materially stronger implemented evidence layers for ScopeSignal.
- Evidence: Existing catalog inspection established concrete workflow concepts but no reuse grant; current combination no longer depends on this code.
- Revisit trigger: Explicit permissive/commercial reuse rights plus implementation/tests that materially outperform the current rights-clean stack.

### D-ivy/renewables_indexes — demoted from MASTER
- Repository / source: https://github.com/D-ivy/renewables_indexes
- Date: 2026-09-19
- Reason rejected/deprioritized: No license detected and visible build path is not fully reproducible. The committed screening artifacts/methodology remain useful clean-room research, but they no longer meet the elite positive-training-set standard.
- Evidence: Prior inspection found national resource×price×revenue layers and volatility/negative-price features, but rights and reproducibility remain unresolved.
- Revisit trigger: Clear reuse/data rights and a reproducible build or a licensed successor with equivalent national screening depth.

### Andalusia-Data-Science-Team/QA-for-call-center — safety quarantine
- Repository / source: https://github.com/Andalusia-Data-Science-Team/QA-for-call-center @ `fd4c22995809ff78568dad18856fede665fa4ff1`
- Date: 2026-09-19
- Reason rejected: The public README advertises a credential-bearing database configuration artifact and no license was established. The project also appears tied to a clinical contact-center environment. The potentially sensitive configuration artifact was deliberately not opened, copied, preserved or tested.
- Evidence: High-level README/project metadata only; inspection stopped before credential-bearing content.
- Revisit trigger: A sanitized revision is published with explicit reuse rights and clearly synthetic/public test material.

### Nemesysco/QA7-SDK as a reusable QA engine
- Repository / source: https://github.com/Nemesysco/QA7-SDK @ `649017cf59b7e60571df311a1c668dcc3d0827bc`
- Date: 2026-09-19
- Reason rejected: No reuse license established; old opaque vendor-SDK style repository with insufficient transparent source/test evidence compared with better MIT contact-center QA substrates.
- Evidence: Repository metadata/README and age/runtime requirements; no binary reverse engineering was performed.
- Revisit trigger: Explicit open-source/commercial reuse license plus auditable source/tests.

### robawtic/heijunka as the workforce-assurance core
- Repository / source: https://github.com/robawtic/heijunka @ `14559d42a08f011467261383cc533fb447529c7b`
- Date: 2026-09-19
- Reason rejected/deprioritized: MIT and operationally interesting, but the inspected fallback objective can minimize positive assignment weights and therefore prefer zero assignments unless coverage is otherwise forced. RosterSpec is a stronger current assurance/repair foundation because it treats verification, hard locks, coverage priority and repair validity explicitly.
- Evidence: Hunter source inspection of fallback objective semantics and current tests.
- Revisit trigger: Objective/coverage semantics are corrected and regression tests prove required staffing cannot collapse to a zero-assignment optimum.

### shafeehhecker/HaulSync as a freight invoice-reconciliation engine
- Repository / source: https://github.com/shafeehhecker/HaulSync @ `0d6fd34b21c1e09309ea155cc29ca06c2242e307`
- Date: 2026-09-19
- Reason rejected/deprioritized: MIT workflow shell is useful for RFQ→award→shipment→POD→invoice lineage, but inspected invoice routes are CRUD and do not support the stronger README claim of billed-vs-quote/contract reconciliation. Open TMS/Kareya/Qatoto already provide the stronger audit core.
- Evidence: Prisma schema plus RFQ, shipment and invoice route inspection.
- Revisit trigger: Real invoice comparison/rerating logic and tests are implemented. Until then keep only as optional workflow-schema donor.

### clickpost-tech/clickpostERP as a freight-audit engine
- Repository / source: https://github.com/clickpost-tech/clickpostERP @ `7808a6dbc25a4698acff7acd14c1a8704777f0c7`
- Date: 2026-09-19
- Reason rejected/deprioritized: MIT ERPNext integration has meaningful carrier recommendation, shipment/AWB, tracking webhook and sales-invoice linkage, but source inspection did not find the advertised freight invoice reconciliation path. It is an optional connector, not a recovery core.
- Evidence: carrier/shipment APIs, custom shipment script, webhook and invoice linkage inspected; most doctype tests are scaffolding.
- Revisit trigger: Actual billed-vs-expected reconciliation is committed and tested, or a pilot specifically needs ERPNext/ClickPost intake.

### ifte110/Ocean-Freight-Rates direct reuse
- Repository / source: https://github.com/ifte110/Ocean-Freight-Rates @ `cd0b2a3cfa818f083992654e1d9611833c9fc7d3`
- Date: 2026-09-19
- Reason rejected: No LICENSE found and the workbook/database/notebook appear to originate from a third-party data-science exercise. Public visibility does not establish reuse rights. Binary data were not inspected/extracted.
- Evidence: Root metadata/README only; domain concepts include port/equipment normalization, effective windows and surcharge logic.
- Revisit trigger: Explicit rights are established. Otherwise recreate any useful benchmark cases independently with synthetic ports/rates.

### ShakthiW/canton-research freight engine
- Repository / source: https://github.com/ShakthiW/canton-research @ `4f74ba2b8d8808313e19c4cf0e0e6df645796fc8`
- Date: 2026-09-19
- Reason rejected: No license detected; deterministic-looking freight calculations include fallback estimated cube/default divisors and broad optimistic/conservative multipliers that are inappropriate for evidence-grade billed-vs-contracted recovery. Kareya/Qatoto materially surpass it.
- Evidence: Inspected chargeable-weight/minimum/air-sea-courier logic and fallback behavior.
- Revisit trigger: Clear rights plus rigorous source-backed freight tests and removal of guessed values from recovery decisions.

### mohammedrasulkhan09-arch/route-wise-rate-card-manager
- Repository / source: https://github.com/mohammedrasulkhan09-arch/route-wise-rate-card-manager @ `fa71892ba44a5c53212b7dec64796c6fac436716`
- Date: 2026-09-19
- Reason rejected: Four-file browser CRUD/quotation demo with no LICENSE, no backend/versioning/provenance/tests and only simple route/weight/category/per-kg semantics. Does not improve Qatoto/Kareya.
- Evidence: Full small project structure inspected.
- Revisit trigger: Substantive backend, provenance/versioning, tests and clear rights are added.
