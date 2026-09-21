# CSV ingestion and review queue v1

This layer connects a real export-shaped input to the deterministic Finding Factory.

## Invoice charge CSV

The v1 adapter accepts exactly these columns:

`invoice_id, shipment_id, customer_id, carrier_id, currency, charge_id, charge_code, service_date, quantity_units, billed_cents`

Rules:

- buyer and business-unit scope are supplied by the authenticated caller and are not accepted from the CSV;
- the file first passes the existing fail-closed CSV input guard;
- the header set must be exact; extra/missing/duplicate columns are rejected;
- quantities and money are exact unsigned integers, never floats;
- currency is normalized to an uppercase three-letter code;
- charge code is normalized to uppercase;
- service date must be ISO `YYYY-MM-DD`;
- duplicate charge IDs are rejected;
- every charge source hash is bound to the complete source-file SHA-256, physical CSV row number and normalized row content.

This adapter does not infer columns, guess currencies, convert dollars to cents, or repair malformed exports.

## Review queue

The queue excludes `CLEAR` derivations and orders remaining work deterministically:

1. verified money-bearing findings;
2. calculable money-bearing review items;
3. evidence/rule gaps without a supported dollar estimate.

Within a class, larger supported variance is shown first. The queue does not approve findings or replace reviewer judgment. Each item and the complete queue are hash-bound to the Finding Factory output.

## Current boundary

This is intentionally not a universal freight importer. CSV v1 is the first controlled adapter. Carrier-specific EDI/X12 and authority-rule adapters should be added only from a real buyer population with fixtures and exact semantics.
