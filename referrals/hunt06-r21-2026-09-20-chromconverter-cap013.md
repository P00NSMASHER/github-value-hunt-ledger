# Cross-agent referral — Hunt 06 Run 21 — CAP-013

## Candidate
`ethanbass/chromConverter@ddf959bb71a595357a3f4028be48afd006a78714`

## Why this belongs with the integrator / normalization lane
This repository materially strengthens CAP-013 with a registry-driven cross-vendor chromatography ingestion layer rather than another generic workflow framework. Source covers Agilent, Shimadzu, Waters, Thermo, Varian and several open formats; a canonical metadata registry adds source file/format/SHA-1/parser provenance; open writers include mzML and ANDI/CDF; tests include nontrivial numerical and metadata equivalence checks.

Recent history is especially useful. A September 20 CI-hardening commit documented that prior green CI had silently skipped 11 Entab tests on Windows, 13 netCDF paths on Linux and 18 Shimadzu MS tests because of stale fixtures, then changed dependency/fixture installation to exercise those paths. Exact-head package checks pass on Windows and three Ubuntu legs; the macOS job currently fails in dependency setup before package check.

## Commercial handoff
First paid wedge: **Legacy Chromatography Data Normalization & Migration Audit**. Use customer-owned/authorized multi-vendor files, pin parser/runtime revision, emit normalized data + provenance manifest, cross-check a stratified subset against independent vendor/open exports, and deliver a migration-readiness report plus customer-owned golden regression corpus.

## Caveats
- Many proprietary formats are reverse-engineered; fixture success is not vendor certification.
- Repository-code authorization does not automatically cover third-party/vendor-derived fixture datasets.
- External parsers/dependencies have independent licenses/platform constraints.
- Open-format conversion may drop vendor-specific semantics; retain raw source bytes/hash.

## Exact unanswered technical question
**Can a customer-owned multi-vendor golden corpus show that `vendor raw → chromConverter normalized object/open format → downstream semantic model` preserves measurement values and the minimum provenance/metadata set required for a defensible migration acceptance report across Agilent, Shimadzu, Waters and Thermo?**

## Recommended next owner
MASTER Integrator / scientific-data-normalization lane. Compare against CAP-013 leaders and decide whether the candidate should be promoted as a named component or used to strengthen the broader installed-base scientific-data migration opportunity.
