# RETALLY Lab 14 — Original SEC-filed transportation contracts with genuinely different fuel-index rules
**18 October 2026 · Source-only draft · No real customer documents · No customer transaction**

## What was inspected

Two **original exhibits published by the U.S. Securities and Exchange Commission**, containing recognizable shipper/carrier terms, signed or filed contract language, rate definitions and different fuel-surcharge authority:

| Original EDGAR agreement | Historical effective date | Rate authority | Fuel price source | Measurement |
|---|---|---|---|---|
| [NEDAK Ethanol / Western Oil Trans, SEC Exhibit 10.1](https://www.sec.gov/Archives/edgar/data/1337226/000092290707000474/form8kexh101_072507.htm) | July 19, 2007 | Exhibit A, Atkinson → O'Neill ethanol storage | **Local** nonaffiliated #2 diesel seller in O'Neill, Nebraska | USD per gallon unloaded |
| [Swift & Company / Load Source Logistics, SEC Exhibit 10.8](https://www.sec.gov/Archives/edgar/data/757563/000129707705000148/mcagree.htm) | February 28, 2005 | Appendix D fuel; lane-rate Appendices J → I → K in priority order | **U.S. national DOE diesel index**, as of stated Monday/Tuesday determination date | Cents per mile |

**Source custody:** SEC publication confirms the agreement/exhibit text was publicly filed. It does NOT establish that the historical agreements remain in force, that all amendments and lane appendices have been supplied, that the Swift form has a separately authenticated signature, or that any original invoice, delivery receipt or payment remittance exists. The original EDGAR HTML source bytes and signatures have not independently been hashed/validated as of this receipt.

## 2007 NEDAK public negotiated rate is NOT a national diesel-index surcharge

The filed Exhibit A gives a base price of **$0.01299 per gallon of ethanol unloaded** between **Atkinson Ethanol Storage Site and O'Neill Ethanol Storage Site**, and surcharge increments per gallon unloaded. The text states the fuel price comes from an independent O'Neill, Nebraska #2 diesel seller (such as Cubby's), established on the 15th and 30th billing dates. It is not the 2026 federal EIA national average, nor a percentage applied to a hypothetical shipment's dollar value.

Only these original published **price → fuel-surcharge** pairs are frozen:

| Local retail diesel price per gallon | Surcharge per ethanol gallon unloaded |
|---:|---:|
| $2.499 | $0 |
| $2.749 | $0.0003 |
| $2.999 | $0.0006 |
| $3.249 | $0.0009 |
| $3.499 | $0.0012 |
| $3.749 | $0.0015 |
| $3.999 | $0.0018 |

**Illustrative arithmetic only:** Given an *invented* 1,000-gallon hypothetical tender and *invented* $2.749 local diesel price matching one published example row, the unamended source rate yields $12.99 base + $0.30 fuel = **$13.29**. No such historical tender, pump quotation, rate confirmation, invoice or paid amount was seen. The test is a source-bound arithmetic demonstration, **not** a $13.29 historical invoice.

Rates for **unlisted fuel prices**, other lanes, other shipper/carrier parties, 2026 retail prices and contracts amended or terminated after 2007 must not be silently interpolated/extrapolated from this historical excerpt. Only a properly authorized and current customer agreement can establish today's applicable rates.

## 2005 Swift public contract form is based on a different source and different unit

The separately filed Swift agreement's Appendix D uses the **national Department of Energy average diesel index**, with a Monday determination date (Tuesday after a federal holiday) and applicability to shipments beginning the following Monday. Selected original explicitly published tiers include **$1.250–$1.299 = 1 cent per mile** and **$1.500–$1.549 = 6 cents per mile**. These are **fuel line items only**, not full shipment charges.

For an *invented* 150-mile journey and *invented* DOE index **$1.275**, the original tier indicates a **$1.50 hypothetical fuel-only** amount. Base linehaul, mileage authority, detention, credits and contract amendments are NOT available; RETALLY therefore cannot produce an authoritative final freight charge. The contract requires the carrier to show a fuel surcharge as a distinct invoice line item; a shipper is not obligated by this excerpt to create omitted fuel charges itself.

The filed Swift document has a shipper/carrier form with fields/appendices; current binding execution status, full lane-rate appendices and signature authenticity are independently **unverified**. The original source is stronger than a hypothetical rate table, but cannot replace a real authorized 2026 customer contract.

## Preventing wrong contract selection and false positives

Offline validator `freight/public_sec_contract_authority_v1.py`, its source facts in `freight/fixtures/public_sec_2005_2007_original_carrier_rate_contracts.json`, and independent adversarial tests verify:

- Exact original SEC URLs, historical party names, effective dates and source-specific fuel authority.
- Local-nebraska gallons pricing **cannot** accept national DOE/EIA/UPS/FedEx pricing, and vice versa.
- No swaps between *gallons unloaded* and *miles*, no missing applicable lane rates represented as a full invoice.
- No fuel calculation outside the **explicitly pinned original pricing rows** without a reviewed larger source table, no automatic interpolation, and no fictitious source amount as current.
- No claimed actual source signature, original invoice, customer money received, current contract, overpayment or recovery.
- Exact Decimal-based educational examples only; no bank, tariff, customer portal, carrier inquiry, public money-claim promotion or protected-main mutation.

Run the offline source tests:

```bash
PYTHONPATH=. python -m unittest -v freight.test_public_sec_contract_authority_v1
PYTHONPATH=. python -m freight.public_sec_contract_authority_v1
```

**Commercial evidence ladder:** An original historical filed contract adds a fourth, stronger class of authority than a generic carrier surcharge schedule—but **actual applicability** still requires the customer's current executed contract and amendments, bill of lading/EDI shipment details, exact original invoice, index observation on the governing date, payment evidence, independent source review and a documented recovery decision. None is present here.

**Research-only**: 26 historical findings remain OPEN_UNVERIFIED; 18 independent human first-customer gates unmet. Actual original RETALLY customer invoices **0**, recoveries **0**. Live RETALLY intake, vendor payments, carrier outreach, scheduled monitoring, and production billing code remain unchanged.
