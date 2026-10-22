# SheetHarbor

Private product repository seed for SheetHarbor spreadsheet products.

## v0.2.0 release state

`v0.2.0-alpha` has cleared all three technical freeze gates. The release manifest
allows freezing; no release tag, storefront or customer delivery is implied.

Cleared gates:
- Golden arithmetic: PASS for all four vertical workbooks.
- Google Sheets import/recalc/export: PASS for all four vertical workbooks.
- Microsoft Excel 16.0 build 17830: PASS for all four workbooks on October 21,
  2026, including full recalculation, save/reopen, key formulas and error scans
  across every worksheet. See the retained release evidence JSON.

The same canonical source hashes passed all 24 independent golden arithmetic
checks again on October 21. Workbook bytes were unchanged; Excel tested copies.

## Canonical artifacts

The canonical alpha workbooks belong under `artifacts/v0.2.0-alpha/` and are pinned by SHA-256 in `release/v0.2.0-alpha/manifest.json`.

## QA

Run the dependency-free arithmetic gate:

```bash
python ../qa/golden_arithmetic_v0_2_0.py artifacts/v0.2.0-alpha
```

Run the Microsoft Excel round-trip gate on Windows with desktop Excel installed:

```powershell
pwsh -File qa/excel_roundtrip_v0_2_0.ps1 -ArtifactDir artifacts/v0.2.0-alpha -OutputDir qa-results/excel
```

The Excel gate opens copies in Microsoft Excel via COM, performs a full rebuild calculation, saves, closes, reopens, recalculates, and verifies the key decision outputs and formula-error count.

Do not tag or freeze `v0.2.0` until every required gate in `RELEASE_CHECKLIST.md` passes.
