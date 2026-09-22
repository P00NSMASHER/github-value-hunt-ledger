# Wildcard

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

### RichieGarafola/invoice-reconciliation-tool
- Repository: https://github.com/RichieGarafola/invoice-reconciliation-tool
- Commit / revision: `ed946c293697575a7ed1bf9bc27488bea2052ea0`
- Date discovered: 2026-09-19
- What it contains: Zero-star MIT Python/Streamlit federal-contractor accounts-receivable reconciliation tool. The core reconciler aggregates multiple payments per invoice, joins invoice and payment ledgers, computes remaining balance, classifies PAID/PARTIAL/UNPAID/OVERPAID with a $0.01 tolerance, computes days outstanding and aging buckets, and feeds reporting/dashboard/CSV-export layers. The inspected tree also contains sample data, architecture/data-dictionary docs, GitHub Actions CI, and substantial reconciler/reporter tests.
- Why it matters: It is an unusually complete zero-attention foundation for a federal-contractor cash-recovery product. The existing application performs the ledger reconciliation and aging work but does not calculate Prompt Payment Act interest. Separately, official FAR 52.232-25 confirms that qualifying late federal payments can carry automatically due interest and that an additional penalty can involve a short written-demand window when specified conditions are met. That creates a higher-value extension around missed interest and expiring recovery opportunities rather than merely another AR dashboard.
- Commercial possibilities: Build a `Federal Prompt-Pay Recovery Audit` for GovCon CFOs, controllers, contracts administrators, and portfolio operations teams. Ingest invoice, payment, acceptance, and contract-clause data; identify qualifying late payments; calculate candidate interest/additional-penalty opportunities from official rate/rule sources; and generate an evidence-linked review packet. A fixed-fee historical scan plus shared savings on client-verified recovery, or recurring deadline monitoring, is plausible. Do not automatically assert entitlement: contract/rule applicability and any demand should remain human reviewed.
- Build-time savings: Estimated 2-4 weeks for reconciliation, aging, reporting/UI, CSV intake/export, and tested core plumbing. New work is still required for proper-invoice and acceptance-date rules, Treasury interest-rate history, contract-clause applicability, dispute/exclusion handling, duplicate-payment hardening, and recovery workflow.
- Evidence inspected: Repository metadata and license; commit/tree at the revision above; `src/reconciler.py`; `tests/test_reconciler.py`; README/architecture claims; GitHub Actions CI. Official Acquisition.gov FAR 52.232-25 was checked independently to validate the extension opportunity rather than assuming the repository implemented it.
- License / rights: MIT. Direct code reuse is permitted subject to the license notice/conditions. Bundled examples appear to be sample/synthetic data; no private data or credentials were used.
- Reuse classification: Directly reusable
- Scores:
  - Technical value: 8/10
  - Commercial value: 9/10
  - Rarity: 9/10
  - Completeness: 8/10
  - Build-time saved: 7/10
  - Data advantage: 3/10
  - High-ticket potential: 9/10
- Next action: Build a deterministic validation fixture spanning proper invoice receipt, acceptance date, payment date, excluded/disputed amounts, official interest-rate periods, and the additional-penalty timing rule; validate every output against official FAR/5 CFR source examples before any customer use.

### nathansutton/hospital-price-transparency
- Repository: https://github.com/nathansutton/hospital-price-transparency
- Commit / revision: `2e62e685c22c0aa56b804128d62d7f6a444a1b96`
- Date discovered: 2026-09-19
- What it contains: A low-attention, long-running hospital-price collection and normalization system covering a claimed 5,000+ hospitals across all 50 U.S. states. The inspected implementation includes substantial CMS JSON, CSV, XLSX, and ZIP scrapers; a scraper registry; retry/large-file handling; CPT/HCPCS normalization; JSONL outputs; URL/status tracking; tests; scheduled validation; and a self-healing failure workflow. Its Git history is intentionally used as a slowly changing historical archive of posted hospital prices.
- Why it matters: Hospital machine-readable-file URLs and formats change constantly, while prior posted prices can disappear. Recreating years of snapshots, thousands of source URLs, format-specific parsers, normalization rules, and maintenance machinery is expensive and in some cases impossible retroactively. The historical change layer is therefore more valuable than a one-time price lookup.
- Commercial possibilities: Build a `Hospital Price Change Radar` for health-system strategy teams, revenue-cycle/healthcare consulting firms, patient-navigation or bill-review vendors, and market-research users. Monitor competitor cash/gross price movements by CPT/HCPCS, flag missing/changed files, reconstruct longitudinal changes, and produce evidence-linked market briefs or alerts. Do not market this inspected version as payer-negotiated-rate intelligence: the inspected CMS JSON parser primarily extracts gross and discounted-cash fields rather than payer-specific negotiated rates.
- Build-time savings: Estimated 3-6 months of source discovery, format handling, streaming/retry infrastructure, normalization, test coverage, URL maintenance, and operational failure handling. Historical snapshots already captured cannot be fully recreated after source files disappear or change.
- Evidence inspected: Repository metadata; exact commit; root license; README architecture/coverage description; `src/scrapers/` directory; `tests/` directory; `tests/test_scrapers.py`; `src/scrapers/cms_json_scraper.py`; self-healing workflow changes in the inspected commit.
- License / rights: Root `LICENSE` is Apache-2.0 even though the README badge/text says MIT; treat the code as Apache-2.0 and preserve required notices. Hospital machine-readable files are publicly posted regulatory data, but source/provenance should be preserved and any third-party vocabulary/data terms (including external normalization vocabularies) should be checked separately before redistribution.
- Reuse classification: Directly reusable, subject to Apache-2.0 conditions and separate source-data terms where applicable
- Scores:
  - Technical value: 9/10
  - Commercial value: 8/10
  - Rarity: 9/10
  - Completeness: 8/10
  - Build-time saved: 9/10
  - Data advantage: 10/10
  - High-ticket potential: 8/10
- Next action: Run a controlled sample across 10 hospitals and approximately 20 high-volume CPT/HCPCS codes to quantify how much historical price depth is actually present, how consistently changes can be reconstructed, and which failure modes remain; use that evidence to define a paid competitive-intelligence pilot.

### sputhenofficial/claimjumper
- Repository: https://github.com/sputhenofficial/claimjumper
- Commit / revision: `c45b0080ab68b8e04f0e5d61302d31f1714519ec`
- Date discovered: 2026-09-19
- What it contains: One-star MIT Next.js/TypeScript vertical slice for medical-denial triage. It ingests a PNG EOB/remittance into a strict structured schema, routes denied service lines into appeal/corrected-claim/patient-bill/write-off/human-review lanes, applies code-enforced safety invariants after model triage, deterministically computes deadline/urgency/priority ordering, produces cited appeal or corrected-claim work artifacts, requires human approval before export, and never performs payer-facing submission. The inspected tree includes substantial pipeline/UI/API code plus broad Vitest coverage for ingest, invariants, prioritization, drafting, route composition, queue behavior, and export filtering.
- Why it matters: This is unusually complete low-attention workflow infrastructure for converting raw denials into a prioritized, reviewable revenue-recovery queue rather than another static RCM dashboard. The strongest reusable design is the separation of probabilistic extraction/triage from deterministic safety controls: contractual-obligation adjustments are prevented from becoming patient-bill recommendations, risky CARC 197 write-offs and low-confidence decisions are forced to human review, and draft failures do not drop the underlying work item. That architecture maps well to a high-value denial-recovery product where errors can create financial/compliance harm.
- Commercial possibilities: Build a `Denial Recovery Work Queue` for smaller RCM vendors, specialty groups, multi-site practices, or outsourced billing teams: import remittance/EOB data, rank unresolved denial dollars by evidence and urgency, assemble cited appeal/correction packets, and track human-approved outcomes. A paid historical-denial scan or per-location SaaS pilot is more defensible initially than autonomous claims action. Contingency/shared-savings pricing could be explored only against client-verified realized recovery, not the model's `recovery_probability` score.
- Build-time savings: Estimated 4-8 weeks for the denial schema, human-review UX, pipeline seams, cited drafting/export flow, deterministic safety layer, prioritization framework, and regression-test substrate. Production work remains substantial: ERA/835 or billing-system ingestion, persistence/multitenancy, authentication/RBAC, audit logging, HIPAA/security controls, payer-specific rules, outcome calibration, and enterprise integrations.
- Evidence inspected: Repository metadata; exact commit/tree; root MIT `LICENSE`; README limitations and architecture; `package.json`; `lib/pipeline/invariants.ts`; `lib/pipeline/prioritize.ts`; `tests/invariants.test.ts`; `tests/prioritize.test.ts`; `tests/triage-draft-route.test.ts`; test-directory inventory. The bundled sample is explicitly described as demo/synthetic data; no real patient data or credentials were inspected.
- License / rights: MIT. Direct code reuse is permitted subject to preservation of the copyright/license notice. Healthcare code reuse does not validate medical-billing, payer, HIPAA, or deadline rules; those must be independently verified before customer use.
- Reuse classification: Directly reusable
- Scores:
  - Technical value: 8/10
  - Commercial value: 9/10
  - Rarity: 8/10
  - Completeness: 7/10
  - Build-time saved: 8/10
  - Data advantage: 3/10
  - High-ticket potential: 9/10
- Next action: Replace the demo PNG-only intake with a synthetic ERA/835 fixture and an independently verified payer/rule table, then benchmark routing precision, evidence completeness, deadline correctness, and recovered-dollar prioritization against labeled historical denial cases. Treat the current hard-coded 5-day receipt presumption + 120-day deadline and model-generated recovery probabilities as uncalibrated until validated for the specific payer/workflow.


### aws-samples/sample-energy-utility-rate-engine — utility tariff compiler / batch rerating substrate
- Repository: https://github.com/aws-samples/sample-energy-utility-rate-engine
- Commit / revision: e2f987be3863b0a5026940b7217cbc4ddffe6129
- Date discovered: 2026-09-22
- What actually works: Four-star MIT-0 full-stack utility rate engine. Business-readable Rate Definition Language (RDL) is parsed with Lark into a typed AST, transpiled into Rust, compiled to ARM64 Lambda, and used from both real-time and high-volume batch paths. Rate logic is separated from date-effective factor values. The shipped rule/function surface covers customer charges, tiered/N-tier energy, demand caps and ratchets, power-factor adjustments, critical-peak days, TOU periods including overnight windows, seasons, riders, net-metering credits, taxes/fees, minimum bills and multiple rounding modes.
- Evidence of implementation: `cdk/lambda/dsl-generator/*`; generated Rust template; frontend scenario/calculation editors; Step Functions batch path; `tests/test_dsl_generator.py`; `tests/rust_function_tests.rs`; and `tests/test_calculation_e2e.py`. The E2E test generates the actual Rust from shipped RDL/custom-function data, compiles it with Cargo, injects a controlled factor table, and checks line-item and total bills across residential/commercial tiers, tax exemption, NEM, demand caps, minimum bills, ratchets, power factor, critical peak and riders.
- Rare / undernoticed value: This is much closer to a utility billing compiler than a tariff calculator. The same versioned business rules can be applied to one disputed bill or a multi-year, multi-site population, which maps unusually well to retrospective recovery auditing.
- Useful capability/workflow: reviewed tariff logic + effective-dated factors -> compiled deterministic calculator -> itemized expected bill -> large-scale historical rerating.
- Likely buyer: commercial/industrial multi-site energy users, REIT/property managers, retail/franchise chains, manufacturers, cold storage, universities/hospitals, wastewater/municipal energy users, energy consultants.
- Pain solved: Recalculating complex historical utility bills across changing tariffs, demand rules and riders is expensive and often spreadsheet/vendor dependent.
- Fastest monetization path: Use the engine behind a managed Utility Bill Recovery diagnostic, not as a standalone rate-engine sale.
- Paid-pilot concept: freeze official tariff/rider versions for 5-25 meters and rerate 12-24 months of interval/bill data; human-review discrepancies; pursue only customer-authorized utility credits/refunds.
- Estimated engineering time saved: roughly 4-8 months across rate-language/parser/compiler, scenario management, batch rerating, calculation UI and regression tests.
- License / reuse status: MIT-0 for repository code. Utility tariff documents/data and customer meter/bill data remain separately governed.
- Important dependencies/risks: **Do not use the shipped calculator unchanged for money authority.** Its numeric model is `f64`, and the seeded `GET_FACTOR` returns `0.0` when no applicable factor is found. For recovery this must become a typed UNKNOWN/REVIEW state, never a zero-valued factor. Replace/guard monetary arithmetic with exact decimal/integer-minor-unit semantics and bind every deployed scenario to immutable reviewed authority/source hashes.
- Connections: Pair with WE3 tariff discovery/source metadata, LBNL Elecprice as an independent comparator, existing CAP-006 settlement attribution and proof-obligation controls.
- Opportunity score: **9.6/10**.

### we3lab/industrial-electricity-tariffs — monthly US industrial/commercial tariff discovery corpus
- Repository: https://github.com/we3lab/industrial-electricity-tariffs
- Commit / revision: ffab0314814d4796c6655c91f53f90b525acdf94
- Current release inspected: 2026.09.01, GitHub release asset `industrial-electricity-tariffs.zip`, published digest `sha256:71ae5b5666099b13f53e08ded151744095d8f5fc5798c1597ed102ebca64fa7b`.
- Date discovered: 2026-09-22
- What it contains: Two-star MIT research/data pipeline that publishes a monthly normalized dataset of U.S. industrial/commercial electricity tariffs derived from USURDB plus manually collected research tariffs. The format represents customer, energy and demand charges; monthly/daily demand assessment; multiple concurrent demand periods; tiers; month/hour/weekday applicability; units; service type; ZIP/geography; and source links. Each release also includes metadata and an explicit reject list with reject reasons. DOI/Zenodo provenance is provided.
- Evidence of implementation: GitHub Actions monthly pipeline; `scripts/download.py`, `filter.py`, `convert.py`, `merge.py`, `validate.py`; large conversion test suite (~100 KB) plus validation/filter/merge/download tests; current release asset.
- Rare / undernoticed value: This is a ready-made national **tariff discovery/index layer** for the buyer segment Utility Recovery would target. The source URL attached to each tariff is especially valuable because it can drive acquisition of controlling first-party documents rather than treating the normalized dataset as entitlement.
- Useful capability/data/workflow: utility/rate candidate search -> normalized complex tariff structure -> original source link -> customer/official document authority review.
- Likely buyer: same Utility Recovery ICP; internal tariff research/QA.
- Pain solved: discovering and normalizing thousands of complex commercial/industrial tariff schedules before a historical rerating exercise.
- Fastest monetization path: use internally to accelerate meter/rate onboarding and identify source documents; do not resell its normalized row as controlling authority.
- Paid-pilot concept: map each pilot meter to candidate tariff/source, freeze the actual controlling utility document/account class, then rerate in the independent engine.
- Estimated engineering time saved: 2-4 months of tariff discovery/normalization and data-maintenance work, plus an ongoing monthly refresh pipeline.
- License / reuse status: MIT repository; dataset has academic citation/provenance. Preserve source/citation metadata and verify source-specific terms where relevant.
- Important dependencies/risks: **The current validator has a material bug:** `if charge_type == "customer" or "demand": return True` is always truthy in Python, so its advertised continuity check does not actually prove full time coverage. Re-run independent continuity/completeness tests before any tariff is admitted to money-bearing calculations. Normalized/OpenEI data is reference evidence, not controlling tariff authority.
- Connections: Data moat/discovery plane for the AWS engine; original source URL should enter the authority/provenance graph.
- Opportunity score: **9.2/10**.

### LBNL-ETA/elecprice — independent commercial TOU/demand bill-calculation comparator
- Repository: https://github.com/LBNL-ETA/elecprice
- Commit / revision: a6947c3b65fdedec7da5bbeb52b85e8fdeffd1f4
- Date discovered: 2026-09-22
- What actually works: Lawrence Berkeley National Laboratory Python library for manipulating U.S. commercial electricity tariffs and computing bills from time-series meter data. It models fixed, energy and demand components, commercial time-of-use schedules, monthly detail and Peak Day Pricing events/credits; it can ingest OpenEI-format tariff data or a local revised tariff JSON.
- Evidence of implementation: `electricity_rate_manager/rate_manager.py`, rate/tariff structure modules, OpenEI analyzer and example workflows inspected. The project explicitly documents its supported/unsupported cases rather than claiming universal tariff coverage.
- Rare / undernoticed value: An implementation from a materially independent code lineage is useful as a **falsifier** for straightforward commercial tariff cases. Production recovery math should not be validated solely by the same engine that generated the candidate discrepancy.
- Useful capability/workflow: meter interval series + independent tariff representation -> fixed/energy/demand bill breakdown for comparison against the primary engine.
- Likely buyer/user: internal Utility Recovery QA and commercial-building energy analysis.
- Pain solved: independent re-performance of tariff math and demand-charge interpretation.
- Fastest monetization path: internal acceptance/comparator layer in Utility Recovery; not a standalone wedge.
- Estimated engineering time saved: 2-4 weeks of independent comparator and commercial TOU/demand fixtures.
- License / reuse status: LBNL BSD-style permissive license with attribution/nonendorsement conditions.
- Important dependencies/risks: Project is older; README says it is tested mainly for commercial buildings, does not support residential tiers or reactive-power cost, and has PDP-credit limitations. Keep its supported domain narrow and route disagreement to review.
- Connections: independent comparator to AWS RDL/Rust calculation; combine with literal hand-derived goldens and later utility credit/refund evidence.
- Opportunity score: **8.5/10**.

### Wondermove-Inc/saaslens — self-hosted SaaS spend / seat-waste assurance substrate
- Repository: https://github.com/Wondermove-Inc/saaslens
- Commit / revision inspected: 10a93ea490d1d7d98df041b368d04d292096c7f5
- Date discovered: 2026-09-22
- What actually works: MIT Next.js/Postgres multi-tenant SaaS-spend platform with payment/card import and merchant-to-app matching, subscription inventory, SSO/browser-extension usage evidence, seat assignment/utilization, terminated-user access scanning, renewal alerts, cost analytics, unused-app analysis, billing-model/seat-price inference and broad tests.
- Evidence of implementation: `seat-waste-analysis.ts` and tests explicitly refuse to classify missing/null telemetry as inactive; only observed stale use is counted inactive, while unassigned paid seats are separately counted. `unused-apps.ts` combines UserAppAccess and browser-extension evidence. `seat-optimization.ts` simulates seat reductions and adds a 15% active-user buffer. Payment matching, cost analytics, renewal alerts, terminated-user scanning and seat-price heuristics have dedicated tests.
- Rare / undernoticed value: Supplies most of the data plane for an evidence-backed **SaaS Spend Assurance** service without requiring expensive commercial SaaS-management tooling.
- Useful capability/workflow: payment/card feed + SaaS identity + assigned seats + observed use/offboarding + renewal date -> evidence-ranked waste/renewal review -> human-approved seat/license changes -> later invoice confirmation.
- Likely buyer: 50-1000 employee tech/professional-services firms, PE portfolio ops, IT/finance/procurement.
- Pain solved: orphaned seats, former-employee access, shadow subscriptions, unmatched card spend and renewals happening without usage evidence.
- Fastest monetization path: read-only 30-day SaaS spend/seat audit followed by recurring renewal calendar and optimization review.
- Paid-pilot concept: reconcile 6-12 months of card/AP payments to SaaS inventory, import Workspace/SSO or usage evidence, and produce a pre-renewal cancellation/downsize queue.
- Estimated engineering time saved: 3-6 months of multi-tenant SaaS inventory, payment matching, telemetry, seat analytics, renewals and dashboard work.
- License / reuse status: MIT.
- Important dependencies/risks: This is primarily **future spend avoidance**, not recovery. Estimated annual/monthly “savings” are not realized until a vendor contract/seat count changes and later invoices actually decrease. The optimization path may treat missing usage as zero active for recommendation math more aggressively than the waste-analysis path, so human review/telemetry-sufficiency gates are required. Never charge a recovery fee on forecast savings.
- Connections: reuse the portfolio's settlement/outcome discipline to track `candidate waste -> approved change -> vendor confirmation -> subsequent lower invoice -> realized avoided spend`.
- Opportunity score: **8.8/10**.
