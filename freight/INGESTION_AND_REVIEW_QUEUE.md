# CSV ingestion and review queue v1

This layer connects a real export-shaped input to the deterministic Finding Factory.

## Invoice charge CSV

The v1 adapter accepts exactly these columns:

`invoice_id, shipment_id, customer_id, carrier_id, currency, charge_id, charge_code, service_date, quantity_units, billed_cents`

Rules:

- buyer and business-unit scope are supplied by the authenticated caller and are not accepted from the CSV;
- the file first passes the existing fail-closed CSV input guard;
- the header set must be exact; extra/missing/duplicate columns are rejected;
- quantities and money are exact unsigned integers after trimming surrounding export whitespace, never floats;
- currency is normalized to an uppercase three-letter code;
- charge code is normalized to uppercase;
- service date must be ISO `YYYY-MM-DD`;
- duplicate charge IDs are rejected;
- every charge source hash is bound to the complete source-file SHA-256, physical CSV row number and normalized row content.

This adapter does not infer columns, guess currencies, convert dollars to cents, or repair malformed exports.

## Population freeze

The accepted invoice-charge batch is also the source of the frozen pilot population. Multiple charge rows for one invoice/shipment collapse into one population row. The builder fails closed if customer, carrier, or currency identity changes within the same invoice/shipment.

Each population-row source hash binds the invoice-charge adapter hash plus every contributing charge-row source hash. The stated selection rule is included in the population manifest hash. This removes manual population-row entry while preserving the exact evidence that created the scope.

## Charge-rule CSV

The v1 authority-rule adapter accepts only rule semantics:

`charge_code, pricing_model, effective_from, effective_to, fixed_cents, unit_rate_cents`

Buyer/business-unit scope, customer/carrier identity, currency, authority-document ID, original document SHA-256, and **whether the document is verified as controlling authority** all come from trusted caller context. They are deliberately not accepted from the CSV, so a spreadsheet cannot promote itself into controlling authority.

The adapter supports the same `INCLUDED`, `FIXED`, and `PER_UNIT` models as the Finding Factory, validates effective dates and exact integer-cent semantics, rejects duplicate normalized rules, and binds the normalized rule batch to both the CSV file hash and original authority-document hash.

## Review queue

The queue excludes `CLEAR` derivations and orders remaining work deterministically:

1. verified money-bearing findings;
2. calculable money-bearing review items;
3. evidence/rule gaps without a supported dollar estimate.

Within a class, larger supported variance is shown first. The queue is built from challenger output before incumbent output is opened, so it deliberately does not suppress or deprioritize a finding merely because an incumbent may later be shown to have identified it. The queue does not approve findings or replace reviewer judgment. Each item and the complete queue are hash-bound to the Finding Factory output.

## Current boundary

This is intentionally not a universal freight importer. CSV v1 is the first controlled adapter. Carrier-specific EDI/X12 invoice adapters and richer authority models should be added only from a real buyer population with fixtures and exact semantics. The current rule adapter handles normalized deterministic rule rows; it does not extract or interpret prose contracts.
