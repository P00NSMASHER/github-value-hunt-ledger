# RETALLY Research Lab 14 — Mission 23: Census trucking peer benchmark validation

**Research-only draft · October 11, 2026 · stacked on Mission 22 PR #397.** Nothing here authorizes a production merge/deployment, external research contact, customer invoice collection, public recovery claim, or schedule change. The original fourteen laboratories and eighteen human/data-owner pilot gates remain in place.

## Why the source comparison matters

Mission 22 proved that two official Census 2022 Services Annual Survey (SAS) publications gave different **industry revenue estimates for 2017 NAICS 484122**, long-distance general-freight less-than-truckload trucking. The revised August 31, 2026 Census benchmark had **$65.688 billion**, versus the older publication's **$68.411 billion**, and matched the Census AIES historical 2022 series ($65.688461 billion) at nearest-$1-million precision.

Mission 23 independently asks: **Was LTL uniquely revised, or did the Economic Census benchmarking affect the surrounding truck transportation sector?**

The actual original Census 2022 SAS Table 2 source cells answer this:

| Industry (2017 NAICS) | Older employer-firm 2022 revenue ($m) | Aug 2026 revised 2022 revenue ($m) | Signed revision ($m) | Revision vs old |
| --- | ---: | ---: | ---: | ---: |
| Truck transportation, parent **484** | 445,509 | **423,271** | −22,238 | **−4.99%** |
| Long-distance general freight truckload **484121** | 183,482 | **172,717** | −10,765 | **−5.87%** |
| Long-distance general freight LTL **484122** | 68,411 | **65,688** | −2,723 | **−3.98%** |

All three industry revenue estimates were revised downward. The **percentage revision in LTL was smaller than the percentage revision in truckload or in all truck transportation**. It is therefore false to characterize the originally noticed LTL revenue discrepancy as a uniquely LTL-sized revision without showing the broader parent and sibling series.

These are different vintages of **the same Census SAS survey family**, not independently measured recoverable mistakes or distinct amounts that may be totaled as separate markets.

## Peer hierarchy and why naive totals fail

NAICS **484** already includes **484121** and **484122**, so adding all three doubles counts both child categories. The purely algebraic unrepresented remainder of the NAICS 484 employer-industry revenue after subtracting these two children is:

- Older source: **$193,616 million** = $445,509m − $183,482m − $68,411m.
- Revised source: **$184,866 million** = $423,271m − $172,717m − $65,688m.
- Signed revision of remainder: **−$8,750 million**.

The remainder is **NOT** itself one directly surveyed NAICS classification, nor a customer/shipper study, and it may include other truck transportation categories. This is a decomposition of public *survey revision magnitudes*, not a forecast or the serviceable market RETALLY could audit.

LTL's within-parent revenue share changed from **15.36%** in the older publication to **15.52%** in the revised publication, despite LTL's own revised revenue declining. **This is a denominator/revision effect, not evidence that LTL invoicing became more accurate or valuable.**

LTL's absolute revision ($2,723m) accounts for **12.24%** of the parent trucking industry's aggregate $22,238m revision, after recognizing overlap. This figure must not be relabeled as a recovery rate.

## The primary-source evidence

Original Census publisher files and fixed fingerprints are already authenticated by prior Lab 14 research and separately replayed in this mission:

- Revised SAS [Table2.xlsx](https://www2.census.gov/programs-surveys/sas/tables/time-series/sas-latest/Table2.xlsx), **128,635 bytes**, SHA-256 `cdfaaec9375064517da18e81623308fe4d62ae3ad102a232413ec2a6299310ac`. Worksheet `xl/worksheets/sheet1.xml`, 839 published rows. NAICS 484 occupies rows 42/43, NAICS 484121 rows 46/47, NAICS 484122 rows 48/49.
- Earlier SAS [sas-22.xlsx](https://www2.census.gov/programs-surveys/sas/tables/time-series/sas-latest/sas-22.xlsx), **515,901 bytes**, SHA-256 `4aa1efe9533fb3b16f32806af4f0b1bd5c72e92f2db024e559f891e03f0bc33a`. Worksheet `xl/worksheets/sheet2.xml`, 839 published rows. NAICS 484 occupies rows 44/45, 484121 rows 48/49, 484122 rows 50/51.

Both workbooks have the same Table 2 heading and **2022 revenue in millions of nominal USD**. Each NAICS category has **two tax-status rows**: all establishments and establishments subject to federal income tax. Those rows are **not independent samples** and are not counted twice.

The revised 2022 coefficient-of-variation cells for the selected three industries are published as raw `0`, whereas the earlier published 2022 CVs are **1.3%** (all trucking), **2.7%** (TL), **1.6%** (LTL). The published zero cannot be interpreted as zero statistical uncertainty, let alone evidence of zero invoice errors.

Publisher announcement: https://www.census.gov/data/tables/2022/econ/services/sas-naics.html

Benchmark methodological context: https://www.census.gov/programs-surveys/sas/technical-documentation/methodology/benchmarkprocess22.html

### AIES independently cross-checked at reporting precision

The original, separate Census AIES historical ZIP was verified in Mission 21. Its 2022 NAICS values are, in thousands of USD, **423,270,958** (484), **172,717,339** (484121), and **65,688,461** (484122). When expressed in millions, they differ from the SAS-revised values by **−$0.042m**, **+$0.339m**, and **+$0.461m**, respectively. Each rounds to the corresponding integer-million dollar benchmarked SAS table value. That validates *publication-precision consistency*, **not** independent survey sample agreement or a separately fielded 2022 AIES.

## Implementation

- `freight/research/SAS_TRUCKING_PEER_BENCHMARK_20261011.json`: closed dated source registry, two exact publisher ZIP checksums, six source industry/population entities with 12 original tax rows, NAICS parent/child scope and commercial limitations.
- `freight/research_sas_peer_benchmark.py`: deterministic Decimal arithmetic; strict manifest Git-blob identity and source checks; requires both original government XLSX digests and byte lengths, readable table title/units, all six NAICS × vintage row pairs; crosschecks prior M22 LTL truth; emits read-only `sas_peer_benchmark.json` and `sas_peer_benchmark.html`. No macro/formula execution.
- `freight/test_research_sas_peer_benchmark.py`: adversarial tampering of archive identity, industry keys, tax row duplication, units, CV metadata, noninteger figures, false future source dates, fictional commercial claims and network failures. The synthetic tests **do not pretend to authenticate publisher originals**.
- Existing research Lab 14 Python director and operator Control Center: a separate source-quality report, original fourteen-lab count, all existing negative probes and preflight holds preserved.
- `.github/workflows/retally-sas-peer-benchmark.yml`: PR/manual-only CI, standalone offline adversarial job and separate official Census source download/attestation job. No cron, production deploy, external outreach, raw Census workbook upload or customer data.

## Reproduce

From repository root (Python 3.11+):

```bash
PYTHONPATH=. python -m pytest -q freight/test_research_sas_peer_benchmark.py
PYTHONPATH=. python -m freight.research_sas_peer_benchmark --offline --as-of-date 2026-10-11 --out /tmp/retally-peer-offline
PYTHONPATH=. python -m freight.research_sas_peer_benchmark --fetch-publisher-workbooks --as-of-date 2026-10-11 --out /tmp/retally-peer-original
PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-peer-operator
```

The real research prerequisite for estimating invoicing errors or recoverable cash remains a **consented data-owner pilot** with source bills, shipment proof, effective customer-specific rate authorities, actual payment/refund evidence, two independent blinded reviewers, privacy/security/legal controls and selection denominators. The **18/18 external pilot signoffs remain unverified**. Source-backed market context cannot replace them.

**NO MERGE, DEPLOY, SCHEDULE CHANGE, CUSTOMER/PROSPECT CONTACT, PRIVATE DATA ACQUISITION, MONEY ACTION, OR PUBLIC RECOVERY CLAIM.**
