# RETALLY Mission 36 — Public-Copy Claim Release Gate

**October 12, 2026 · DRAFT / NO DEPLOYMENT.** Stacked on Mission 35 PR #426. No changes to previously approved contact, intake, recovery, pricing or customer permissions.

## The risk this closes

Mission 35 established 16 closed source-to-claim decisions: eight source-attributed macroeconomic statements qualified for INTERNAL use, eight unsupported customer/results/TAM inferences blocked, and zero public commercial performance claims authorized. Original 18 human pilot approvals remained unmet.

Previously the M35 claim register existed inside Research Lab 14 but was not connected to RETALLY's GitHub Pages **build path**. A new website headline, social preview description, JSON-LD service metadata, or public script string could claim fabricated refunds or audit accuracy without this research evidence checking the outgoing copy.

**Mission 36 runs the evidence-bound claim-pattern check BEFORE \`freight/site/build.py\` creates the output folder.** Public website builds now fail closed on matched high-risk statements, preserving the existing allowlisted public assets and controlled fictional demo. This does not independently approve any public claims, and does not scan social accounts, email campaigns, connected publishing tools, or externally managed Cloudflare content. It only protects the repository's GitHub Pages freight public bundle.

## Actual build boundary and channels

- **\`freight/site/build.py\`** already uses explicit text/binary allowlists and separately verified business contact + contingency pricing, copies a controlled fictional invoice demo, and outputs to a fresh external directory. After all contact/rate/demo substitutions but BEFORE the first \`mkdir\` or public-file write, it now calls \`require_public_copy_clearance(text_bundle)\`.
- **\`freight/public_claim_release_gate.py\`** is a stdlib deterministic scanner. It inspects all allowlisted HTML visible sections (including text across inline markup), HTML document titles, social/open graph/twitter description metadata, image alt/ARIA labels, JSON-LD name/description/headline fields, and line-scoped raw JavaScript/CSS/CSV/XML/llms.txt material. It rejects malformed JSON-LD; no unexpected binary/font asset is interpreted as prose. It uses a *small high-specificity ruleset*, not an AI model or a claim of semantic completeness.
- The gate reads the **unchanged, closed M35 source/claim policy** and **unchanged M11 human-pilot preflight**. If the M35 source register is invalid, if publication approval is forged, or if the 18 existing buyer/legal/privacy/finance signoffs are misrepresented as completed, the build is blocked. Even a clean output does NOT mean buyer consent or permission to publish real customer claims.
- Matching source issues identify the filename, channel and rule; tests prove a rejected headline leaves **no output directory at all**.
- Normal "$0-upfront audit", *potential* findings, fees conditional on actual eligible recovered funds, "recovery is not guaranteed", and clearly fictional Northstar sample invoicing stay intact.

### Deterministic cases blocked

1. RETALLY/we/our team **asserting past collected customer savings or recoveries** with an unverified numerical amount or invoice count.
2. Asserted **real customer recovery** amounts presented as real company accomplishments.
3. Invented **measured 90%/95%/99% accuracy, recovery rates or success rates**.
4. **Guaranteed refunds, savings, recoveries or accuracy** presented without qualification.
5. Stated dollar **serviceable/recoverable audit TAM** in public sales copy without real buyer/data evidence.
6. The real $142,607.754-million **BEA–Census macroeconomic denominator difference** promoted as recoverable customer overcharges, refunds or market size.
7. The same types of false claims inserted into **social previews, SEO tags, JSON-LD, text, scripts, styles or provider scorecard CSV**, not just visible headings.

**Important limitation:** These are pattern-matched high-confidence risk controls, not a complete natural-language fact checker. Reworded claims or dynamic external content might evade detection, and harmless text with similar patterns might sometimes require review. A clean static preflight is NOT evidence of real audited invoices, permission to solicit customers, or legal/commercial release approval. External platforms and the separately managed canonical domain require their own guard.

## Integration and QA

- \`freight/public_claim_release_gate.py\`: complete scan and M35/M11 unchanged-gate validation with no network access or private customer files.
- \`freight/test_public_claim_release_gate.py\`: adversarial tests for false refunds, recoverable TAM, human reviewer accuracy, fake approval, metadata, JSON-LD, JS/CSS/CSV, path traversal, baseline offer language, and intentionally fictional sample examples.
- \`freight/site/build.py\`: additional prewrite publication stop—no deployment logic or rate calculation changed.
- \`freight/site/test_build.py\`: transactional negative fixture injects a false $8 million customer recovery into an otherwise intact local homepage and verifies no output folder was created. Positive control verifies original demo and contingency offer wording survives.
- \`.github/workflows/freight-site-pages.yml\`: existing **RecoveryOS Public Sites** verification now runs the explicit standalone static preflight and new adversarial site-copy tests before the existing controlled-demo/public build tests and Node syntax checks; the existing deploy job is unmodified, and on a draft PR it does **not** deploy.
- \`.github/workflows/retally-public-copy-claim-gate-m36.yml\`: unscheduled PR/manual-only replay of claim/pilot/source and site-build regression, plus independent adverse-copy check. No cron, third-party accounts, API credentials, sales/email, customer invoice data or money flows.

Reproduction from repository root (Python 3.11+; standard inherited test dependencies):

    PYTHONPATH=. python -m pytest -q freight/test_public_claim_release_gate.py freight/site/test_build.py freight/test_research_claim_clearance_m35.py freight/test_research_pilot_preflight.py
    PYTHONPATH=. python -m freight.public_claim_release_gate --site-root freight/site
    FREIGHT_CONTACT_EMAIL=sales@freightfixture.com FREIGHT_CONTACT_VERIFIED=1 python freight/site/build.py --output /tmp/retally-m36-only-public

No direct approval of external marketing, website deployment or customer onboarding follows from passing tests. All 18 independent real-customer pilot conditions remain unmet.

**NO MERGE OR DEPLOY; NO SCHEDULED TASK MODIFICATION; NO PRIVATE CUSTOMER/CONTRACT/PAYMENT RECORDS; NO CUSTOMER-CARRIER CONTACT; NO REAL CASH OR FREIGHT RECOVERY CLAIM.**
