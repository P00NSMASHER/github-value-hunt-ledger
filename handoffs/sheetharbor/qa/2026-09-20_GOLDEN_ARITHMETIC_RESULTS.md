# SheetHarbor v0.2.0-alpha Golden Arithmetic Gate

Date: 2026-09-20
Source release issue: `P00NSMASHER/github-value-hunt-ledger#1`

## Result

**PASS — 4/4 vertical products, exact release hashes, 24 independent arithmetic checks.**

This clears the P0 gate: **run golden arithmetic tests against each vertical workbook's key output cells**.

It does **not** clear the remaining P0 gates for Microsoft Excel round-trip compatibility, Google Sheets conversion/recalc/export compatibility for the four legacy vertical workbooks, or creation of the dedicated private SheetHarbor product repository. v0.2.0 must therefore remain unfrozen.

## Canonical artifacts verified

| Product | Artifact | SHA-256 | Golden sheet | Checks | Status |
|---|---|---|---|---:|---|
| SH-CANDLE | `SheetHarbor_Candle_Economics_v0.2.0-alpha.xlsx` | `b289019dbf6c129d640a7b431ab52f3431f9f6d5bf0ead387b309341005631ba` | `Candle Calculator` | 6 | PASS |
| SH-FDM | `SheetHarbor_FDM_3D_Printing_Economics_v0.2.0-alpha.xlsx` | `94d69ceecf4f894ddacc8ae36f882dde25a918072aa7b802f2b9039a4631a94c` | `Job Calculator` | 6 | PASS |
| SH-EMB | `SheetHarbor_Embroidery_Economics_v0.2.0-alpha.xlsx` | `384108221ab99173f91c54d7b5cacbf1c24212b76ea07d05cd56c168fe37bc8d` | `Job Calculator` | 6 | PASS |
| SH-SCREEN | `SheetHarbor_Screen_Printing_Economics_v0.2.0-alpha.xlsx` | `702b5fd6fdcdc69638d570699b323c021b18d3540241d63a24a2828169241b84` | `Worked Example` | 6 | PASS |

The hashes above match `handoffs/sheetharbor/SHA256SUMS_2026-09-19.txt`.

## Arithmetic cells checked

- SH-CANDLE: `B16`, `B32`, `B33`, `B35`, `B37`, `B40`
- SH-FDM: `B19`, `B30`, `B32`, `B33`, `B35`, `B37`
- SH-EMB: `B17`, `B32`, `B34`, `B35`, `B37`, `B38`
- SH-SCREEN: `G6`, `G14`, `G15`, `G16`, `G17`, `G18`

The expected values are computed independently in Python from the frozen worked-example assumptions rather than copied from workbook outputs. The gate then reads the XLSX cached values directly and compares them with a tight numeric tolerance.

## Reproducible gate

Test harness: `handoffs/sheetharbor/qa/golden_arithmetic_v0_2_0.py`

The harness uses only the Python standard library. It intentionally has no Excel library dependency, making it suitable for a future private product repository and CI workflow.

Example:

```bash
python handoffs/sheetharbor/qa/golden_arithmetic_v0_2_0.py /path/to/canonical/xlsx/artifacts
```

Expected terminal result:

```text
PASS SH-CANDLE — ... — hash + 6 arithmetic checks
PASS SH-FDM — ... — hash + 6 arithmetic checks
PASS SH-EMB — ... — hash + 6 arithmetic checks
PASS SH-SCREEN — ... — hash + 6 arithmetic checks

GATE: PASS (4/4 products; exact hashes; 24 independent arithmetic checks)
```

## Release-control interpretation

This gate demonstrates that the frozen v0.2.0-alpha artifacts contain the expected worked-example arithmetic and that the exact artifacts tested are the ones listed in the release hash manifest.

It does not demonstrate recalculation behavior after an application opens/saves the workbook. Excel and Google Sheets compatibility remain separate release gates and must still be tested independently.
