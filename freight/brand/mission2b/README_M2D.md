# RETALLY | Reproducible collateral build and technical acceptance

**Technical build: PASS. Customer distribution: BLOCKED.** Source: GitHub draft PR #300.

## Canonical source
- `COMMERCIAL_TRUTH_M2C_V1.json`: reviewable canonical approved wording / hypothetical financial states.
- `source/commercial_truth.json`: byte-independent JSON mirror checked against canonical in GitHub CI.
- `source/build_collateral.py`: actual generator of 12 editable DOCX customer artifacts.
- `source/financial_controls.py`: synthetic invoice, claim-state, settlement, reversals and fee safeguards.
- `source/acceptance_qa.py`: 12 PDF/DOCX pair inspections, 23 US Letter pages, monetary parity, margins, logo checks and rendered QA contact sheets.
- `test_collateral_m2c.py` and `test_import_m2e.py`: 19 standard-library tests. These **are not** real RecoveryOS production tests.

## Exact approved original artwork is now in GitHub
- `assets/retally-wordmark-approved.png`: 293,909 bytes, SHA-256 `08421ccd7e8b1db752002f7ea177e76c83b6ee1cae40cf8b459368ade0c4eadd`.
- `assets/retally-emblem-approved.png`: 484,377 bytes, SHA-256 `bb02ab4a468762f597c241199baeff61b485dd793f8fb746140ad33670b68043`.

Both masters were admitted to the internal PR after source and byte-level verification. They are not re-encoded website WebP derivatives. The temporary write-enabled upload workflow was removed after import; the normal CI has **read-only** repository permission.

## Clean checkout commands

Run from repository root:

```sh
python -m unittest discover -s freight/brand/mission2b -p 'test_*m2*.py' -v
python -m pip install -r freight/brand/mission2b/source/requirements.txt
# LibreOffice Writer must be installed; this does not require a production browser
cd freight/brand/mission2b/source
python build_collateral.py
mkdir -p ../pdf ../qa
libreoffice --headless --convert-to pdf --outdir ../pdf ../docx/*.docx
python acceptance_qa.py
```

Outputs remain under `freight/brand/mission2b/{docx,pdf,qa}/`; they are generated QA artifacts, not independently approved customer publications.

## GitHub proof
At PR SHA `ac132dbd893e7810f933d74f8fd6c3151d13d3fb`, GitHub Actions run [37812262203](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/37812262203) succeeded:
- Canonical-source parity and 19 automated tests: PASS.
- Hash admission directly from repository: PASS.
- Rebuild 12 editable DOCX and 12 PDFs on a clean runner: PASS.
- 23 US Letter pages, dollar parity, no reported QA errors: PASS.
- [Internal review artifact](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/37812262203), retained temporarily in GitHub Actions.

This is a reproducible **technical** acceptance result, not legal, security or commercial authority. Future changes require CI on the new exact head.

## Remaining commercial release blockers
1. Verified registered/legal contracting party and trade-name clearance.
2. Professional approval of binding contingency pricing, exclusions, reversals and NDA/DPA where required.
3. Verified confidential-data intake, retention, access control and authorized destruction.
4. Real external-to-company email receipt and contact-flow end-to-end check.
5. Customer-specific scope and reviewer authorization before any outside activity.
6. The published sample's gross $14,200 less reversal $750 gives $13,450 net, but its $11,800 fee-eligible figure leaves **$1,650 unexplained**. Never label it a verified exclusion without source-level evidence.
7. Per-artifact distribution approval; case-study publication requires actual verified customer outcomes and permission.

Do not publish automatically, contact customers/carriers or execute contracts solely because technical CI is green.
