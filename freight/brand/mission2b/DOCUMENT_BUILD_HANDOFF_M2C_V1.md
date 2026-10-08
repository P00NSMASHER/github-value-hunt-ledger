# RETALLY Mission 2C | Controlled customer collateral

Date: 2026-10-08. Status: **INTERNAL DOCUMENT BUILD COMPLETE; COMMERCIAL RELEASE BLOCKED**.

A single local reproduction command (requires python-docx, PyMuPDF, Pillow and LibreOffice):

```bash
cd source
python -m unittest test_financial_controls.py -v
python build_collateral.py
libreoffice --headless --convert-to pdf --outdir ../pdf ../docx/*.docx
python acceptance_qa.py
```

The build operates relative to its source folder and uses original approved logo PNG sources in `../assets/`; no generated alternate logos. Its synthetic inputs are versioned in `source/commercial_truth.json`. The existing 12 file basenames are preserved. Do not mistake a digitally regenerated document for customer distribution authorization.

See `BUYER_ACCEPTANCE_AND_RELEASE.md` for buyer acceptance and approval matrix, `FIRST_THREE_PILOTS_OPERATING_SEQUENCE.md` for operating workflow, and `qa/m2c_acceptance.json` for exact per-file hashes and PDF inspection results.

The GitHub PR carries a condensed business-truth register and independent standard-library regression tests. The full editable generator, 24 binary files and QA images are delivered in this local package. **The GitHub PR alone is not yet a fully mirrored artifact repository**; closing that gap requires transferring the delivered source/package into the connected repository through a binary upload-capable workflow.