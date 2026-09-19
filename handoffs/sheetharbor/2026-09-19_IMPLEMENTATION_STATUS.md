# SheetHarbor GitHub-Intelligence Upgrade — Implementation Status

Date: 2026-09-19

## Implemented

1. Frozen the four current QA workbooks as normalized v0.1.0 baseline artifacts in Google Drive.
2. Computed independent SHA-256 hashes for the frozen baseline artifacts.
3. Created a release-control workbook covering artifact identity, rights/reuse boundaries, release gates, and roadmap.
4. Created v0.2.0-alpha copies of Candle, FDM 3D Printing, Embroidery, and Screen Printing with a standardized Version & QA tab. Existing calculation logic is preserved.
5. Built a new clean-room SheetHarbor Maker Economics Scenario + Inventory Planner.
6. Kept no-license repository material clean-room only and did not embed GPL code in the generated workbooks.
7. Uploaded exact generated XLSX snapshots to the SheetHarbor Releases Google Drive hierarchy.
8. Converted Maker Economics v0.1.1-alpha to a native Google Sheet and inspected formulas/effective values after conversion.

## Verification change

- Maker Economics v0.1.0-alpha is SUPERSEDED. Its production safety-stock formula was correct, but its independent golden-test expected value was wrong (86.10).
- v0.1.1-alpha corrects the golden expected value to 94.78528366787747 for z=1.65, average demand=100, demand SD=20, average lead time=2, and lead-time SD=0.5.
- In the native Google Sheets conversion of v0.1.1-alpha:
  - scenario arithmetic golden test = PASS;
  - inventory safety-stock golden test = PASS;
  - scenario formulas retained expected effective values;
  - inventory formulas retained expected effective values.
- Google Sheets formula compatibility is therefore VERIFIED for Maker Economics v0.1.1-alpha via the current QA conversion.
- Microsoft Excel round-trip compatibility remains unverified.

## Rights boundaries

- ph4n70mr1ddl3r/erp — no license detected: clean-room requirements inspiration only.
- djconnexion77/DynamicPricingEngine — no license detected: clean-room scenario architecture inspiration only.
- OmniDiscount — GPLv3-or-later: behavioral/edge-case research only for the current closed workbook path.
- OctopusTakopi/bocpd — MIT: future historical-ops option after a real history-import workflow exists.
- Microsoft RulesEngine, Zerox, Dedupe — MIT: potential future app dependencies, not required for spreadsheet-first v1.
- Hyper-Trees — Apache-2.0 plus Commons Clause: restricted; no paid-product reuse without separate review.

## Claims still blocked

- Microsoft Excel compatibility has not yet been independently round-trip verified.
- Google Sheets compatibility for the four legacy vertical v0.2.0-alpha workbooks has not yet been independently conversion/recalc/export verified.
- No customer outcome claim (time saved, margin improvement, stockout reduction, etc.) is allowed without pilot evidence.
- Historical forecasting / change detection is not a current shipped feature.

## Next release gates

### P0
- run golden arithmetic tests against each vertical workbook's key output cells;
- round-trip test named Microsoft Excel version(s);
- test Google Sheets conversion/recalc for the four legacy vertical workbooks;
- create a canonical SheetHarbor product repository and add release manifests/build/test assets;
- freeze v0.2.0 only after compatibility and arithmetic gates pass.

### P1
- normalize common UX and terminology across all four vertical products;
- package Embroidery + Screen Printing as a Custom Apparel Pricing Family;
- package all four as a Maker Economics Bundle;
- run structured user pilots and create a marketing-claim registry.
