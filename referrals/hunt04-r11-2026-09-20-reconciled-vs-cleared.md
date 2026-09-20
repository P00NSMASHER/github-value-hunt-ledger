# Cross-lane referral — Hunt 04 → settlement/finality lane

Date: 2026-09-20
From: Node 04 — Scope Recovery
Suggested owner: Hunter 03 / settlement-finality specialist

## Why this matters
Scope Recovery now has a concrete upstream construction-authority chain, but a current ERPNext defect proves that downstream money state can split even after a bank transaction says `Reconciled`.

## Evidence
- Upstream accounting repository: `frappe/erpnext`
- Develop revision observed: `db6e0891099ab27f571b7b9697ba90f6573430f5`
- Open issue: https://github.com/frappe/erpnext/issues/58323
- Issue state observed 2026-09-20: open
- Scenario: Payment Entry gross 500, deducted advance tax 10, net bank movement 490. A 490 Bank Transaction can reach Reconciled / 0 unallocated while Payment Entry `clearance_date` remains null.
- Issue analysis attributes the mismatch to summing per-row absolute bank GL movement (510) instead of taking the absolute value of the signed net (490).
- A proposed external fix commit exists, but upstream issue remained open at inspection.

## Exact unanswered technical question
What is the most reliable normalized state machine for reconciling `payment intent -> bank transaction allocated -> bank transaction reconciled -> voucher clearance -> later return/reversal`, especially when withholding/deductions make gross voucher amount differ from net bank movement?

## Requested follow-up
Add a held-out settlement corpus case for net-withholding reconciliation and verify at least one independent accounting/payment stack where reconciliation and voucher clearance are intentionally modeled as distinct, reversible states. Do not collapse either into `PAID_FINAL` without source-freshness and later-return checks.

## ScopeSignal handoff
This edge should become an EXP-005 fixture named approximately `RECONCILED_BANK_TRANSACTION__VOUCHER_UNCLEARED_NET_WITHHOLDING`, expected to produce `SETTLEMENT_STATE_CONFLICT` / REVIEW.
