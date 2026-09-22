# ProcurementRecovery ingestion contract

ProcurementRecovery audits supplier invoice charges against effective negotiated contract or PO unit pricing.

## Supplier charges CSV

Default columns: Charge_ID, Counterparty, Account_ID, Service_ID, Service_Date, Actual_Amount.
Counterparty is the supplier. Service_ID should identify the contracted SKU, service, catalog item, or rate line.

## Contract/PO rate CSV

Default shared columns: Counterparty, Service_ID, Effective_From, Effective_To, Fixed_Fee, Included_Units, Unit_Rate.
For ordinary unit-price procurement, Fixed_Fee=0, Included_Units=0, and Unit_Rate is the negotiated price per independent quantity unit.
Fixed contracted fees are also supported.

## Quantity CSV

Columns: Charge_ID, Quantity.
Quantity evidence should come from a customer-controlled receipt, receiving, consumption, or approved-quantity source rather than merely repeating the supplier invoice quantity.
The quantity file is SHA-256 hashed and row-located independently from supplier charges and contract pricing.

If a unit-priced contract rate has no independent quantity record, the candidate fails closed with MISSING_USAGE.
Duplicate charge IDs, conflicting quantity records, missing effective rates, and overlapping contract-rate versions inherit the shared contract-billing fail-closed controls.

## Scan 360 fields

procurement.charges_csv
procurement.rates_csv
procurement.quantities_csv
procurement.charge_source_verified
procurement.rate_source_verified
procurement.quantity_source_verified

## Relationship to APRecovery

APRecovery focuses on payment execution, duplicate payments, vendor credits, and statement reconciliation.
ProcurementRecovery focuses on whether the supplier invoiced the correct contracted unit/fixed price for the independently evidenced quantity.
The two branches can therefore find different recoveries from the same supplier relationship without sharing calculation assumptions.

## Operational boundary

Detection does not authorize a supplier dispute, debit memo, deduction, or contact. Validated findings remain behind RecoveryWorks human review and explicit customer authorization.
