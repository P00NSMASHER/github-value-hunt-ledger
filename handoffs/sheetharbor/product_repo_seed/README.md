# SheetHarbor

Private product repository seed for SheetHarbor spreadsheet products.

## v0.2.0 release state

`v0.2.0-alpha` is **not frozen**.

Cleared gates:
- Golden arithmetic: PASS for all four vertical workbooks.
- Google Sheets import/recalc/export: PASS for all four vertical workbooks.

Open gate:
- Microsoft Excel round-trip compatibility on a named supported Excel version.

## Canonical artifacts

The canonical alpha workbooks belong under `artifacts/v0.2.0-alpha/` and are pinned by SHA-256 in `release/v0.2.0-alpha/manifest.json`.

## QA

Run the dependency-free arithmetic gate:

```bash
python qa/golden_arithmetic_v0_2_0.py artifacts/v0.2.0-alpha
```

Run the Microsoft Excel round-trip gate on Windows with desktop Excel installed:

```powershell
pwsh -File qa/excel_roundtrip_v0_2_0.ps1 -ArtifactDir artifacts/v0.2.0-alpha -OutputDir qa-results/excel
```

The Excel gate opens copies in Microsoft Excel via COM, performs a full rebuild calculation, saves, closes, reopens, recalculates, and verifies the key decision outputs and formula-error count.

Do not tag or freeze `v0.2.0` until every required gate in `RELEASE_CHECKLIST.md` passes.
