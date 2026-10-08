# RETALLY Mission 2D | Reproducible collateral source

**Status: engineering source integrated, customer release BLOCKED.** This folder belongs to draft PR #300. No website, client record, carrier or contract is modified by these materials.

## Source of truth

- `COMMERCIAL_TRUTH_M2C_V1.json` and `source/commercial_truth.json` must be identical, checked in CI.
- `source/build_collateral.py`: the actual v1.0 generator for 12 editable Word documents.
- `source/financial_controls.py`: synthetic invoice, claim-stage and settlement logic.
- `source/acceptance_qa.py`: checks 12 Word/PDF pairs, 23 pages, monetary values, version footer, page bounds, approved-asset SHA and renders contact sheets.
- `test_collateral_m2c.py`: 16 standard-library negative and positive tests (does **not** establish RecoveryOS correctness).

## Required original assets: not committed yet

Place the exact reviewed PNGs in **`freight/brand/mission2b/assets/`**, WITHOUT redrawing or using website WebP derivatives:
- `retally-wordmark-approved.png` SHA-256 `08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd`
- `retally-emblem-approved.png` SHA-256 `bb02ab4a468762f597c241199baeff61b485dd793f8fb746140ad33670b68043`

The original masters are already in the separate Mission 2C downloadable package. **As long as these bytes are absent from the repository, a clean GitHub checkout cannot rebuild customer PDFs, and the release acceptance job MUST FAIL.** Copying bytes from the exact approved package is allowed after human verification; substituting arbitrary logos is not.

## Verified exact-master import (Mission 2E)

A standalone, offline importer now validates and extracts **only** the approved original master PNG files from the existing `RETALLY_Mission2D_Approved_Master_Transfer.zip`. It matches SHA-256 values against the commercial-truth register, rejects tampering/duplicates, and never substitutes logo derivatives:

```sh
python freight/brand/mission2b/source/import_approved_masters.py RETALLY_Mission2D_Approved_Master_Transfer.zip --check-only
python freight/brand/mission2b/source/import_approved_masters.py RETALLY_Mission2D_Approved_Master_Transfer.zip
python -m unittest discover -s freight/brand/mission2b -p 'test_*m2*.py' -v
```

This importer **does not automatically upload to GitHub**. The verified binary files still require committing at the two specified repository paths. The PR remains draft and the GitHub `print-and-document-gate` must remain blocked until the real PNG files are present and remote document rendering passes.

## How to verify locally

From the repository root, after placing the two original master files:

```sh
python -m unittest discover -s freight/brand/mission2b -p test_collateral_m2c.py -v
python -m pip install -r freight/brand/mission2b/source/requirements.txt
cd freight/brand/mission2b/source
python build_collateral.py
libreoffice --headless --convert-to pdf --outdir ../pdf ../docx/*.docx
python acceptance_qa.py
```

LibreOffice is required only for DOCX→PDF export; code and tests do not send network traffic or contact customers. Outputs under `docx/`, `pdf/`, `qa/` are review artifacts and must not be added to website production or sent without approval.

## Independent clean-room result

An empty build folder containing five source files and only the two approved PNGs regenerated **12 Word files and 12 PDFs with 23 total pages**, 16 tests passing, no monetary-parity/page-boundary QA errors. This establishes portable build functionality *once exact assets are supplied*, not a self-contained repository build.

## Release blockers

1. Mirror the exact two masters and generated artifact provenance; re-run remote CI on exact head.
2. Resolve real contract party and binding fee terms with owner/counsel.
3. Verify confidential-data intake controls and actual successful inbound customer inquiries.
4. Investigate the `$1,650` sample net-vs-eligible difference using source-level evidence, or continue labeling it unexplained.
5. Final human approval of customer-document distribution.

No unverified placeholder should ever be replaced with a made-up value.
