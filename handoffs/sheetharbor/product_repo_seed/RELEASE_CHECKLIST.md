# SheetHarbor v0.2.0 Release Checklist

## P0 — must pass before freeze

- [x] Canonical artifacts pinned by SHA-256.
- [x] Independent golden arithmetic gate passes for all four vertical workbooks.
- [x] Google Sheets native import/recalculation/XLSX-export gate passes for all four vertical workbooks.
- [ ] Microsoft Excel round-trip gate passes on a named supported desktop Excel version.
- [ ] Excel result records exact Excel version/build and exported artifact hashes.
- [ ] No key formula output contains `#REF!`, `#DIV/0!`, `#VALUE!`, `#NAME?`, or `#N/A` after Excel save/reopen.
- [ ] `release/v0.2.0-alpha/manifest.json` updated with Excel evidence and `freeze_allowed: true` only after the gate passes.
- [ ] Tag `v0.2.0` only after all above checks are complete.

## P1 — post-freeze quality work

- [ ] Normalize terminology and UX across vertical products.
- [ ] Package Embroidery + Screen Printing as Custom Apparel Pricing Family.
- [ ] Package all four as Maker Economics Bundle.
- [ ] Run structured user pilots.
- [ ] Maintain a marketing-claim registry tied to pilot evidence.
