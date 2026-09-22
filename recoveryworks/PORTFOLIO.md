# RecoveryWorks portfolio readiness

RecoveryWorks uses one RecoveryOS proof, ledger, review, authorization, and
outcome model across all divisions. Branch status below describes the code path
in this repository; it does not imply customers, recoveries, or commercial
traction.

## Status definitions

- **Operational ingestion** — branch has deterministic/proof-bound ingestion,
  RecoveryEngine output, Scan 360 orchestration, durable-ledger reporting, and
  automated tests.
- **Foundation** — branch is registered with policy/architecture but does not yet
  have a complete Scan 360 ingestion path.
- **External action** — intentionally separate from ingestion. No branch may
  contact a counterparty, submit a claim/dispute, or move money without the
  existing human-review and explicit-customer-authorization gates.

## Current branches

| Branch | Recovery direction | Repository status | Primary evidence |
|---|---|---|---|
| FreightRecovery | overpayment | Operational ingestion | invoice/shipment + contract/tariff authority |
| PayerRecovery | underpayment | Operational ingestion | deidentified claim/remittance + verified rate/policy |
| UtilityRecovery | overpayment | Operational ingestion | bill/usage + effective-dated tariff |
| APRecovery | overpayment | Operational ingestion | payments/invoices/vendor statements |
| DutyRecovery | overpayment | Operational ingestion | customs entry + professionally reviewed expected assessment |
| SaaSRecovery | overpayment | Operational ingestion | invoice + subscription contract + independent seat/usage quantity |
| TelecomRecovery | overpayment | Operational ingestion | invoice + service contract + independent CDR/usage quantity |
| RebateRecovery | underpayment | Operational ingestion | rebate program + purchase population + settlement evidence |
| LeaseRecovery | overpayment | Operational ingestion | landlord charge + effective lease rate + independent area/allocation evidence |
| ConstructionRecovery | underpayment | Operational ingestion | reviewed entitlement + event mapping + versioned CPM schedules + qualified causation review + settlement evidence |

## Shared commercial motion

A single client can be scanned across multiple branches without creating
separate companies or ledgers:

1. freeze the supplied source population
2. hash and normalize branch inputs
3. calculate expected vs actual deterministically
4. separate REVIEW from VALIDATED dollars
5. route validated candidates to a human reviewer
6. require explicit client authorization before external recovery activity
7. record recovered cash and realized fees in the common ledger

This supports both a historical **Recovery Scan 360** engagement and continuous
monitoring using the same evidence model.

## Cross-sell map

A manufacturer/distributor can plausibly supply inputs for:

- FreightRecovery
- APRecovery
- UtilityRecovery
- DutyRecovery
- SaaSRecovery
- TelecomRecovery
- RebateRecovery
- LeaseRecovery
- ConstructionRecovery when project records exist

A healthcare provider can plausibly add PayerRecovery to the same shared
portfolio.

## Portfolio state

All 10 registered RecoveryWorks divisions now have operational Scan 360
ingestion paths with the same durable evidence/lifecycle model.

ConstructionRecovery completes the previously missing lane with:

- reviewed contract/change-order entitlement evidence;
- claimant/project scope enforcement;
- source-hashed baseline and update schedule versions;
- deterministic finish-to-start CPM calculation and project-duration comparison;
- explicit event-to-activity mapping;
- qualified causation review bounded by reproducible CPM impact; and
- settlement evidence establishing the actual amount received.

The next leverage layer is deeper source automation: direct P6/XER normalization,
drawing/model revision deltas, quantity takeoff changes, and field-evidence links.
Those should feed the existing proof model rather than bypass its review gates.
