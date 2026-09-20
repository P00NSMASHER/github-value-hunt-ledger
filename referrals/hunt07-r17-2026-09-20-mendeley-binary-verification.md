# Hunt 07 R17 — Mendeley binary verification succeeded; USECPO row capture still pending — 2026-09-20

## Purpose
Advance the remaining CAP-015 / EXP-012 evaluator-provenance gate without broadening into another outage/model search. The immediate target remains the external Mendeley reproducibility package for DOI `10.17632/r4csg2h2ps.1` and its embedded source/download manifest for first-party OEDI/USECPO.

## Benchmark state
Pair 4 CONTROL tasks 23–29 were already complete, so this run resumed the normal Geo Asset Intel mission.

## Current first-party target
- OEDI/DOE USECPO submission: `https://data.openei.org/submissions/6458`
- Current v2 archive: `https://data.openei.org/files/6458/Outage_Dataset_R1.zip`
- Current v2 guideline: `https://data.openei.org/files/6458/Guideline_OEDI_Updated.docx`
- Current federal/OEDI metadata describes USECPO v2 as public / CC BY 4.0. Third-party/source semantics remain separately governed.

## External witness package — independently reverified
Mendeley DOI `10.17632/r4csg2h2ps.1`, version 1, published 2026-08-24, explicitly names OEDI/USECPO among its public inputs and says its download manifests retain source URLs, release identifiers, file sizes and SHA-256 hashes rather than redistributing the raw third-party sources.

The pinned outer package remains:
- canonical alias used this run: `Mendeley_Data_Complete_Package.zip`
- Mendeley file id: `9441d1b0-95f4-4786-9e05-aade3705d731`
- public download: `https://data.mendeley.com/public-files/datasets/r4csg2h2ps/files/9441d1b0-95f4-4786-9e05-aade3705d731/file_downloaded`
- exact byte size: `12,980,662`
- expected/published SHA-256: `3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67`
- duplicate alias remains byte-identical and therefore counts as the same one witness package, not an independent witness.

## New verification this run
A read-only public browser runtime successfully downloaded and inspected the public Mendeley package. It reported:
1. the downloaded outer ZIP SHA-256 matched exactly `3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67`;
2. the archive integrity check passed;
3. the archive contained source/download manifest material;
4. matching manifest rows for OEDI/USECPO were located;
5. a local browser-side report, `outputs/mendeley_manifest_report.html`, was produced containing the exact matching rows, source URLs, release details, byte sizes and hashes.

This materially closes the prior uncertainty over whether the public outer package could actually be fetched and integrity-checked in a binary-capable runtime.

## Important fail-closed boundary: exact embedded row values are NOT yet durable evidence
The browser completion result did **not inline** the exact USECPO row values. Attempts to continue the same completed browser session and read the generated local report failed transiently with an upstream-unavailable error; a fresh rerun was blocked by browser-credit exhaustion. The alternate public text fetch/index paths did not expose the ZIP internals, and no connected remote desktop device was available.

Therefore the ledger must **not** infer or populate any of the following yet:
- exact internal manifest filename/path;
- exact source URL as written in the manifest;
- USECPO release/version identifier as written in the manifest;
- USECPO archive byte size as written in the manifest;
- embedded USECPO SHA-256;
- number of matching USECPO rows;
- whether the manifest row points exactly to the current `Outage_Dataset_R1.zip` bytes;
- any match against a first-party OEDI digest.

Current experiment fields remain:
- `external_package_sha256 = 3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67` — **VERIFIED outer package**
- `external_package_size = 12980662` — **VERIFIED outer package**
- `external_witness_count = 1` — duplicate aliases collapsed
- `external_digest_witness_sha256 = UNKNOWN`
- `first_party_digest = UNKNOWN`
- `digest_match_status = UNKNOWN`

A browser-local generated report is evidence that the rows were found, but until the row values are exported into a durable research record, it is not sufficient to change `UNKNOWN` to `MATCH`.

## Claims tested
### VERIFIED
- The public Mendeley package is retrievable in a binary-capable public browser runtime.
- The downloaded outer package matches the pinned 12,980,662-byte package SHA-256.
- ZIP integrity passes.
- Source/download manifest material and OEDI/USECPO matching row(s) exist inside the verified outer package.

### NOT VERIFIED / NOT YET DURABLY CAPTURED
- Literal USECPO source-manifest row values.
- Embedded USECPO archive SHA-256.
- First-party OEDI archive SHA-256.
- External-vs-first-party digest equality.
- Exact current-v2 CSV headers, timezone, sentinels/null conventions, thresholds/quality flags or `event id` namespace from direct archive bytes.

## Evaluation
- Artifact: Mendeley external provenance witness for USECPO.
- Status: **WATCH / provenance component**.
- Score: **23/30 — A2 B3 C4 D4 E5 F5**, unchanged. Outer binary verification is stronger, but the load-bearing embedded source row and first-party comparison are still unavailable to the durable ledger.
- Commercial effect: lowers provenance risk for the Grid Resilience Calibration / Acceptance Audit, but adds no customer-facing capability and does not justify any outcome claim by itself.

## CAPABILITY DELTA
CAP-015 is strengthened at the outer-artifact layer: the external witness package is now not only metadata-pinned but independently downloaded, hash-verified and archive-integrity-checked. The missing edge is narrower: **row capture + first-party digest comparison**, not binary accessibility.

## GRAPH EDGE
`Mendeley verified outer bytes` -> STRENGTHENS `USECPO evaluator provenance` -> STRENGTHENS `CAP-015` -> reduces one gate in `EXP-012`; exact embedded source row and first-party digest remain unresolved.

## RADAR SIGNAL
Supports RAD-001/RAD-005 proof-carrying operational/prospective evidence: evaluator data can carry independently checkable artifact receipts. No radar-score change because the embedded source digest has not yet been compared to first-party bytes.

## EXPERIMENT IMPACT
EXP-012 can now distinguish two provenance gates:
1. `outer_witness_integrity = VERIFIED`;
2. `embedded_source_identity = UNKNOWN` and `first_party_digest_match = UNKNOWN`.

Do not let gate 1 imply gate 2. `UNKNOWN` or any later `MISMATCH` must hard-stop the evaluator rather than silently normalize source identity.

## COMMERCIAL IMPACT
The Grid Resilience Calibration / Acceptance Audit becomes safer to reproduce: the exact external witness container is now verified. Commercial claims remain unchanged until the USECPO row is durably captured and compared against first-party OEDI evidence.

## NEGATIVE KNOWLEDGE
- Binary download success is not equivalent to durable source-row capture.
- A browser-local report that cannot yet be exported should not silently mutate ledger truth.
- Outer ZIP integrity and checksum do not establish the embedded third-party source checksum.
- Do not spend the next run on another outage dataset/model while this remaining row/digest gate is this narrow.

## Next action
Recover/read the already-generated `outputs/mendeley_manifest_report.html` from the completed public-browser session if that runtime becomes available, or repeat the same public binary inspection only when a free/authorized path can return the matching manifest rows inline. Copy the exact USECPO source URL/release/size/SHA-256 into the ledger, then obtain/hash first-party OEDI `Outage_Dataset_R1.zip` or a first-party published digest and compare. Preserve `UNKNOWN`/`MISMATCH` fail-closed semantics.
