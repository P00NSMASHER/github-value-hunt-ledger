# QA Gates

## Golden arithmetic

`golden_arithmetic_v0_2_0.py` is dependency-free. It verifies exact artifact hashes and independently computes the expected decision outputs for the default worked examples.

## Microsoft Excel round trip

`excel_roundtrip_v0_2_0.ps1` requires Windows plus an installed desktop copy of Microsoft Excel.

It does not mutate the canonical source files. For each workbook it:

1. verifies the source SHA-256;
2. copies the workbook into the output directory;
3. opens the copy through Excel COM with macros disabled;
4. performs `CalculateFullRebuild()`;
5. verifies key output cells and formula presence;
6. verifies no formula-error cells are present;
7. saves and closes;
8. reopens the saved copy in Excel;
9. recalculates and repeats the checks;
10. writes `excel-roundtrip-results.json` with the Excel version/build and per-product evidence.

A nonzero exit code blocks release.
