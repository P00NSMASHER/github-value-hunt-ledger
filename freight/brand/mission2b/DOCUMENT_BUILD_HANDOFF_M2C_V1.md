# RETALLY | Customer collateral build handoff, Missions 2C–2F

**Date:** 2026-10-08. **Status:** GitHub-reproducible technical build PASSED; customer commercial release remains BLOCKED.

## Actual controlled sources
- Financial and commercial authority: `COMMERCIAL_TRUTH_M2C_V1.json`, mirrored in `source/commercial_truth.json`.
- Approved source artwork: `assets/retally-wordmark-approved.png`, `assets/retally-emblem-approved.png` (verified by SHA-256).
- Portable editable-document generator: `source/build_collateral.py`.
- Sample-specific controls and negative-case tests: `source/financial_controls.py`, `test_collateral_m2c.py`, `test_import_m2e.py`.
- Rendered-PDF acceptance: `source/acceptance_qa.py`; generated `qa/m2c_acceptance.json`.
- Buyer review: `BUYER_ACCEPTANCE_M2C_V1.md`; pilot workflows: `FIRST_THREE_PILOTS_M2C_V1.md`.
- Full rebuild instructions: `README_M2D.md`.
- Strict release restrictions: `COLLATERAL_RELEASE_REGISTER_V1.md`.

## Verified GitHub run
[RETALLY collateral acceptance #37812262203](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/37812262203) successfully generated 12 DOCX + 12 PDF documents (23 pages) from the complete GitHub branch and original artwork. All 19 source tests, logo integrity checks, monetary parity and existing automated PDF layout checks passed. CI artifacts are internal review only and subject to GitHub artifact-retention expiry.

## Commercial release gates
There is no approved customer case study, no verified fee-base explanation for the $1,650 sample difference, and no authenticated proof in this collateral build of actual legal contracting identity, signed fees, or operationally accepted confidential intake. A green GitHub build cannot close those gates.

Do not edit the public website, send customer/partner correspondence, contact carriers, assume secured intake is operational or sign contracts through this source handoff.
