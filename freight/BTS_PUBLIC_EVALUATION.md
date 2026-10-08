# RETALLY: traceable real-world freight data for importer evaluation

**October 8, 2026. Review only. No new machine-learning weights, customer
invoices, contracts, claims, posted credits or billable fee records.**

## 1. What was actually admitted

- Source format and publisher: **Bureau of Transportation Statistics (BTS),
  T-100 Domestic Segment, U.S. carriers**, publicly reported flight-segment
  freight and mail traffic, not a motor-carrier LTL freight bill.
- Upstream source-field dictionary:
  https://www.transtats.bts.gov/Fields.asp?gnoyr_VQ=GEE
  (`Freight` = non-stop segment freight transported, **pounds**;
  `Mail` likewise pounds; `Distance` miles).
- Historical GitHub mirror:
  https://github.com/dannguyen/bts-transstats-t100-domestic-demo
  path `data/sample-T100D-segment-data.csv`, original Git blob
  `359f319355edbef944ffd103ed16c7a5877131c8`.
- Curated, minimal local projection:
  `freight/data/bts_t100_airfreight_observed_subset_2013.csv` at Git blob
  `90de471b78ad61fced14d4436b33f392b533ee83`.
- Exactly **20 source-row-linked records** from a 197-record GitHub
  sample: four carriers (codes 2E, 2F, 4W and 7H), five rows each,
  including 12 records with nonzero *reported* air freight and eight with
  zero air freight. They are labeled only by the observed numeric field.
  No personal contact details or restricted carrier-identity attributes
  have been copied.
- The CSV's year/month fields report **January 2013**. The repository
  README uses November 2013 in its download instructions. That discrepancy
  has **not** been resolved against the original publisher at the row level.
  We retain the actual row's year/month, explicitly identifying the
  GitHub mirror rather than claiming an independent official BTS row
  verification.
- The repository includes an MIT code license; do **not** assume that
  alone establishes rights to bulk redistribute the original mirrored
  dataset or train/commercialize learned weights from it. This project
  includes only a bounded factual projection, with attribution, for
  internal technical evaluation; confirm terms before wider reuse.

## 2. What it tests

`freight.bts_public_evaluation.load_observations` validates the pinned
Git blob identity, explicit schema, source row identity, reported numeric
precision, carrier/airport formats, service class, required positive/zero
balance and year/month vintage. It preserves mail separate from freight
and rejects label changes that conflict with observed freight weight.

`carrier_disjoint_eval` supplies 15 training-side **parser examples**
from carriers 2E/2F/4W and five **evaluation-side** examples from 7H;
the carrier codes do not overlap. This is a tiny one-month fixture.
It establishes no statistical generalization, fraud-classifier quality,
precision/recall for overcharges, safety rating, or commercial recovery
effectiveness. No model is fitted or automatically retrained.

Run the existing contract CI or directly:

```bash
PYTHONPATH=. python -m pytest -q freight/test_bts_public_evaluation.py
```

## 3. Other promising source classes, with explicit acceptance limits

| Discovered GitHub repository | Original authority | Permitted initial role | Reason not used to claim a customer invoice |
| --- | --- | --- | --- |
| `gregchedwick/carrier-survival` (MIT code; source code reviewed) | Federal Motor Carrier Safety Administration public Company Census (`az4n-8mr2`), authority-history (`9mw4-x3tu`), revocation (`sa6p-acbp`) and crash (`aayw-vxb3`) data | Source discovery, field mapping, temporal-leakage and negative-control design | Modeled carrier continuity is not an audited freight invoice or a binding carrier authority record |
| `Helban/fmcsa-carrier-lead-scraper` | FMCSA census `az4n-8mr2` | Examples of census retrieval and carrier identity deduplication; **do not scrape contacts** | Public registration fields are time-lagged, may include personal contacts, and do not prove active operating authority |
| `LBNL-UCB-STI/SynthFirm` | U.S. Department of Energy lab research using real inputs to generate synthetic economic agents and freight movements | Research into realistic schema variability | Generated firms/flows are synthetic; provenance, private input rights and redistribution controls must be independently reviewed |
| `asu-trans-ai-lab/RAS2026-PSC` | INFORMS/ASU railroad competition, transformed FAF/OSM inputs | Research and stress-test ideas only | Competition demand and network parameters are transformed and explicitly **not** operational rail data; code MIT license excludes datasets |
| `indy-viberr/stowaway` | Authors' invented fraud scenarios | **Synthetic negative-control only** | Their invoice set is expressly synthetic; planted fraud labels are not real-world ground truth |

Primary authority references:
- https://www.fmcsa.dot.gov/registration/fmcsa-data-dissemination-program
- https://data.transportation.gov/d/az4n-8mr2
- https://www.bts.gov/faf
- https://www.transtats.bts.gov/
- https://www.eia.gov/petroleum/gasdiesel/

FMCSA says its Company Census data is refreshed daily from roughly
24-hour-old records. Its public portal metadata currently lists a
**license-not-resolved** link. No raw full-country contact list,
historical carrier status claim, or production carrier-risk model is
admitted here.

## 4. Non-negotiable distinction

The observed target `freight_present` only means the source reports
a positive airfreight weight. It **does not mean freight was
correctly billed, underbilled, overbilled, recoverable or paid**.

RETALLY's proposed $0-upfront review requires actual, permissioned
buyer invoices, governing dated contracts and authority sources,
independent reviewer acceptance, incumbent suppression, separately
authorized carrier action, customer-ledger-confirmed settlement and
only then a contract-specific fee. The observation fixture never
supplies any of those facts and is not connected to the recovery
engine, external-action workflow or billing.

**Status:** source-controlled internal parser and provenance QA only.
PR #329 remains an unmerged review candidate and diverges from current
main on separate inquiry files. No production deployment, API data
collection scheduler, customer contact or billable action is authorized.
