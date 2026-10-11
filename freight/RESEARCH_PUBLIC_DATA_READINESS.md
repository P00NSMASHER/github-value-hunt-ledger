# RETALLY Research Lab — Mission 9: Public Freight Data Provenance & Benchmark Readiness

**October 10, 2026 research snapshot. DRAFT / REVIEW ONLY**, stacked on unmerged Mission 8 PR #369. Extends existing Lab 14. No new research platform, live data ingest, purchase, scheduled task, outward contact, claims-to-carriers, production change or publication.

## What was actually checked

Seven specific public source URLs were researched. Government metadata pages, a third-party X12 210 illustration, the X12 organization's short definition, and a public GitHub repository *tree* were inspected; **no raw freight dataset, licensed third-party transaction sample or customer invoice was downloaded**. The registry makes that absence explicit rather than inventing byte checksums.

| Source | Publicly observed level | Actual approved use in this branch |
| --- | --- | --- |
| [2022 CFS PUMS dataset](https://www.census.gov/data/datasets/2022/econ/cfs/historical-datasets.html) | Public-use shipment-level sample released January 28, 2026; publisher lists about 680 MB | Catalogued metadata only; sampling/terms/integrity review outstanding |
| [FAF6 regional freight database](https://www.bts.gov/faf) | July 31, 2026 FAF6.0 2022 benchmark, public regional downloadable CSV; modeled tonnage and value | Catalogued metadata only; no freight audit revenue or invoices inferred |
| [Census CFS geographic API](https://www.census.gov/data/developers/data-sets/cfs/2022.html) | API documentation of CFS geographic/statistical series; key indicated | Catalogued metadata only; no requests or credentials |
| [2022 CFS final tables](https://www.census.gov/data/tables/2022/econ/cfs/aff-2022.html) | Official downloadable survey tables and citation instructions | Catalogued metadata only; not a separate independent market from CFS/FAF |
| [EdiFabric's X12 210 illustration](https://www.edifabric.com/docs/transactions/x12-210.html) | Public webpage presenting an EDI 210 freight invoice example | Third-party sample rights not established, no copies in repository |
| [freighttrust/X12-Examples](https://github.com/freighttrust/X12-Examples) | Public GitHub root and T210 example directory. No root LICENSE/LICENCE file observed on inspection | Discovery only; code/data reuse and upstream authorship remain unresolved |
| [X12's official 210 description](https://x12.org/node/4210) | Short official transaction-set description | Standards-research discovery only, not licensed full specification |

**Careful distinction:** A public-use CFS sample may legitimately support transport-related statistical research under its published terms, after methodology/rights review. It contains shipment characteristics rather than a verified comparison of actual carrier bills with controlling customer contract, dated tariff, paid amount and independently adjudicated overcharge. Nothing here permits claims about real RETALLY audit precision, actual cash recovery, addressable recovery fees or competitor inferiority.

## Source-family anti-double-counting

CFS microdata, Census CFS tables/API and FAF6 have methodological dependencies. FAF incorporates the CFS. The four public federal leads are marked as `CFS_FAF_2022_INTERDEPENDENT` so a future analyst cannot add them together as unrelated freight markets or pretend they independently confirm the same estimate.

The EdiFabric 210 page and the freighttrust X12-Examples repository also may share source lineage; merely being posted on separate domains does not establish independent test observations, sample author permission or original transaction data.

## Implemented

- `freight/research/PUBLIC_FREIGHT_DATA_CANDIDATES_20261010.json`: seven dated, exact-URL source records, release dates when available, observed grain, availability, uncertain rights, lineage, potential study link, limitations and the next manual verification step.
- `freight/research_data_readiness.py`: deterministic, fail-closed metadata validator and rights/provenance review queue. Rejects source impersonation, forged file digests when no bytes were fetched, fabricated licenses or customer ground truth, invalid URLs/dates, new private/customer fields, missing records and misleading granularities.
- `freight/test_research_data_readiness.py`: adversarial fixtures checking source identity, rights flags, sampling grain, duplicate/unknown IDs, source lineage, market/rate distinction, malformed metadata and secure HTML escaping.
- Existing Lab 14 negative probe, read-only Research Intelligence CI and operator Control Center include this new source review output. Prior historical findings remain OPEN_UNVERIFIED; no new lab is created.

## Status/acceptance model

Every candidate is `PUBLIC_METADATA_CATALOGUED_NOT_ADMITTED`. To admit a dataset later for a specific use, a human-governed future change must establish **all** of the following independently:
1. Verified original publisher, version, exact permitted use, license/terms and reuse/redistribution bounds, including third-party contents.
2. Explicit permissioned data acquisition, source file byte checksum, legitimate storage/retention and independently inspected schema/grain.
3. Privacy and confidentiality clearance with removal/redaction of any personal or customer data and legally acceptable provenance.
4. An independent ground-truth oracle if the target is actual invoice accuracy: *bill + governing rate/contract + shipment context + payment/credit record + adjudicator evidence*.
5. A preregistered real test protocol, separate security/commercial/legal authorization and independently reviewable denominators, missingness, exclusions and uncertainty.

**None of these admission conditions has been satisfied in this Mission.** A synthetic invoice or an EDI sample can eventually exercise a parser, but it cannot demonstrate a recoverable real overcharge without independent original evidence.

## Execute offline

From repository root, Python 3.11+:

```bash
PYTHONPATH=. python -m pytest -q freight/test_research_data_readiness.py
PYTHONPATH=. python -m freight.research_data_readiness --as-of-date 2026-10-10 --out /tmp/retally-data-rights-review
# View freight_data_readiness.html and freight_data_readiness.json
PYTHONPATH=. python -m freight.lab_phase4_control_center --out /tmp/retally-operator
```

GitHub CI does not fetch network resources, authorize a license, run Census API requests, store new raw data, or upload public/customer-facing benchmarks. SHA-256 receipts validate in-repository serialization only, not publisher truth. The operator HTML links directly to original source pages for later authorized review; these are reference links, not signed licenses or automatic downloads.

## Next high-value test after independent review

The **2022 CFS PUMS** is the most promising authentic shipment-characteristic data lead for prospective segmentation and data-shape QA. Its 680 MB scale and survey weighting/suppression require deliberate sampling and methodology review. The **FAF6 CSV** is a smaller source for regional flow summaries, not invoice-level errors. For RETALLY's most important task—second-look invoice error accuracy—**an independently authorized, rights-cleared reference corpus remains missing**. A buyer-controlled pilot will still need separate approval and security/data-rights review.

No production merge, external contact or scheduling is authorized by this branch.
