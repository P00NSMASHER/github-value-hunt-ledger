# RETALLY — Sungold's September 2022 shipment: historically effective detention rate sources

**Research time:** October 19, 2026. **Decision:** Two additional original CMA CGM/ANL 2022 DETENTION rate publications discovered. Their original URLs are verified by the public search index, but **new independent PDF byte ingestion attempts were held**. No evidence establishes the rate controlling BOL AMC1912992. No original Sungold trial exhibit or customer bank settlement acquired.

## New original carrier-published 2022 detention sources — **not** 2024 retroactive substitutes

1. **CMA CGM India January 20 2022 Export Container Detention Charges — client advisory CCAI-009-040122.**
   Original [issued carrier PDF](https://www.cma-cgm.com/assets/public/pdf/Export%20Detention%20Charges%20-%2020%20Jan%202022.pdf). Original indexed text says *Brand CMA CGM, ANL — all trades*, effective January 20, 2022, two equipment classes, free days and daily tariff tiers. This has the **correct service type (equipment DETENTION)**, as opposed to the separately verified demurrage-only PDF from the prior research run.
2. **CMA CGM India official archive of the standard EXPORT—ALL PLACES detention tariff.**
   Exact [original carrier PDF](https://www.cma-cgm.com/assets/public/documents/DD_Tarifs_IN_2020-04-01%2028-7-23_1.pdf). The **PDF's own page 11 (zero-index 10)** says **EFFECTIVE DATE: 20-JAN-2022**, **DETENTION** (not demurrage), 10 free calendar days, standard container 20/40/45ft tiers in **USD/day**. The filename has another date embedded in its basename; **use the source document's effective-date declaration rather than guessing validity from the filename**. The original PDF is independently indexed as 13 pages, but the original bytes were unavailable to the current runner.
3. **CMA CGM-hosted ANL India January 20, 2022 D&D tariffs — export all except ICD.**
   [Original tariff bundle PDF](https://www.cma-cgm.com/assets/public/dnd-documents/anl/DD_Tarifs_IN_2022-01-20%2021012022.pdf), nine indexed pages. PDF's **page 8 (zero-index 7)** lists export detention and demurrage in separate columns with the same standard rates, effective January 20, 2022. **ANL-specific repository path is an added brand/applicability hold:** hosting by CMA CGM does not independently prove the exact carrier and contract for Sungold.

## Exact published standard detention price tiers

| Container type | Free period | Days 11–17 | Days 18–24 | Day 25+ |
| --- | --- | --- | --- | --- |
| **Standard 20-foot** | 10 calendar days | **USD 35/day** | **USD 65/day** | **USD 82/day** |
| **Standard 40/45-foot** | 10 calendar days | **USD 70/day** | **USD 130/day** | **USD 164/day** |
| **Special 20-foot** | 10 calendar days | **USD 55/day** | **USD 79/day** | **USD 112/day** |
| **Special 40/45-foot** | 10 calendar days | **USD 110/day** | **USD 158/day** | **USD 224/day** |

The PDF also differentiates reefer containers: 7 free days and distinct brackets (days 8–14, 15–21, 22+). Do not substitute the standard rates without exact equipment type.

**Crucial:** This is **general 2022 carrier-published USD/day tariff context**, not the established controlling rate for the five rice containers. The court's original invoice **₹689,695.85**, credit note **₹619,339.26**, and court-awarded unpaid pass-through to shipper are **INR/paise**. Without original booking/invoice exhibit images, equipment size/type, pickup/return event dates, free-time adjustment, customer-specific agreement, USD/INR FX rate and IGST basis, there is **no verifiable invoice recalculation**. The credit arose from a government export-restriction exemption, not an independently proved false application of the schedule.

## Read-only original-PDF byte ingestion and actual status

Code: `freight/research/authorized_original_case_fetch.py` pins both additional full-document original URLs, requires HTTPS exact host/path, checks %PDF magic/EOF and SHA-256, and calls source-page text corroboration without logging original third-party text or PDF bytes.

- [Targeted independent public-byte verification GitHub Actions run](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39317171690): ran successfully with **45 passing synthetic source tests**, but **both newly targeted original PDF requests returned `ORIGINAL_SOURCE_UNAVAILABLE`**. No newly verified SHA-256 or original PDF bytes. **A green workflow is not a successful ingestion of unavailable sources.**
- Prior signed source evidence: [CMA CGM general export DEMURRAGE-only PDF](https://www.cma-cgm.com/assets/public/documents/Export%20Demurrage%20Charges%20-%2020%20Jan%202022_0.pdf), 2 pages, 177,395 bytes, SHA-256 `d9d292679d9ea3e486ecbb0d3eb1dcf4c781ddf51176d467f56ea13474030701`, cannot supply the missing *detention* rate authority.
- [Repository release run](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39316768424) passed **201 freight tests** including rate-page checks. These tests are synthetic only; they do not change commercial freight acceptance.
- PAAM-L044 remote computer appeared offline at the local source-inspection attempt; no private device intake happened. No login bypass, court request, carrier/customer contact, expenses or source publication.

## Original court exhibit / bank settlement check

**Court case:** Delhi West District Commercial Suit 32/2026, CNR DLWT-01-014066-2025, BOL AMC1912992. Source transcript: [September 17, 2026 judgment](https://indiankanoon.org/doc/161666818/).

| Required original record | Court-document locator | Actual bytes obtained? |
| --- | --- | --- |
| Carrier three-page booking confirmation | Ex.PW2/1 | **NO** |
| Carrier original Oct 10, 2022 detention invoice | Ex.PW2/2 (also Ex.PW1/9) | **NO** |
| Sungold original ICICI Bank paid statement | Ex.PW1/12 | **NO** |
| Carrier original Dec 8, 2022 ₹619,339.26 credit note to intermediary | Ex.PW2/3 / Ex.PW1/17 | **NO** |
| Carrier rate schedule official 2022 DETENTION | New original publisher URLs above | **Indexed, original bytes not newly downloaded** |
| **Chevisance→Sungold separate actually CLEARED bank repayment after Sep 17, 2026 judgment** | No original bank transaction/credit reference identified | **NO** |

The Delhi court judgment found **credit to Chevisance** and ordered pass-through to Sungold; it does **not** certify final receipt by Sungold. Public case-index and exact legal searches yield judgment and registration entry, not an original postjudgment payment receipt or supplementary execution/satisfaction record. The original trial exhibits may be nonpublic court-file documents; **availability cannot be assumed**. A judicial award remains an **uncollected outcome** until independently cleared.

### Strict data admission

`case_4_document_complete=false`
`original_trial_exhibits_ingested=false`
`shipment_controlling_rate_verified=false`
`customer_refund_bank_cleared=false`
`verified_RETALLY_recovery=0`

The original URLs and exact holds are preserved in isolated research PR #487, not merged or advertised as proof of RETALLY freight recovery success. The user says they have permission to download; **commercial redistribution of private bank/carrier exhibits still requires independently confirmed source rights**.

**Best possible next zero-contact path:** an actual openly downloadable original Delhi exhibit file with known provenance (not merely the judgment), official carrier-rated original 2022 tariff bytes, and a later public satisfaction/credit event matching Sungold as bank beneficiary. No such complete chain has been publicly located by this research.
