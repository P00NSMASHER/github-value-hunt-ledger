# Datasets & Data Pipelines

Cross-lane index maintained by Hunt 15 MASTER Integrator.

Use this file for high-value public datasets, data pipelines, APIs, reference tables, historical archives, schemas, normalization/entity-resolution assets, and hard-to-recreate lawful data advantages discovered by the hunters.

For each entry record:
- Repository / source
- Canonical URL
- Exact revision / date inspected
- Dataset or pipeline description
- Coverage / freshness / format
- Evidence inspected
- Actual published license / rights metadata
- User-asserted separate commercial authorization posture
- Buyer / problem
- Monetization or product use
- Build-time / data advantage
- Value score
- Combination opportunities
- Next action

Do not store credentials, tokens, private/personal data, or raw accidental secrets.

## Elite indexed sources — 2026-09-19

### GSA/srt-fbo-scraper — solicitation packet/history acquisition pipeline
- Repository / source: https://github.com/GSA/srt-fbo-scraper
- Exact revision: `fbdfa86a2bce4323a5afacda04f083698cab02e1`.
- Dataset / pipeline: official GSA implementation that pages SAM Opportunities v2, canonicalizes agency/office context, downloads solicitation attachments including malformed-link cases, extracts DOC/RTF/DOCX/PDF text and maintains solicitation/history state.
- Coverage / format: opportunity metadata + attachment packet/history acquisition and normalized extracted text; live SAM/source-system freshness and terms remain external.
- Evidence inspected: implementation, attachment/history behavior and extraction paths as recorded in MASTER.
- Published rights: CC0-1.0 for repository work; SAM/source data terms/status remain separate.
- Standing permission posture: repository-owned content treated as commercially authorized under the user's standing assertion; third-party/source-system data remains separately governed.
- Buyer / problem: federal capture/proposal teams need the controlling packet and amendment history, not just an opportunity summary.
- Product use: CaptureBrief packet-completeness and source-evidence layer.
- Build/data advantage: removes substantial attachment/history edge-case engineering and provides a first-party operational lineage.
- Value score: **28/30** — A4 B4 C5 D5 E5 F5.
- Combination: GSA FAR + USAspending + DATA Act broker + FAR Overhaul/deviation evidence.
- Next action: 10-live-solicitation packet-completeness benchmark with exact source artifact/hash and amendment-history verification.

### GSA/GSA-Acquisition-FAR — machine-readable FAR authority corpus
- Repository / source: https://github.com/GSA/GSA-Acquisition-FAR
- Exact revision: `da52ccbbe114e1f031a7f4c59195c508dbfa485f`.
- Dataset / pipeline: official Acquisition.gov FAR DITA with clause/provision structure, fill-in metadata, FAC revision markers, FAR Case identifiers and change provenance.
- Coverage / format: machine-readable FAR regulatory source; agency deviations and solicitation-specific fill-ins remain separate evidence.
- Evidence inspected: structured clause/provision and revision metadata as recorded in MASTER.
- Published rights: official FAR/regulatory text is authoritative public-law/regulatory material; no blanket permissive software license was established for every packaging artifact.
- Standing permission posture: repository-owned code/content is treated as commercially authorized under the user's standing assertion; this does not expand rights in separately owned standards/assets.
- Buyer / problem: capture/proposal teams need exact current clause text, revision and fill-ins instead of stale summaries.
- Product use: CaptureBrief clause reconstruction and rule-currency baseline.
- Build/data advantage: replaces ad-hoc scraping/search with a first-party structured regulatory source.
- Value score: **29/30** — A5 B5 C5 D5 E5 F4.
- Combination: solicitation packet/history + FAR Overhaul agency deviations + SAM/USAspending/DATA Act identity/award lineage.
- Next action: validate deviation applicability and supersession on 10 live solicitations.

### fedspendingtransparency/usaspending-api — federal award/procurement evidence pipeline
- Repository / source: https://github.com/fedspendingtransparency/usaspending-api
- Exact revision: `1692d484b38c66361c54faa221548527cae29964`.
- Dataset / pipeline: official USAspending server/ETL schemas and implementation for award, procurement, recipient and spending data.
- Coverage / format: federal award/procurement/recipient/spending semantics and ETL; upstream source-system caveats remain external.
- Evidence inspected: server/ETL schemas, implementation and tests as recorded in MASTER.
- Published rights: CC0-1.0 for the official repository; source-system caveats separate.
- Standing permission posture: repository-owned material treated as commercially authorized; underlying source data remains governed by its authoritative source terms/status.
- Buyer / problem: GovCon teams need defensible incumbent, award and spend lineage without reverse-engineering semantics.
- Product use: CaptureBrief historical award/incumbent/spend evidence.
- Build/data advantage: official upstream schemas/lineage materially reduce false award and incumbent joins.
- Value score: MASTER-promoted authoritative source; no separate /30 was recorded in the current source entry.
- Combination: DATA Act broker identity + SAM opportunity/packet + FAR/deviation evidence.
- Next action: validate PIID/referenced-IDV and parent-entity joins against live solicitation samples.

### fedspendingtransparency/data-act-broker-backend — federal identity/procurement normalization
- Repository / source: https://github.com/fedspendingtransparency/data-act-broker-backend
- Exact revision: `76dcae4ccbf6951223608bc1d8fd0c5b03da5d68`.
- Dataset / pipeline: official DATA Act broker semantics for UEI/DUNS/legal/DBA/parent identities, addresses/business types and procurement/referenced-IDV identifiers.
- Coverage / format: normalized federal award/recipient/identifier semantics and validation logic.
- Evidence inspected: schemas/validation/identity semantics recorded in MASTER.
- Published rights: CC0-1.0; downstream/source-system caveats separate.
- Standing permission posture: repository-owned material commercially authorized under the standing assertion; source-system data separately governed.
- Buyer / problem: false entity/parent/PIID joins can invalidate capture conclusions.
- Product use: CaptureBrief identity/award normalization and contradiction checking.
- Build/data advantage: hard-to-recreate first-party identity/procurement semantics.
- Value score: **29/30** — A4 B5 C5 D5 E5 F5.
- Combination: USAspending + SAM packet + FAR/deviation layer.
- Next action: benchmark parent/PIID/referenced-IDV conflict cases and require unresolved conflicts to remain unresolved.

### aiparallel0/freight-audit — synthetic freight audit challenge corpus and evaluation pipeline
- Repository / source: https://github.com/aiparallel0/freight-audit
- Exact revision: `e7869162cf9cb23f6d520a0cd71f87cf973d8c28`.
- Dataset / pipeline: freight-specific rate-confirmation + invoice + POD audit harness with integer-cents money, OCR/evaluation/review tooling and synthetic challenge cases such as clean billing, duplicate fuel, unauthorized liftgate and detention evidence.
- Coverage / format: committed synthetic/PII-free benchmark cases plus evaluation harness; external benchmark assets retain separate attribution/rights.
- Evidence inspected: code, synthetic fixtures/challenge cases and evaluation behavior recorded in MASTER.
- Published rights: MIT for code and committed synthetic/PII-free corpus; external benchmark assets separate.
- Standing permission posture: repository-owned material commercially authorized; no extension to external datasets/assets.
- Buyer / problem: freight audit systems need falsifiable gold truth separating extraction failure from rule/math failure.
- Product use: Freight Audit Acceptance Test / blind incumbent bake-off challenge layer.
- Build/data advantage: ready-made freight-specific negative/positive cases compress benchmark construction and reduce self-confirming tests.
- Value score: **28/30** — A4 B4 C5 D5 E5 F5.
- Combination: RateCon extraction + Assay acceptance + Qatoto/Kareya authority/rerating + settlement attribution.
- Next action: extend only with independently authored customer-authorized accessorial/addendum and settlement cases; do not treat synthetic fixtures as proof of real-world recovery.