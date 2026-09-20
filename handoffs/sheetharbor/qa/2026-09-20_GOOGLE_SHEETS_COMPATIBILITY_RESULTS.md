# SheetHarbor v0.2.0-alpha — Google Sheets Compatibility Gate

Date: 2026-09-20
Release-control issue: `P00NSMASHER/github-value-hunt-ledger#1`

## Result

**PASS — Google Sheets import / recalculation / XLSX export compatibility verified for all four legacy vertical v0.2.0-alpha workbooks.**

This clears the P0 gate:

> Run Google Sheets import/recalc/export compatibility QA for the four legacy vertical workbooks.

It does **not** clear Microsoft Excel round-trip QA or the requirement to create a dedicated private SheetHarbor product repository. Therefore **v0.2.0 remains blocked from freeze**.

## Test method

For each canonical frozen XLSX:

1. Confirmed the source artifact was the expected v0.2.0-alpha workbook used by the 2026-09-19 release handoff.
2. Imported the XLSX to Google Drive using native Google Sheets conversion.
3. Confirmed native conversion succeeded and expected worksheet tabs survived.
4. Read formulas and effective values directly from the native Google Sheet after conversion/recalculation.
5. Compared key decision-output formulas and values against the canonical workbook / independent golden arithmetic gate.
6. Exported the native Google Sheet back to `.xlsx`.
7. Reopened the exported XLSX and inspected key formula/output ranges.
8. Scanned the exported workbook for `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, and `#N/A`.
9. Rendered each principal calculator/output sheet after export for visual QA.

## Products verified

| Product | Native Google Sheet | Key range | Recalc result | XLSX re-export | Formula-error scan | Visual check |
|---|---|---|---|---|---|---|
| SH-CANDLE | `1i6zN8IFTHYzvBt-G6-mUEvgTZCzZs1pq3f5Ol3gGjfc` | `Candle Calculator!B16:B40` | PASS | PASS | PASS | PASS |
| SH-FDM | `1P4pxtfKkcEKMZA05Yiv1Rhe-nhxqu6BVR1PeChZtpS8` | `Job Calculator!B19:B37` | PASS | PASS | PASS | PASS |
| SH-EMB | `14TVofpuH5nvetXv9W9sJWjRss0Ptp_Q_9yM7fQLTQLk` | `Job Calculator!B17:B38` | PASS | PASS | PASS | PASS |
| SH-SCREEN | `1h9IPx9RpJpuFCZaVb_O9Ub_1qskDh7pldQindf87kwc` | `Worked Example!G6:G18` | PASS | PASS | PASS | PASS |

## Golden decision outputs after native Google Sheets recalculation

### SH-CANDLE
- Planned production units: 50
- Total production cost: 265.9166666666667
- Cost / sellable candle: 5.539930555555556
- Target retail / candle: 11.834908361970218
- Retail margin: 0.45
- Wholesale margin at default discount: 0.06379831831105186

### SH-FDM
- Build plates required: 5
- Cost before selling fees: 69.04710144927536
- Target quote: 129.43383448462683
- Target price / unit: 12.943383448462683
- Target margin realized: 0.40
- Profit / hands-on labor hour: 44.377314680443476

### SH-EMB
- Planned production units: 25
- Cost before selling fees: 435.2363888888889
- Target quote: 845.7017259978427
- Target price / item: 35.237571916576776
- Target margin realized: 0.45
- Profit / hands-on labor hour: 290.87830066167845

### SH-SCREEN
- Production garments incl. spoilage: 50
- Total internal cost: 279.00666666666666
- Recommended quote total: 490.0116959064327
- Recommended price per garment: 10.208576998050681
- Estimated profit after selling fees: 171.5040935672514
- Realized margin: 0.35

These values agree with the canonical v0.2.0-alpha worked examples and the independent golden arithmetic gate recorded in `handoffs/sheetharbor/qa/2026-09-20_GOLDEN_ARITHMETIC_RESULTS.md`.

## Formula preservation

The key operational formula ranges survived native conversion and XLSX export.

- SH-CANDLE: 25/25 formulas preserved in `B16:B40`.
- SH-FDM: 19/19 formulas preserved in `B19:B37`.
- SH-EMB: all formulas preserved in `B17:B38`.
  - Google exported `B26:B27` using Excel's shared-formula representation. `B26` contains the shared formula definition and `B27` carries the shared-formula reference. `B27` therefore remains a formula equivalent to `=B12` and evaluates to the expected value.
- SH-SCREEN: 13/13 formulas preserved in `G6:G18`.

No tested formula became an error after the Google Sheets round trip.

## Worksheet structure preservation

Expected tabs survived conversion and export.

- Candle: 8 tabs
- FDM 3D Printing: 8 tabs
- Embroidery: 8 tabs
- Screen Printing: 5 tabs

The principal calculator/output sheets rendered cleanly after XLSX export with readable inputs, outputs, number formats, section styling, and no obvious clipping or overlap in the tested regions.

## Release-control conclusion

### P0 gates now cleared
- [x] Golden arithmetic tests for all four vertical products
- [x] Google Sheets import/recalc/export compatibility for all four legacy vertical products

### P0 gates still open
- [ ] Create the dedicated private SheetHarbor product repository and migrate canonical release/build/test assets into it
- [ ] Microsoft Excel round-trip compatibility QA on named supported Excel version(s)

Do not freeze `v0.2.0` until both remaining gates pass.
