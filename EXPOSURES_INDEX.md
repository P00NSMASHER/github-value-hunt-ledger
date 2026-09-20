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