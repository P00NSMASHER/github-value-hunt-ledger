# Cumulative Freight Lab Audit and Donor Review

This GitHub folder is the **canonical research index**. The read-only SQLite semantic oracle, original auditor inputs and all standalone negative-control tests are delivered together as a portable research ZIP. Neither this folder nor the ZIP changes the hosted RecoveryOS application.

`python -m unittest -q freight.test_lab_integrity_registry` checks that all 26 historically observed IDs remain present, explicitly evidenced fixes aren't invented and no rights or deployment claims are silently promoted. The index counts two more defects found and repaired in the **research gate itself**. This is a research-inventory pass, not financial release authorization.

## Portable proof gate notes



- `CUMULATIVE_LAB_FINDINGS.json`: 28 individually identified observations, severity, overlapping root-cause cluster, status, source audit, suggested donor.
- `source_audits/`: the two original audits with SHA-256 provenance; do not overwrite them.
- `DONOR_SHORTLIST.json`: eight pinned, source-inspected donor repositories with licenses, suitability, acceptance tests and major restrictions. No donor code copied, installed or deployed.
- `proof_gate.py`: independent **read-only** SQLite event, journal, source-identity and state oracle for the *fictional* Unified staging database. Does not import or trust the staging engine's verifier.
- `run_validation.py`: CLI that returns **0 only for the narrowly labeled synthetic PASS**, **1 for semantic FAIL**, and **2 for invalid input**.
- `frozen_source_24.jsonl.gz`: tiny fictional source data with sealed synthetic truth labels; **never give this to a supposedly blind detector**.
- `baseline_24.sqlite3`: copied fictional 24-case database to audit, not a production environment.
- `test_proof_gate.py`, `test_registry.py`: positive and negative controls, including intentionally rehashed wrong evidence.
- `build_findings.py`, `build_donors.py`: deterministic input-to-registry builders.

## Commands

```bash
python -W error::ResourceWarning -m unittest -q test_proof_gate test_registry
python build_findings.py
python build_donors.py
SHA=$(sha256sum frozen_source_24.jsonl.gz | cut -d' ' -f1)
python run_validation.py baseline_24.sqlite3 frozen_source_24.jsonl.gz --expected-source-sha256 "$SHA"
```

The last command **MUST fail** (exit 1) with observed missing independently supplied contractual fee receipts and fee-accrual discrepancies. That is an intentional **good failure**; a previously green staging verifier does not overrule it. A one-case synthetic clean intake is independently verified to pass in the unit suite.

## Major limitations



- SHA-256 protects consistency relative to an independently pinned digest, **not** authenticity when a single party can rewrite both the source and its digest. The test fixture's hash is not an externally witnessed signing certificate.
- A caller-provided fee-bps integer is **not a cryptographically verified signed agreement**; even with a value present, this gate must never be called legal fee authorization.
- The gold fields in the fictional source are a *reference oracle*, not independently adjudicated real-customer invoice facts. The test has no true blind evaluator process isolation yet.
- Source/tenant identity collision checks are conservative because the old database lacks independently authorized economic-issue and ownership records. Legitimate multiple different issues per invoice may require separate reviewable identity models.
- No cloud concurrency, hosted Floot tenancy, bank credit, customer settlement, independently signed evidence or external data has been tested.
- Donor code is only a documented architecture candidate. Inspect exact HEAD, full dependency tree, rights and test coverage again before any import.

**Next engineering prerequisite:** repair the original staging twin's entitlement and financial accounting in an isolated PR, run all reproduced audit cases as fail-before/fix-after regressions, and then execute actual RecoveryOS staging code with authorized fictional tenants. Do not promote the existing giant synthetic-suite results to financial certification.