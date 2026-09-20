# Redacted Exposure Metadata

Cross-lane index maintained by Hunt 15 MASTER Integrator.

This file records only non-sensitive metadata when a hunter encounters accidentally published credentials, authentication material, private/personal data, confidential material, or similar exposures while searching public GitHub.

Allowed fields:
- Repository
- Canonical URL
- File/path
- Exact revision
- Date observed
- High-level exposure type
- Apparent status if knowable without testing
- Non-sensitive context
- Remediation / reporting note

Never store, reproduce, test, validate, authenticate with, exploit, or monetize the sensitive value itself. Replace any such value with `[REDACTED]`.

## Redacted exposure observations — 2026-09-19

### Andalusia-Data-Science-Team/QA-for-call-center
- Repository: `Andalusia-Data-Science-Team/QA-for-call-center`
- Canonical URL: https://github.com/Andalusia-Data-Science-Team/QA-for-call-center
- File/path: README-referenced database configuration artifact; the potentially sensitive artifact itself was not opened.
- Exact revision: `fd4c22995809ff78568dad18856fede665fa4ff1`.
- Date observed: 2026-09-19.
- High-level exposure type: credential-bearing database configuration was advertised/referenced by repository documentation.
- Apparent status: **unknown; not tested or validated**.
- Non-sensitive context: project appeared tied to a clinical contact-center environment, increasing the cost of unnecessary inspection.
- Remediation/reporting note: keep the revision quarantined; revisit only a clearly sanitized revision with synthetic/public fixtures. No credential value is stored here.

### ansh-guptaa/LastMileSaathi
- Repository: `ansh-guptaa/LastMileSaathi`
- Canonical URL: https://github.com/ansh-guptaa/LastMileSaathi
- File/path: commit-history artifact; exact secret-bearing path/value intentionally not retained in the shared ledger.
- Exact revision encountered: `ae9e4d2196aedc2b822838a44dd713566318b009`.
- Date observed: 2026-09-19.
- High-level exposure type: authentication material surfaced during commit-history inspection.
- Apparent status: **unknown; not tested, authenticated with or validated**.
- Non-sensitive context: inspection stopped when the exposure was encountered.
- Remediation/reporting note: use only a later sanitized revision; do not reopen historical secret material. No authentication value is stored here.

### adrianstanca1/cortexx
- Repository: `adrianstanca1/cortexx`
- Canonical URL: https://github.com/adrianstanca1/cortexx
- File/path: committed environment-vault artifact; artifact was not opened and exact sensitive contents were not inspected.
- Exact revision: `87679c82a6bb5cf3619d63ee32786f8260f3ef6b`.
- Date observed: 2026-09-19.
- High-level exposure type: environment/secret-vault style configuration artifact.
- Apparent status: **unknown; not tested or validated**.
- Non-sensitive context: recursive tree inspection alone was sufficient to trigger quarantine.
- Remediation/reporting note: revisit only a clearly sanitized later revision and only for a concrete unmet construction-domain gap.

### boomlocal/Dumpster-Rental-Management-System-2320
- Repository: `boomlocal/Dumpster-Rental-Management-System-2320`
- Canonical URL: https://github.com/boomlocal/Dumpster-Rental-Management-System-2320
- File/path: committed environment file; file was not opened.
- Exact revision: `ca9ec596d559c10c64fcdd3706f125f1985f9af7`.
- Date observed: 2026-09-19.
- High-level exposure type: environment/configuration artifact that may contain authentication or service credentials.
- Apparent status: **unknown; not tested or validated**.
- Non-sensitive context: repository was being evaluated as a waste/field-service vertical analog.
- Remediation/reporting note: safety quarantine this revision; revisit only a sanitized later revision. No values are stored here.

### ClintonK399/Fuel-Delivery-Management-System
- Repository: `ClintonK399/Fuel-Delivery-Management-System`
- Canonical URL: https://github.com/ClintonK399/Fuel-Delivery-Management-System
- File/path: database-configuration artifact; artifact was not opened.
- Exact revision: `ced5ce2faecd5ceea4cc7fa94d7275b1cce35a3d`.
- Date observed: 2026-09-19.
- High-level exposure type: database connection/authentication configuration risk.
- Apparent status: **unknown; not tested or validated**.
- Non-sensitive context: safe evidence did not establish enough domain value to justify deeper inspection around the risky artifact.
- Remediation/reporting note: keep quarantined/deprioritized; revisit only a sanitized revision with a specific fuel-delivery gap to solve. No credentials or connection values are stored here.

## Index policy
- A metadata entry is not evidence that any credential is valid, live or exploitable.
- Do not test or authenticate with accidental material.
- Do not copy a raw value into issues, commits, chat, logs, benchmarks or product artifacts.
- When a safe sanitized revision exists, use that revision and preserve the quarantine note for the older one.

<!-- INTEGRATOR-R11-2026-09-20T0025-0400 -->
## Additional redacted exposure observations — 2026-09-20

### sandyliu3056/UPS-reconciliation
- Repository: `sandyliu3056/UPS-reconciliation`.
- Canonical URL: https://github.com/sandyliu3056/UPS-reconciliation
- Exact revision used for safe technical evidence: `d1e11940b262debc3c3216aba6467f39722c3000`.
- High-level exposure type: repository documentation/history indicated older public versions contained password/authentication material.
- Apparent status: **unknown; no historical value was retrieved, copied, tested or validated**.
- Non-sensitive context: current safe source was evaluated only for parcel correction/rebill semantics.
- Remediation note: repository owner should ensure any historical credential is revoked/rotated; hunt should use only sanitized revisions and never reopen secret-bearing history.

### BritneyMcCullough/PayrollReconciliation
- Repository: `BritneyMcCullough/PayrollReconciliation`.
- Exact revision: `64cd190...` (full exact SHA preserved in hunter 21).
- High-level exposure type: tree contains payroll-like `data/uploads/` and `data/runs/` artifacts that could hold personal/private operational data.
- Apparent status: **not inspected**; no artifact contents or personal values were opened or retained.
- Non-sensitive context: safe source/code evidence was sufficient to assess its normalization/matching architecture.
- Remediation note: continue code-only inspection; use synthetic fixtures for benchmarking unless customer data is explicitly authorized.

### adamleap02/PermitBuild
- Repository: `adamleap02/PermitBuild`.
- Exact revision: `ff795137e0c66e62a87e62956fa351926886255d`.
- High-level exposure type: repository documentation reports `backend/.playwright-signup-evidence/` may contain browser-profile/cookie/autofill/payment-adjacent state.
- Apparent status: **not opened, copied, tested or used for authentication**.
- Non-sensitive context: permit connector/version/semantic-QA code was assessed independently of that directory.
- Remediation note: owner should review/remove any sensitive browser state and revoke unintended accounts; hunt must continue to avoid the directory.

### kasun-m-rathnayaka/gas-distributer-backend
- Repository: `kasun-m-rathnayaka/gas-distributer-backend`.
- Exact revision: `f0a1f8013759f11be625f383a9449826f0751f37`.
- File/path: committed `backend/.env.development.local`; file was not opened.
- High-level exposure type: environment/configuration artifact potentially containing secrets/auth material.
- Apparent status: **unknown; not tested or validated**.
- Remediation note: quarantine this revision; revisit only a sanitized revision/fork.

### dev-k99/ScrapFlow
- Repository: `dev-k99/ScrapFlow`.
- Exact revision: `170a655118347be55fcefd8f94f51747df8a9a35`.
- High-level exposure type: public documentation exposed authentication material.
- Apparent status: **unknown; no value retained, tested or used**.
- Remediation note: revisit only sanitized later revision; rotate/remove any exposed authentication material.

### openmymed/open-fleetr
- Repository: `openmymed/open-fleetr`.
- Exact revision: `8a4bfdd8ff644784b3706d4821ca49fb98e5c188`.
- High-level exposure type: public SQL artifact contains credential-like authentication material and personal-data-like seed values.
- Apparent status: **not inspected beyond safe metadata; no value/person record retained or tested**.
- Remediation note: sanitize the dump and rotate potentially live credentials before any revisit.

### anjalaeepriyadarshaniyapa/Medical-Waste-Management-System
- Repository: `anjalaeepriyadarshaniyapa/Medical-Waste-Management-System`.
- Exact revision: `f1ea2792db9b3a8684a68677c2f4391a6107c83b`.
- High-level exposure type: README contains login credential-like authentication material.
- Apparent status: **unknown; no value retained, tested or used**.
- Remediation note: remove public authentication material and rotate if potentially live; inspect only a sanitized later revision.

### AbhishekLGowda05/SAGE-Scheduling-engine-with-Adaptive-constraint-relaxation-Grounded-Explanations
- Repository: `AbhishekLGowda05/SAGE-Scheduling-engine-with-Adaptive-constraint-relaxation-Grounded-Explanations`.
- Canonical URL: https://github.com/AbhishekLGowda05/SAGE-Scheduling-engine-with-Adaptive-constraint-relaxation-Grounded-Explanations
- File/path: `frontend/.env`; contents were deliberately not opened.
- Exact revision: `49aee96f0a15e12e7b14b1c97989600f7ab0a146`.
- Date observed: 2026-09-20.
- High-level exposure type: committed environment/configuration artifact potentially containing service or authentication material.
- Apparent status: **unknown; not inspected, copied, tested or validated**.
- Non-sensitive context: safe solver source and tests were sufficient to assess the scheduling/constraint-relaxation capability without touching the environment file.
- Remediation note: use only sanitized configuration for any reuse/deployment review; do not inspect or rely on the committed environment artifact. No secret value is stored here.

### Akash-kolladikkel/Emirates-Line-Tariff-Scraper-AI
- Repository: `Akash-kolladikkel/Emirates-Line-Tariff-Scraper-AI`.
- Canonical URL: https://github.com/Akash-kolladikkel/Emirates-Line-Tariff-Scraper-AI
- File/path: `Base-code/.env` and `Main-code/.env`; contents were deliberately not opened.
- Exact revision: `5a2a48ea0f4b3d985076082ab4a43f7c9d214644`.
- Date observed: 2026-09-20.
- High-level exposure type: committed environment/configuration artifacts potentially containing service or authentication material.
- Apparent status: **unknown; tree names only were inspected, values were not opened, copied, tested or validated**.
- Non-sensitive context: safe scraper source was sufficient to assess carrier-published detention/demurrage schedule acquisition behavior without touching either environment file.
- Remediation note: use only sanitized configuration for any reuse; do not inspect or rely on the committed environment artifacts. No secret value is stored here.

<!-- INTEGRATOR-R11-POSTCHECKPOINT-2026-09-20T0056-0400 -->
### muhdwaseem/Logisticsrate
- Repository: `muhdwaseem/Logisticsrate`.
- Canonical URL: https://github.com/muhdwaseem/Logisticsrate
- File/path: signed-agreement / tariff-seed material referenced by public commit history; exact sensitive artifact contents and contract-derived values were deliberately not opened or retained.
- Exact revision: `6250dc36137f66d65e4d18314d36ca3b86b66913`.
- Date observed: 2026-09-20.
- High-level exposure type: potentially confidential third-party commercial contract/tariff material transcribed into a public repository.
- Apparent status: **not inspected or validated** beyond non-sensitive commit/tree metadata.
- Non-sensitive context: safe architecture evidence was insufficient to justify touching contract-derived material, and repository-code permission does not extend to third-party confidential terms.
- Remediation note: quarantine contract-derived assets; use only a sanitized code revision with independently generated synthetic/publicly authorized tariff fixtures. No commercial rate or contract value is stored here.
