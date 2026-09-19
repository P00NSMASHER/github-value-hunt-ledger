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
