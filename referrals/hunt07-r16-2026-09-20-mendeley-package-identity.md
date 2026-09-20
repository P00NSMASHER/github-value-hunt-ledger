# Hunt 07 R16 — Mendeley USECPO checksum-witness package identity — 2026-09-20

## Purpose
Advance the remaining CAP-015 / EXP-012 evaluator-provenance gate: determine whether the external Mendeley reproducibility package can bind the current USECPO v2 archive to a stable source URL, release identifier, byte size and SHA-256 without confusing the package hash with the underlying USECPO hash.

## Current first-party USECPO target
- Federal/OEDI record: https://data.openei.org/submissions/6458
- Current v2 archive: https://data.openei.org/files/6458/Outage_Dataset_R1.zip
- Current v2 guideline: https://data.openei.org/files/6458/Guideline_OEDI_Updated.docx
- The federal record currently describes USECPO as public / CC BY 4.0. Artifact-level source semantics remain separate from catalog metadata.

## Newly verified Mendeley package identity
Mendeley dataset DOI `10.17632/r4csg2h2ps.1`, version 1, published 2026-08-24, explicitly names OEDI/USECPO among its public inputs and states that source URLs, release identifiers, file sizes and SHA-256 hashes are retained in download manifests rather than redistributing raw third-party files.

The public Mendeley dataset/file endpoints expose exactly two top-level ZIP records for version 1:

1. `Mendeley_Data_Complete_Package-9jp8EC.zip`
   - file id: `a3b0095f-9345-4bf4-8151-a1dfeec313c6`
   - content id: `182385cd-29ce-4291-8dba-518f346c4461`
   - size: `12,980,662` bytes
   - SHA-256: `3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67`
   - created: `2026-08-21T14:36:21.68Z`
   - download: https://data.mendeley.com/public-files/datasets/r4csg2h2ps/files/a3b0095f-9345-4bf4-8151-a1dfeec313c6/file_downloaded

2. `Mendeley_Data_Complete_Package.zip`
   - file id: `9441d1b0-95f4-4786-9e05-aade3705d731`
   - content id: `2926d559-9906-4d0a-a69c-f70ff9188789`
   - size: `12,980,662` bytes
   - SHA-256: `3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67`
   - created: `2026-08-21T14:36:21.65Z`
   - download: https://data.mendeley.com/public-files/datasets/r4csg2h2ps/files/9441d1b0-95f4-4786-9e05-aade3705d731/file_downloaded

The two apparent package copies are byte-identical by both published size and SHA-256. Treat them as two aliases/copies of **one external witness package**, not as two independent witnesses.

Mendeley version-1 dataset metadata also reports CC BY 4.0 for the package, with the normal caveat that third-party content can require separate permission. That package license does not change the rights of the external USECPO source artifact.

## Negative test: archive is not traversable as a folder
The public Mendeley files endpoint supports `folder_id=root`, but substituting either top-level ZIP file ID as `folder_id` returned `404`. Therefore the uploaded ZIP is not exposed by this API as a virtual directory whose internal manifest can be enumerated.

Direct archive extraction was also unavailable in this runtime: text-oriented fetchers reject or time out on the binary ZIP, the connected desktop was offline, and no paid browser automation was used. No manifest values were guessed.

## What remains UNVERIFIED
- Internal manifest filename/path inside the Mendeley package.
- The literal manifest row for USECPO / `Outage_Dataset_R1.zip`.
- The source release identifier recorded for USECPO by that package.
- The USECPO ZIP byte size recorded by that package.
- The USECPO ZIP SHA-256 recorded by that package.
- Any first-party OEDI SHA-256 for the current USECPO v2 archive.
- Any `MATCH` between an external USECPO digest and first-party bytes/digest.

**Critical distinction:** `3496a7fe...bbc67` is the SHA-256 of the 12,980,662-byte Mendeley reproducibility package. It is **not** the SHA-256 of `Outage_Dataset_R1.zip`.

## Evaluation
- Status: **WATCH / provenance component**.
- Score: **23/30 — A2 B3 C4 D4 E5 F5**. Evidence quality rises one point because the exact external package bytes, file IDs and duplicate identity are now pinned; the core USECPO manifest row is still not extracted.
- `digest_match_status`: **UNKNOWN**.
- Why useful: EXP-012 can now record a stable external-package receipt before attempting internal manifest extraction. Any future package fetched under this DOI/version can be checked against the exact outer SHA-256 before its manifest is trusted.
- Why insufficient: a pinned outer package does not establish the embedded source-file hash, source semantics or first-party digest.

## CAPABILITY DELTA
CAP-015 evaluator provenance is stronger: the external checksum witness now has an exact DOI/version + file IDs + byte size + outer SHA-256 receipt, and apparent duplicate files have been correctly collapsed into one witness.

## GRAPH EDGE
`Mendeley r4csg2h2ps.1 exact outer package` -> STRENGTHENS/CHALLENGES `DATA USECPO v2 artifact identity` -> STRENGTHENS `CAP-015` -> reduces provenance ambiguity in `EXP-012` once the exact internal source row is extracted.

## RADAR SIGNAL
Supports proof-carrying data / prospective-evidence infrastructure: source manifests can carry URL + release + byte size + cryptographic digest. No radar score change until the USECPO row itself and a first-party comparison are verified.

## EXPERIMENT IMPACT
Add/preserve these EXP-012 evaluator receipt fields:
- `external_package_doi = 10.17632/r4csg2h2ps.1`
- `external_package_version = 1`
- `external_package_sha256 = 3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67`
- `external_package_size = 12980662`
- `external_package_file_ids = [a3b0095f-9345-4bf4-8151-a1dfeec313c6, 9441d1b0-95f4-4786-9e05-aade3705d731]`
- `external_witness_count = 1` despite two aliases
- `external_digest_witness_sha256 = UNKNOWN`
- `first_party_digest = UNKNOWN`
- `digest_match_status = UNKNOWN`

A later internal-row or first-party digest mismatch remains a hard stop.

## COMMERCIAL IMPACT
No customer-facing feature is added. This lowers reproducibility and provenance risk for the Grid Resilience Calibration / Acceptance Audit by preventing an outer-package checksum or duplicate alias from being misreported as independent USECPO proof.

## NEGATIVE KNOWLEDGE
- Two files with the same published size and SHA-256 are aliases/copies, not independent checksum witnesses.
- A ZIP file ID is not necessarily a traversable folder ID; the tested Mendeley endpoint returned 404 for both package file IDs.
- Outer-package SHA-256 != embedded third-party source SHA-256.
- Dataset/package CC BY does not automatically relicense third-party source inputs.
- Do not broaden back into outage-model discovery while the exact USECPO manifest-row / first-party-digest gate remains unresolved.

## Next action
Obtain the already-public Mendeley ZIP bytes in a runtime that can download binary public artifacts, verify the outer SHA-256, extract only the source/download manifest, and read the exact USECPO row. Then compare its source URL, release identifier, byte size and SHA-256 against direct first-party OEDI bytes or a first-party published digest. Preserve `UNKNOWN` or `MISMATCH`; never normalize a discrepancy away.
