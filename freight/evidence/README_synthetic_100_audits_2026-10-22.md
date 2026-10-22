# RETALLY — source-pinned 100-audit synthetic laboratory

**Date:** 2026-10-22  
**Classification:** `SYNTHETIC_ONLY` / research QA. **Not real-customer freight-detection accuracy, a pilot, a recovery, a payment, or commercial acceptance.**

## Evidence and scope

- Full-lifecycle source: `freight/synthetic_rehearsal.py` at immutable RETALLY commit `7a43c19f0b298285a28b46ff1fd0f3d4349f4344`.
- Audit fault-injection source: `freight/audit_workflow.py` at the same head.
- The lab benchmark reference `freight/REAL_DOCUMENT_LAB_RESULTS_2026-10-20.md` was read but was not re-executed or expanded. Neither original freight PDFs nor NHS CSV source bytes were re-fetched in this run.
- The real-document laboratory's 110 freight invoice faces have zero eligible independently adjudicated binary freight-error truth labels. The Pennine Care 273 unique same-source declarations are **general accounting reconciliation**, not freight-error detection.
- The original **synthetic** three-invoice workflow fixture was expanded deterministically into 100 isolated runs using distinct fictional invoice/shipment identifiers and 15 permitted service dates. Economic shape, artificial review/claim approval, and fictional settlement/reversal amounts were intentionally held fixed. This is a repeatability/stress exercise, **not 100 economically independent truth cases**.
- In each cycle a second audit-only fault-injection case varied one of 13 failure/decision surfaces, including positive/exact/under billing, verified versus missing/unverified rate authority, currency mismatch, fractional/negative/Unicode amount inputs, date defects, invoice-identity conflicts, incomplete rates, and duplicate charge evidence. No customer contracts or real payments were used.

## Measured (isolated PAAM-L044 run)

| Scope | Observed |
|---|---:|
| Full synthetic audit-to-report lifecycles | **100/100 successful** |
| Generated synthetic invoice identities | 300 |
| Distinct complete audit manifest hashes | 100 |
| Distinct synthetic settlement snapshot hashes | 100 |
| Additional changed-input audit probes | **100/100 expected outcomes** |
| Unexpected failures | **0** |
| Actual carrier actions, real customers, verified recoveries | Not performed or verified |

Each full trial called native audited code for ingestion/freeze, rate authority, Finding Factory, review routing, fictional buyer decision, claim creation, generated carrier-action payload/authorization **without external execution**, fictional credit-memo and return accounting in a temporary SQLite store, report rebuilding, and old-report invalidation. The audit ZIP manifest was verified in each trial.

The 13 fault-injection classes returned `CLEAN`, `REVIEW_REQUIRED`, or fail-closed `BLOCKED` as expected. These are code-adjacent synthetic expectations, not estimates of real true-positive/false-positive rates.

## Reproducibility and provenance

- Source head: `7a43c19f0b298285a28b46ff1fd0f3d4349f4344`.
- Base synthetic invoice CSV SHA-256: `23114c2adda7ff5fdae58bfea8177727a500d515bc4248195ef43c900bd5a9cd`.
- Base synthetic settlement CSV SHA-256: `dc66f0734037bdc23371043f9e93d18054b586195540f75f2b5e6b9918775949`.
- Laboratory summary Markdown SHA-256: `2dcd8a53a89174e5a199af4f90ffce8927a7b673914b7e16f6c30a55022c2e5a`.
- Phase 3 synthetic gold fixture SHA-256: `e53404f4c881e61fe01959bb5cdba972519ff39247d58a80392ab59593aee78e`.
- Canonical ordered 100-case receipt list SHA-256: `fee9685201216133cdbbb2d664a65afbee6108eee7a52f205ae475cc73adefdd`.
- As-executed local report SHA-256: `aa07e42d86da94d3d3af1beca3a15c4d750d70e92da5c93d3d1f7fe4d33809e2`.
- As-executed runner local SHA-256: `1f3023fbaa9d9a9fd1c356132984d542bc3afc2972dd0e299df6812d645b8c6d`.

The report `synthetic_100_audits_2026-10-22.json` contains 100 case-level synthetic fixture and audit/result/snapshot fingerprints, one controlled-probe decision per case, explicit limitations, and zero raw invoice/customer data.

### Re-run the exact tested source

The included `retally_synthetic_100_runner_as_executed.py` is the *local research script as used*, with an intentional exact-`HEAD` assertion, so execute it against the pinned original source, not against this evidence-only branch commit. In a separate clean, nonproduction clone of this evidence branch, copy the runner into the repository root as `_retally_simulate_100.py` before detaching to `7a43c19f0b298285a28b46ff1fd0f3d4349f4344`; then run `python _retally_simulate_100.py` from that repository root. The only generated output is an untracked synthetic JSON summary; no external actions or original-document downloads are part of this script.

**Verification classification:** Python run and independent report-integrity readback **passed locally**; Git branch is a **sanitized evidence checkpoint only**. **Not** GitHub CI-verified, integrated to `main`, independently adjudicated, deployed, or production-accepted. Product-engineering files, release rules, financial/customer gates, and automated task schedules were not changed.
