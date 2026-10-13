# RETALLY Research Lab 14 — Mission 42: Reject hidden duplicate financial identifiers

**October 13, 2026 · DRAFT / INTERNAL RESEARCH ONLY · stacked on M41 PR #435.** No merge, production deployment, schedule change, live customer data, carrier contact, financial action or external claims.

## Actual verifier bug addressed

The independent read-only settlement verifier in freight/lab_assurance.py consumes arbitrary scoped SQLite tables, including legacy imports without the primary-key constraints used by the production-oriented SettlementStore schema. It formerly converted recovery, payment, counter and allocation rows into dictionaries keyed by their IDs, but checked duplicated identifiers only for recovery claims and settlement events. An untrusted imported snapshot with **two counter or allocation rows sharing the same identifier** could be silently collapsed to one record and then treated as valid. The reversal rows were processed as a list, but no reversal_id uniqueness check existed, and two records with the same reversal ID and equivalent aggregate money could be accepted. A passing local SHA never establishes independent bank or carrier authorization.

Mission 42 directly hardens this **current verifier** rather than merely adding another status flag.

### Implemented controls

- Strict row-census checks are added **before credit/fee allocation accounting**. Counter IDs and allocation IDs must be unique in the *original fetched rows*, not just dictionary keys.
- Reversal IDs must be nonempty strings and unique within the scoped original row population. An invalid or duplicated reversal identity fails before financial calculations.
- Existing claim/event duplicate detection remains in place. Existing legitimate settlement, partial returns, fee recognition, audit receipts and synthetic economics remain unchanged.

### Executable isolated attacks

| Unconstrained test-only SQLite scenario | Duplicate shape | Required verifier rejection |
| --- | --- | --- |
| ALLOCATION | Two identical allocation-400 rows, 1 dictionary key | DUPLICATE_ALLOCATION_ID |
| COUNTER | Two identical return-500 rows, 1 dictionary key | DUPLICATE_COUNTER_ID |
| REVERSAL | Two reversal-500 rows split as 499 + 1 cents; total equals original 500 | DUPLICATE_OR_INVALID_REVERSAL_ID |

Each starts from the current Python verifier’s **passing positive settlement** with a fictional $5.00 net recovered, $1.00 earned/collected fee and **test-only HMAC signing keys**. It then mutates only a new temporary SQLite file. A missing positive result, wrong denial code, incorrectly sized test rows or accepted bad rows fails the run.

The new M42 checks run inside original Lab 14; no 15th lab is created. The existing M39 cross-lab acceptance now requires three exact M42 negative outcomes and rejects a fake historical closure count. The same three scenarios are also exercised by independent CI code that does not call the M42 runner.

### Changed files

- freight/lab_assurance.py — actual independent-verifier duplicate-row defense.
- freight/test_lab_assurance.py — four direct regression cases, including an invalid/null reversal identity.
- freight/lab_settlement_identity_m42.py — three isolated SQLite positive/negative proofs with internal JSON/HTML receipts.
- freight/test_lab_settlement_identity_m42.py — adversarial tests for all three scenarios, wrong denial, falsely accepted attack, missing positive control, malicious case names, null reversal, HTML escaping and fail-before-output behavior.
- freight/lab_phase4_director.py — Lab 14 acceptance requires all three actual verifier denials.
- freight/lab_cross_lab_assurance_m39.py and freight/test_lab_cross_lab_assurance_m39.py — bounded cross-lab proof gates.
- freight/lab_phase4_control_center.py — internal source-row identity panel and reports.
- .github/workflows/retally-settlement-row-identity-m42.yml — PR/manual-only suite, existing 14-lab runtime and independent raw SQLite negative proof, short-lived derived receipts.

### Reproduction

    PYTHONPATH=. python -m pytest -q freight/test_lab_settlement_identity_m42.py freight/test_lab_assurance.py
    PYTHONPATH=. python -m freight.lab_settlement_identity_m42 --as-of-date 2026-10-13 --out /tmp/retally-m42
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-m42-control

## Strong limits

This is a meaningful code-level improvement to the *independent current read-only verifier*. It **does not prove an actual financial exploit occurred in production**. The temporary unconstrained database is intentionally less strict than the current SettlementStore schema. The original **26 historical RecoveryOS findings remain OPEN_UNVERIFIED**, including those that relate to suspicious cash and source rights. No archived original vulnerable baseline, real customer invoice, provider bank account or external human approval was independently reexamined in M42. All **18 customer pilot human gates remain unmet**. These local synthetic results cannot authorize recovered-cash, audit-accuracy, serviceable-market or marketing claims.

**No merge, external publication, deployment, real data import, schedule change, carrier contact or payment.**
