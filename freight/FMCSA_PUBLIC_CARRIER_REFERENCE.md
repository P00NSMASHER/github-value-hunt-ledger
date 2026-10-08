# RETALLY: FMCSA Carrier Reference, research-only prototype

**Status October 8, 2026: SOURCE AND OFFLINE ADAPTER QA ONLY. No production integration or real carrier query has been verified.**

## Publisher and dataset provenance

- **Primary publisher:** Federal Motor Carrier Safety Administration (FMCSA), U.S. Department of Transportation.
- **Official public dataset:** Company Census File, `az4n-8mr2`, https://data.transportation.gov/d/az4n-8mr2 .
- **Original catalog:** https://catalog.data.gov/dataset/company-census-file . On October 8, 2026 the catalog listed last data update **October 7, 2026**. Public access is indicated, but its machine catalog explicitly uses **unknown-license**, so commercial redistribution/training usage rights have not been independently cleared.
- **Data delivery:** Socrata SODA endpoint `https://data.transportation.gov/resource/az4n-8mr2.json`.
- **Upstream GitHub discovery:** `gregchedwick/carrier-survival`, `src/carrier_survival/config.py` at blob `e7d70064c6ba92197623fb675b0c42329bb1c45d`. Its code describes current census as a daily snapshot, not a historical training archive. This is a schema/pipeline research citation, **not** original carrier-data provenance, an imported training dataset, or an endorsement.
- **Other official context:** https://www.fmcsa.dot.gov/registration/fmcsa-data-dissemination-program and the SAFER status definitions https://safer.fmcsa.dot.gov/saferhelp.aspx .

## Implemented code and strict scope

The source-only internal module `freight/fmcsa_public_carrier.py` provides:
- `build_query_url(usdot)`: validates a canonical 1–9 ASCII-digit USDOT number and emits a bounded HTTPS lookup with `$limit=2`, restricted `$where` and only `dot_number`, `legal_name`, and `nbr_power_unit` fields.
- `lookup_public_carrier(usdot)`: **explicit** on-demand read-only lookup with a short timeout, 8 KiB response cap, no repeated paging or persistence; caller should have a legitimate carrier-specific verification purpose. It deliberately has no scheduler, bulk lookup function, exporter or request collector.
- `validate_census_response`: refuses multiple matches, mismatched DOT ID, unexpected fields, email, phone, addresses, control-character names, invalid fleet counts, malformed documents, and non-UTC retrieval times. A missing fleet count stays **unknown** rather than zero. The record's retrieval time is not the originating census data vintage.

`legal_name` is retrieved solely as an ephemeral carrier-identity reference and may contain a sole proprietor's personal name. Do not export it, collect contact details, mine the census for sales leads, cache it to an ML dataset or release it to public users without a separate privacy/rights review. A USDOT number can identify a sole proprietor and requires proportionate handling.

The adapter returns `CarrierCensusReference` marked `PUBLIC_CENSUS_REGISTRATION_CONTEXT_NOT_OPERATING_AUTHORITY`. All four relevant readiness flags explicitly remain false: `historical_point_in_time_verified`, `operating_authority_verified`, `customer_invoice_verified`, and `recovery_fee_authorized`.

## Why this is not a training dataset or legally sufficient carrier verification

1. FMCSA Company Census includes active, inactive, and pending registrations. An entry or its absence is **not** reliable proof that a carrier is authorized to perform a particular shipment; verify operating authority, insurance and effective dates separately through official FMCSA channels.
2. Present-day snapshots cannot backfill historical carrier characteristics without authentic archived vintage evidence. Do not leak later information into earlier evaluations.
3. The dataset's catalog license is unresolved and only the fields necessary for one lookup are requested. **No raw carrier records are bundled** in this PR. Example names and responses in tests are invented and clearly mocked.
4. FMCSA carrier existence, corporate name or vehicle count cannot establish a customer's invoice, tariff rate, rate applicability, overcharge, accepted claim, funds received, or contingency fee.
5. This module performs **no automatic training** and provides no overcharge supervision labels. RETALLY's future supervised overcharge model requires permissioned customer invoices, governing rate contracts, independent reviewer labels and documented rights.

## Reproducible offline acceptance

```bash
PYTHONPATH=. python -m pytest -q freight/test_fmcsa_public_carrier.py
```

Tests substitute an in-memory HTTP opener. They exercise exact query shape, malicious/mismatched carrier numbers, duplicate matches, unexpected contact fields, false authority inferences, response size/encoding, service outages and data validation. They **never call FMCSA during CI**. Passing these tests proves local adapter safety invariants only, not official endpoint uptime, response-schema conformity, licensing clearance or current carrier authority.

This focused development branch targets main because the consolidated draft PR #329 has conflicting changes against main and no exact-head CI for its latest commits. It should not be merged, deployed or appended to #329 until both branches' relevant changes and tests are independently reconciled. No other RETALLY production flags, tasks, customer records, pricing or external systems are touched.
