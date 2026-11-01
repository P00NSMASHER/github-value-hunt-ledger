# Brain-to-RETALLY measured reviewer-code pilot

Status: **DRAFT / NOT DEPLOYED / NO CUSTOMER OUTCOME**.
This extends existing PR #343, not another engine or scheduled worker.

## Delivered in this candidate

`freight.reviewer_cockpit.build_invoice_review_queue(population, charges)`
connects the existing line-level detector and Brain-inspired cross-shipment
invoice-reference detector to RETALLY's existing `ReviewQueue`, `ReviewCase`,
`record_disposition` and `export_disposition` primitives. It requires a
recomputed matching frozen-population manifest before generating any cases.
No user-interface, ingestion-route, settlement or live customer integration is
claimed. The adapter must be explicitly called by a separately reviewed consumer.

Every case carries original candidate/population/batch/source proof references,
required evidence, `UNSCORED_REVIEW_ONLY` and `NO_FINANCIAL_AUTHORITY` blockers.
All monetary/scoring fields are zero placeholders, not probability, low-risk,
savings or recovery claims. Duplicate invoice numbers are not proof of overpayment.
The adapter does no network I/O, writes, payments, auto-dispositions or automatic
Brain feedback. Existing cockpit behavior and both detectors remain unchanged.

## Reproduce

```bash
python -m unittest -v freight.test_duplicate_charge_review freight.test_invoice_reference_review freight.test_brain_review_cockpit
python -m freight.brain_review_measurement
```

The measurement executes the actual first-party methods on the same frozen inputs,
with actual module SHA-256, per-case hashes and single-sample timings. The baseline
is the pre-existing line-level detector, not a deliberately weakened algorithm.
The code base is PR #343 head `9f68a2a0d22abd671ce7be353506a8b8cf9e5a52`.
At readback, `contracts.py`, `finding_factory.py` and original `reviewer_cockpit.py`
were unchanged between that branch and RETALLY main
`7c469d17a7a037e0a947a4696c4dafd0a2bc5946`; main lacks the separately proposed
128-line invoice-reference detector. This is not full current-main release proof.

## Observed local rehearsal (Python 3.12.10)

- Original selected tests: 18 passed.
- RED: 10 new integration tests failed for the missing adapter (13 failing
  assertions including subtests). Two additional manifest-forgery tests failed
  before manifest verification was added. An intermediate shell quoting error
  prevented applying that repair; it did not alter repository source.
- GREEN: all 30 selected tests passed after the final implementation.
- Five designed review scenarios: baseline flagged 2, combined queue flagged 5.
- Five nonmatching controls: both flagged 0.
- Two known-benign consolidation/rebill scenarios: baseline flagged 0, combined
  queue flagged BOTH. This additional review burden is part of the result.
- Validated recovery stays zero. Human time saved, revenue and customer outcomes
  are NOT MEASURED. Single-sample runtime is not a speedup claim.

All twelve cases are synthetic and developer-labeled, not independently adjudicated.
The benign cases deliberately have the same detector inputs as suspicious cases:
identity alone cannot distinguish them. No amount of this rehearsal proves a
real-world false-positive rate, recovered funds or commercially useful adoption.

## Release and learning boundaries

Required full repository checks, independent consumer review and a separately
authorized release remain outstanding; local tests are not substitutes.
Before calling this a delivered project improvement, wire the reviewed adapter
into the intended consumer, verify staging behavior on the then-current exact
source, and obtain authorized real-use evidence. Count technical test improvement,
deployment and measured operational benefit separately. Do not label this as
`INTEGRATED`, `USEFUL`, verified revenue or a live learning outcome in Brain.
No production source/state, task schedules, credentials, rights, financial
controls or customer communications change as a consequence of this draft.
