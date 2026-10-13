# RETALLY — Mission 36 public claim publication safety gate

**October 12, 2026 · Draft only · stacked on Research Lab 14 Mission 35 PR #426.**

This is an internal code-based publication check, not a marketing authorization, live moderation service, or real-customer audit.

## Existing publication architecture

The RETALLY freight site already has a closed file allowlist, a verified contact-email gate, configurable contingency pricing, a clearly fictional downloadable audit demonstration, and a GitHub Pages PR verification workflow. The browser form does not accept freight-document uploads. The missing protection was a direct connection from the Mission 35 source-to-claim risk register to the actual public-site build.

## New boundary

The production-site builder scans the **exact transformed allowlisted public text before creating any output directory**. It checks HTML visible copy, structured JSON-LD, SEO/Open Graph metadata, accessibility and dynamic-copy attributes, inline scripts and public JavaScript, text and CSV files. The source claim policy is the pinned original Mission 35 16-case research register: its Git blob must match, all 18 independent human pilot controls remain unverified and no public economic-performance claims are authorized.

The deterministic negative checks prohibit using Mission 35's internal-only BEA/Census/BLS economic numbers in public marketing, especially the $142,607.754 million BEA–Census dollar gap or its rounded $142.6 billion wording. They reject fabricated RETALLY or customer cash recoveries, invented customer invoice counts and success rates, unsupported certification or recovery guarantees, and fictitious numerical examples with missing disclaimers.

The safeguard preserves the already approved user experience: $0 upfront audit, a separately authorized contingency-recovery offering with 30% default rate, honest explanations of recovery stages and the existing hypothetical calculator. The two example pages must still identify themselves as fictional and not real customer results. The homepage's sample invoice/recovery metrics must retain their fictional and non-customer disclaimers.

### Verification and deployment integration

- Public guard module: freight/site/public_claim_gate.py. Fail-closed original Mission 35 policy fingerprint, known false-claim patterns and exact-copy inspection. Errors reveal file names and rule IDs, not potentially sensitive message text.
- Site builder: freight/site/build.py. Checks the fully rendered public text *before writing* any file to the public export directory.
- Negative tests: freight/site/test_public_claim_gate.py. Real source/brand templates, generated public directory, fake recovery money/volume, macroeconomic TAM, meta/structured/JS injection, fictional disclaimers, policy tampering and clean build behavior.
- Existing release pathway: .github/workflows/freight-site-pages.yml. Runs the new tests in its existing verification job, preceding its independently gated main-branch GitHub Pages deployment.
- Dedicated verification: .github/workflows/retally-site-claim-boundary-m36.yml. PR/manual-only, read-only, checks the original allowlist and existing brand marketing templates. No new schedule or deployment.

### Limits

This guard only protects public site builds that run freight/site/build.py, particularly the repository's GitHub Pages workflow. It is **not** integrated with independent Cloudflare deployments that bypass this builder, BubblaV chatbot runtime replies, connected social accounts, advertising, email, or an unscanned document. Its targeted patterns are not a comprehensive natural-language truth verifier, legal review or customer permission check.

Passing this gate only means the known unsupported patterns were not found in the scanned content. It does **not** certify external marketing claims, real-world accuracy, refund amounts, customer consent, governance approval or billing-error rates. All 18 independent pilot-human controls remain unmet.

Run from repository root under Python 3.11+ using existing test dependencies: PYTHONPATH=. python -m pytest -q freight/site/test_public_claim_gate.py freight/site/test_build.py.

**No real customer data, outreach, cash action, production merge/deploy or scheduled task modifications are part of Mission 36.**
