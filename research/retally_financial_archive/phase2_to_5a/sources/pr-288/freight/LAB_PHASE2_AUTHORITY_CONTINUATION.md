# RETALLY Phase 2 continuation: evidence-controlled settlement intelligence

This is the next **draft research implementation** after GitHub #286. It reuses
existing `freight.settlement_store.SettlementStore` instead of introducing a
second writable settlement ledger. A separate read-only verifier consumes a
consistent SQLite snapshot and **externally supplied** signed fixture assertions
for source identity, credit issuance, returns, contractual fee terms, cash fee
collection and fee refunds. The signing keys in tests are deliberately public
fictional keys; **this is not real buyer/bank/carrier authentication**.

## New modules

- `freight/lab_assurance.py`: independent review-only settlement and fee replay,
  receipt-cap conservation, economic issue identity, historic fee terms,
  cross-currency separation, receipt provenance, fee-refund liabilities, no
  silent profit flooring, typed failures and evidence-bound receipts.
- `freight/lab_operations_intelligence.py`: finite typed route with evidence
  links and an independently computed financial receipt; emits **plans**, not
  executed jobs, for all 14 labs. Provides modeled cost and claim-escalation
  decisions with signed negative margins.
- `freight/lab_phase2_pipeline.py`: single call wrapping independent verification,
  business decisions, and routing over the existing domain's persisted data.
- `freight/lab_customer_scenarios.py`: deterministic controller/SMB behavior
  hypotheses tied to event dates and refund status, never actual customers.
- `freight/lab_experiment_ledger.py`: durable append-only local experiment
  receipts with identity-checked replays and explicit scope labels.
- `freight/lab_phase2_demo.py`: fully fictional, small executable control
  scenario; produces JSON and readable owner memo.
- Corresponding regression tests including
  `freight/test_lab_assurance_real_store.py` for the *actual* SettlementStore.

## How it improves real engineering usefulness

Instead of trusting stored summary balances, it reconstructs the economics
from claim, credit, allocation, counter-event, reversal and separately evidenced
fee events; rejects forged/unsigned and wrong-scope sources, inflation,
reverse-without-source, duplicated credit capacity, unsupported fee rates,
misdated accrual, missing refunds, unsupported write-offs, and missing external
assertions. Authentic signing keys must be held by a separate verifier outside
any tested code or public repository for any stronger claim.

The isolated complex case contains a $10 fictional claim, $4 and $6 credits,
then a $5 return, leaving $5 retained recovery. The 20% hypothetical terms
would produce $1 earned fee, $1 net collected after a 50-cent refund, and an
assumed **negative 90-cent** operating margin. Partial credit and fee
reconciliation are checked by independent Python code and, on GitHub CI, the
existing SettlementStore. A separate causal persona model demonstrates status
and documentation objections; its thresholds are uncalibrated assumptions.

## Execute

```bash
PYTHONPATH=. python -W error::ResourceWarning -m unittest -q \
  freight.test_lab_assurance \
  freight.test_lab_operations_intelligence \
  freight.test_lab_phase2_pipeline \
  freight.test_lab_customer_scenarios \
  freight.test_lab_experiment_ledger
PYTHONPATH=. python -m freight.lab_phase2_demo --output /tmp/retally-phase2-demo
```

On repository GitHub CI, also exercise the full existing
`freight.test_settlement_store` and
`freight.test_lab_assurance_real_store` against the *actual domain code*.

## Non-claims and outstanding work

- No hosted RecoveryOS access, tenant staging deployment, or external identity
  system was available to verify product equivalence.
- Public test keys, lab source hashes and the created receipt are not legal
  authority, actual recovered customer cash, or completed remittance proof.
- The cross-lab routing is executable mapping, but it does not run 14 remote lab
  processes or replace their specialized domain adapters.
- Financial balances are independently recomputed for a controlled synthetic
  case, not externally verified against true statements and contracts.
- All 26 historical audit findings remain formally open until individual
  comprehensive closure is separately evidenced.
- No donor source code was incorporated; historical pinned-license reviews
  remain research inputs rather than new production dependencies.
- No CI workflow is scheduled and no application, website, carrier, bank,
  customer message, purchase or external action is performed.

**Next external prerequisite:** obtain legitimate buyer-controlled source
and signed contracts plus authoritative provider and bank remittance evidence;
then test the real hosted RecoveryOS in an authorized isolated staging tenancy.
