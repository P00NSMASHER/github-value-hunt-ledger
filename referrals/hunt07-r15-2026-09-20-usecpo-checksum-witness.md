# Hunt 07 R15 — USECPO checksum-witness audit — 2026-09-20

## Purpose
Close the remaining CAP-015 / EXP-012 artifact-identity gap without pretending catalog metadata is byte-level evidence.

## Current first-party state
- USECPO landing page: https://data.openei.org/submissions/6458
- Current v2 archive: https://data.openei.org/files/6458/Outage_Dataset_R1.zip
- Current v2 guideline: https://data.openei.org/files/6458/Guideline_OEDI_Updated.docx
- Data.gov currently records the dataset as public / CC BY 4.0 and last modified 2026-07-27, while the guideline response exposes `Last-Modified: Thu, 24 Apr 2025 22:05:06 GMT`. Treat catalog version and file version as separate facts.
- The official Data.gov DCAT record exposes resource URLs/media types but no cryptographic digest for either v2 resource.
- Direct automated archive inspection remains blocked in this environment: the official ZIP is reachable as a current resource but exceeds the text fetcher limit; the DOCX exposes its file validator but not reversible document bytes here.

## New external checksum-witness route
A new Mendeley Data reproducibility package published 2026-08-24:

- DOI: https://doi.org/10.17632/r4csg2h2ps.1
- Title: `Data and code for stochastic planning of building electricity-hydrogen-thermal integrated energy systems across multiple climate zones`
- Contributor: Zhipeng Xu
- Public package license: CC BY 4.0.

The package description explicitly names **OEDI/USECPO outage data** among its public inputs and states that raw third-party files are *not* redistributed. Instead, its download manifests retain **source URLs, release identifiers, file sizes, and SHA-256 hashes** so the public inputs can be reconstructed from original providers.

The Mendeley public API exposes two duplicate root package ZIPs, each 12,980,662 bytes with package SHA-256 `3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67`. This proves the reproducibility package itself is hash-addressable; it does **not** yet prove the SHA-256 of `Outage_Dataset_R1.zip` because the internal download manifest could not be byte-extracted in this run.

## Evaluation
- Status: **WATCH / external checksum witness, not first-party authority**.
- Score: **22/30 — A2 B3 C4 D4 E4 F5**.
- Evidence label: the existence and declared purpose of the Mendeley source manifest are VERIFIED from the dataset record; the exact USECPO manifest row/hash remains UNVERIFIED until the archive contents are inspected.
- Why useful: if the manifest contains the exact OEDI URL `.../Outage_Dataset_R1.zip`, its recorded size/hash becomes an independent contemporaneous witness. When official bytes or an official digest become available, a match can strongly bind the experiment to the same artifact.
- Why insufficient alone: a third-party reproducibility manifest cannot replace a first-party digest or direct byte hash. It may pin a different USECPO release or an earlier download if the URL was mutable.

## CAPABILITY DELTA
CAP-015 gains an explicit `external_digest_witness` concept: independently published source URL + release + size + digest can strengthen artifact identity, but never silently become first-party authority.

## GRAPH EDGE
`Mendeley r4csg2h2ps.1` -> CHALLENGES/STRENGTHENS `DATA USECPO v2` artifact identity -> STRENGTHENS `CAP-015` -> reduces one provenance risk in `EXP-012` once exact manifest row is extracted.

## RADAR SIGNAL
Supports the broader proof-carrying / prospective-evidence trend: serious reproducibility packages are preserving source URL, release identity, byte size and cryptographic hash rather than only citing a dataset name. No radar score change warranted.

## EXPERIMENT IMPACT
Before EXP-012 executes, add evaluator receipt fields:
- `first_party_resource_url`
- `catalog_modified_at`
- `resource_last_modified` when exposed
- `first_party_digest` (UNKNOWN until obtained)
- `external_digest_witness_source`
- `external_digest_witness_sha256` (UNKNOWN until exact Mendeley manifest row extracted)
- `external_digest_witness_size`
- `digest_match_status` = UNKNOWN / MATCH / MISMATCH

A MATCH is supporting provenance evidence; a MISMATCH is a hard stop until release identity is reconciled.

## COMMERCIAL IMPACT
No new product feature. This lowers the risk that a future Grid Resilience Calibration / Acceptance Audit is run against mutable or silently changed evaluator bytes while claiming reproducibility.

## NEGATIVE KNOWLEDGE
- Do not treat a catalog modification timestamp as a resource modification timestamp.
- Do not treat an HTTP `Last-Modified` header as a content digest.
- Do not treat a third-party manifest's existence as proof of the specific USECPO hash until the literal manifest row is inspected.
- Do not treat a third-party checksum witness as first-party authority.
- Do not broaden back into outage-model discovery while this narrow provenance gate remains the active bottleneck.

## Next action
Obtain/extract the Mendeley reproducibility package, locate its source/download manifest, and read only the exact USECPO row. Compare its source URL, release identifier, byte size and SHA-256 to direct first-party bytes/digest if and when the official OEDI resource can be downloaded. If the manifest row points to the current `Outage_Dataset_R1.zip`, record the digest as an external witness; if it points elsewhere, preserve the mismatch rather than normalizing it away.
