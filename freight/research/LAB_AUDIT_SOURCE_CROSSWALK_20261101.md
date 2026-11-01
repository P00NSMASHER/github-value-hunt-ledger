# RETALLY research-lab audit crosswalk (November 1, 2026)

**Scope:** historical synthetic/offline testing evidence and candidate-source *metadata*, not production financial testing or authenticated customer evidence.

Two previously separate PRs are preserved unchanged:
- **#279:** `freight/research/LAB_FINDINGS_CUMULATIVE.json` provides a readable 28-entry historical findings/candidate reference, plus a broader **nine-donor** code-research list.
- **#280:** `freight/lab_integrity/CUMULATIVE_FINDINGS.json` provides a second detailed 28-entry synthetic incident register and negative controls, plus a more selective **eight-donor** list.

Both ledgers describe the **same 28 finding IDs**, not 56 independently verified defects. Exactly **26** IDs describe earlier lab observations that were not fully repaired in those historical snapshots. The other **two** (GATE-001/002) are research-proof-gate defects addressed in an *offline research package*, **not** repairs of hosted RecoveryOS.

Both donor catalogs are *dated candidate snapshots*, not current vendor license certifications, approved dependencies or executable adapters. The ninth broad candidate was excluded from the shorter original shortlist; this is not a missing vulnerability or production code. No donor code or third-party model assets were imported.

`freight/test_lab_audit_source_crosswalk.py` fails closed if an original finding disappears, historical open statuses are silently promoted, the two snapshot counts diverge, or the original donor-count boundaries are changed without a conscious update.

**Do not use either snapshot to assert current production vulnerability counts, actual recovered dollars, validated freight scoring accuracy, customer authorization, source licensing or security certification.** Current statuses require a fresh independently evidenced source/runtime audit. This crosswalk does not modify deployments, payment authorities, original source files, financial workflows, or scheduled research.
