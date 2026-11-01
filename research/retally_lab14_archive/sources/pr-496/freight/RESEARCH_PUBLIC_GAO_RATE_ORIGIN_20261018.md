# RETALLY Lab 14 — Original GAO freight line-item and bill-of-lading correction replay

**Two real government administrative decision texts • source-only • 18 October 2026**

## Strongest new source-level math: B-160344, GAO July 18, 1967

First-party original [GAO decision B-160344](https://www.gao.gov/products/b-160344)
identifies a specific government bill of lading **B-5378637**, a motor-carrier
bill **141**, one shipment of **1,485 pounds** on December 19, 1962,
the money paid in March 1963, two distinct National Motor Freight
Classification items and published historical rates, and an amount that
GAO says was collected by federal setoff after carrier refusal.

| Source finding | GAO figure | Independent arithmetic |
|---|---:|---|
| Original Class 400, NMFC 14440, 1,485 pounds at **$18.53/cwt** | **$275.17 paid** | 14.85 × $18.53 = $275.1705 → $275.17 |
| Accepted Class 200, NMFC 12400, 1,485 pounds at **$9.38/cwt** | **$139.29 allowable** | 14.85 × $9.38 = $139.293 → $139.29 |
| Difference | **$135.88 assessed and deducted Dec 1965** | $275.17 − $139.29 = **$135.88** |

Original document correction chronology is material: an Air Force DD Form 1352
in **February 1964** changed the description after the carrier was **paid
March 1963**. A contemporaneous Air Force technical statement described the
item's primary use as an aircraft nose/airframe, not a ground radar antenna
enclosure. The GAO decision cites the correction and classification
interpretation. **The public decision is not an independent signed copy of the
original Government Bill of Lading, DD Form 1352, or full historical NMFC
tariff page.** Those source gaps remain open. Historical government law does
not automatically authorize private 2026 carrier adjustments.

## Essential false-positive: B-186603, GAO December 22, 1976

The [original GAO decision B-186603](https://www.gao.gov/products/b-186603)
examines **two different government bills of lading**. They must never
be summed or silently collapsed into the same customer or shipment.

**F-7349731 (40 chairs, 2,800 pounds):** The government paid the carrier
**$398.16**. Its original BOL described shipment origin as Washington, D.C.
and GSA deducted **$133.28** as an alleged overcharge. The manufacturer
and procurement facts independently developed by GSA contradicted that
origin: Washington was the **ordering office**, whereas the actual
factory shipment originated at **Canton, Mississippi**. GAO found
the original BOL location rebutted and said the carrier's **$133.28**
claim should be allowed **if otherwise correct**. Thus a deduction
already recorded by the government was **not necessarily a valid permanently
retained recovery**. No bank record proving that a carrier repayment
actually cleared has been independently inspected.

**D-8271398 (1,624-pound blankets):** A separate government shipment
had a **$57.65** deduction and the government later issued a
**$22.90 certificate of settlement** to the carrier. The certificate
is not proof of cash remittance. Neither amount belongs in the
chair-shipment recoverable-value calculation, and the certificate is
not a second documented actual payment.

This is a direct, original first-party source demonstration of:
- Decimal-accurate charge recomputation with explicit quantity,
  dated historical tariff rate and commodity classification evidence.
- Source-document precedence, especially when a later corrected
  document legitimately contradicts an earlier bill of lading.
- Reversal/negative-control guardrails against falsely claiming
  disputed setoffs as permanently recovered money.
- Distinct-bill-of-lading scope and evidence provenance. No invented
  private customer accounts, contracts or shipment correspondence.

## Evidence and test boundaries

Data: `freight/fixtures/public_gao_rate_reclassification_and_origin_rebuttal_20261018.json`.
Validator: `freight/public_gao_rating_lineitem_original_v1.py`.
Adversarial tests: `freight/test_public_gao_rating_lineitem_original_v1.py`.

The fixed facts are tied to exact GAO publisher URLs, original decision
dates, document references, known billed amounts, historical rate and
classification IDs. Payment arithmetic is computed from integer-cents
per hundredweight with Python `Decimal` half-up cent rounding.
The validator rejects tampered rates/weights, re-dating a correction to
pre-payment, merging independent bills, falsely accepting disputed
overcharges, forged bank confirmations or first-party RETALLY recoveries.

**Nothing is a real RETALLY customer invoice:** government report excerpts
are genuine original first-party publications but underlying 1960s and
1970s bill-of-lading *images*, contemporaneous tariff leaflets, bank
statements and private contracts were not obtained.

These two **separate diagnostic decisions and three government GBL references**
must not inflate the earlier **seven GAO government collection case tally**,
the original **307 public freight observation rows** or RETALLY's
recovery totals. The 26 historical open findings and 18 human first-customer
gates are unaffected. Research remains a DRAFT and is not deployed.
