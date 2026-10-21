# SheetHarbor v0.2.0 Release Checklist

## P0 — must pass before freeze

- [x] Canonical artifacts pinned by SHA-256.
- [x] Independent golden arithmetic gate passes for all four vertical workbooks.
- [x] Google Sheets native import/recalculation/XLSX-export gate passes for all four vertical workbooks.
- [x] Microsoft Excel round-trip gate passes on desktop Excel 16.0 build 17830 (October 21, 2026).
- [x] Excel result records exact Excel version/build and exported artifact hashes.
- [x] No worksheet error cells after Excel recalculation and save/reopen; all key outputs retain formulas.
- [x] `release/v0.2.0-alpha/manifest.json` updated with actual Excel evidence and `freeze_allowed: true`.
- [ ] Tag `v0.2.0` only after all above checks are complete.

## P1 — post-freeze quality work

- [ ] Normalize terminology and UX across vertical products.
- [ ] Package Embroidery + Screen Printing as Custom Apparel Pricing Family.
- [ ] Package all four as Maker Economics Bundle.
- [ ] Run structured user pilots.
- [ ] Maintain a marketing-claim registry tied to pilot evidence.
