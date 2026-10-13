# RETALLY Lab 14 / Mission 41 — Executable analog replays for critical failure classes

**October 13, 2026 · draft/internal-only · stacked on M40 PR #434.** No merge, deployment, cron, customer contact, private invoices, provider requests or funds.

## Functional upgrade

Prior Missions 35–40 substantially improved public-source truth boundaries, simulated claims, and experiment-ledger integrity. They deliberately did not replay actual attack conditions for the original **26 OPEN_UNVERIFIED** findings. Mission 41 now directly exercises four **critical analogs** against the **CURRENT** real source-code path through the existing Python settlement verifier. Every attack runs in its own disposable SQLite database using existing **test-only, fictional HMAC signers**. Each requires a previously passing positive settlement control **and the exact rejection reason**, not merely a caught exception.

| Original finding | Current implementation synthetic attack | Required denial |
| --- | --- | --- |
| LAB-P0-01, historically unbacked candidate balance | Direct SQLite allocation/balance inflation beyond provider receipt | RECEIPT_OVER_ALLOCATED |
| LAB-P0-02, historically changed invoice totals | Direct SQLite claim-total rewrite without buyer-signed source update | SOURCE_OWNER_BINDING_MISMATCH |
| LAB-P0-03, historically phantom cash | Insert fictional $90,000 provider-receipt row with no separately signed provider attestation | MISSING_CREDIT_RECEIPT |
| D-01, historically double-recovered invoice | A second fictional buyer-signed claim bearing the **same economic issue identifier** | DUPLICATE_ECONOMIC_RECOVERY |

**These are analog replays of failure classes against today's code, not reproductions against the original archived vulnerable commits.** They neither establish that the historical defect was fixed nor establish bank, carrier, buyer or third-party authentication. The positive fixture has a fictional $5.00 retained recovery and $1.00 earned/collected fee. That cash is **not real** and MUST NOT be reused in product marketing.

The four negative outcomes are incorporated as a **real execution gate inside existing Lab 14**: one unexpectedly accepted mutation, a missing positive control, a wrong denial code, or a changed original-finding registry fails the Lab 14 run. No additional research lab is created. M39's cross-lab verifier now also requires the specific M41 result counts and local-report receipt shape. This is a meaningful regression expansion beyond merely guarding report status flags.

## Implementation and acceptance

- freight/lab_critical_counterexample_replay_m41.py — fresh SQLite positive and mutated records per critical case; four precisely typed expected denials; JSON/HTML internal evidence report with scope limitations and hashed fictional snapshots, no customer data.
- freight/test_lab_critical_counterexample_replay_m41.py — positive/negative end-to-end checks, attacker bypass mock, wrong exception, invalid positive control, frozen finding status, unknown ID, HTML escaping and before-write CLI rejection.
- freight/lab_phase4_director.py — mandatory four modern negative probes in original Lab 14, fail-closed if any is accepted or falsely marked as original historical repair.
- freight/lab_cross_lab_assurance_m39.py — exact additional M41 proof checks in existing 14-lab report verifier.
- freight/lab_phase4_control_center.py — new critical-case card plus separate evidence JSON/HTML report.
- .github/workflows/retally-critical-counterexample-m41.yml — PR/manual-only exact-head tests, existing 14-lab run, independent adversarial challenge, short-lived derived receipts.

## Safety and original status

No pin to the **original vulnerable commits** was provided by the legacy audit register. M41 therefore labels every analog CURRENT and every original finding OPEN_UNVERIFIED. All **26 original defects remain open**, including these four; separately identified two standalone research-gate issues do not close RecoveryOS bugs. All **18 independent human pilot evidence requirements** remain unmet. Nothing here constitutes production security certification, independently verified settlement funds, authority to contact a carrier or permission to publish recovery-rate or market-size claims.

Run locally:

    PYTHONPATH=. python -m pytest -q freight/test_lab_critical_counterexample_replay_m41.py freight/test_lab_phase4_director.py
    PYTHONPATH=. python -m freight.lab_critical_counterexample_replay_m41 --as-of-date 2026-10-13 --out /tmp/m41
    PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/m41-control

No further action to main, production configuration, scheduled automations, external messaging, business registration, customer/payment accounts or public claims is authorized by this research-only draft.
