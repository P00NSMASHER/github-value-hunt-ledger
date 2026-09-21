# Hunt 07 R23 — USECPO archive/member cryptographic binding and R21 correction

Date: 2026-09-21
Node: 07 — Geo Asset Intel
State: VERIFIED EXTERNAL ARTIFACT / CORRECTION
Primary graph edge: CAP-015 → EXP-012 evaluator provenance

## Result

The public Git LFS object referenced by `Outage_Dataset_R1.zip` was retrieved from `brayo003/Substrate-X-Theory-of-Information-Gravity` at exact revision `9d372ae3cb0c640e39b53808f962726d858d0680` and inspected as binary bytes.

The downloaded archive is exactly 31,260,449 bytes and hashes to:

`44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`

This equals both the repository's Git LFS pointer and the expected archive tuple independently recovered from the Mendeley source manifest in R18. `unzip -t` reports no errors.

The ZIP contains 52 central-directory entries: one directory entry plus 51 files. Every one of the 51 archive files has a byte-identical extracted sibling under the same pinned revision's `data/sxc_validation/outage_data/` tree. Whole-tree comparison produced:

- file members compared: 51
- exact size-and-SHA-256 matches: 51
- missing siblings: 0
- mismatches: 0

This closes the archive-to-member binding gap for the externally witnessed archive bytes. It does not close the separate first-party-authority gate because the file currently served directly by OEDI was not retrieved and hashed in this run.

## Exact locations and revisions

Archive repository: `brayo003/Substrate-X-Theory-of-Information-Gravity`

Revision: `9d372ae3cb0c640e39b53808f962726d858d0680`

Archive path:

`SXC_IGC/Domain-Calibrated_Instability_Framework(DCIF)/dcif_modules/energy_module/data/sxc_validation/6458/Outage_Dataset_R1.zip`

Extracted sibling root:

`SXC_IGC/Domain-Calibrated_Instability_Framework(DCIF)/dcif_modules/energy_module/data/sxc_validation/outage_data/`

Independent downstream repository: `Resilient-Supply-Chain/open-supply-chain-control-tower`

Revision: `d0691e25ee1760cc0c0b5258761c12f8add0a9cb`

## Event-correlated member receipts

The base event-correlated CSVs inside the verified archive have these byte receipts, each matching the sibling extracted file at the pinned archive-repository revision:

| Year | Bytes | SHA-256 |
|---|---:|---|
| 2014 | 145,148 | `92f81ccca4714653d9c433e564fd1ef1b71ddb2b0708ff9cd8a0a8d4f86a9b29` |
| 2015 | 2,095,240 | `bfbcabf562055e16ba1ede7d697756b6df988b5152554ddb1760cb92ed83798a` |
| 2016 | 3,633,081 | `f579c4fa3518c058aec18420eae3beff246397dc6ed21539afa3895a97ae2b9c` |
| 2017 | 4,003,692 | `eb8254668643bb19a008500a99954e355e4083dceff3137d95b75047d3f08413` |
| 2018 | 6,295,273 | `7d232eba1721d751f593d1938bff8731753d662eba1802ee4735a844949bf001` |
| 2019 | 9,085,677 | `7184a938ca83de8d98b2452a52d99f2f7c201b5313547d998f2dc824e6b48ba6` |
| 2020 | 14,431,070 | `d5fb076ad7b7740b8ac90d1609c1aa182f3489dd5e83573f82396661168ce331` |
| 2021 | 19,750,272 | `ca83337cc30259e44c2ba813e447c840f88306ef9fbdc6db91c1469f031dee7f` |
| 2022 | 15,464,271 | `5b998d21c1c13c2265cbad44e8098975f480f9341b904fbc02f0ab528f94ecc9` |
| 2023 | 12,452,488 | `8ac7d34ec2a4dae750d4de4a07562d70d9f1cdb71162bbba85362337e045ad5d` |

The 2023 member was also compared with both ordinary-Git copies at `Resilient-Supply-Chain/open-supply-chain-control-tower@d0691e25ee1760cc0c0b5258761c12f8add0a9cb`. Both are byte-identical to the archive member and carry the same SHA-256 and byte length. This establishes a separately hosted member-byte witness, while not making that downstream repository a source authority.

## Literal 2023 member surface

The first row was read from the actual verified archive member. The literal header is:

`event_id,state_event,Datetime Event Began,Datetime Restoration,Event Type,fips,state,county,start_time,duration,end_time,min_customers,max_customers,mean_customers`

Observed timestamp strings use the shape `YYYY-MM-DD HH:MM:SS` without an explicit offset or zone suffix. This verifies syntax only. It does not establish UTC, local time, daylight-saving handling, or any first-party timezone semantic.

## Correction to R21

R21 correctly showed that no extracted tree exists *inside* the `.../sxc_validation/6458/` directory and correctly preserved the archive/member distinction. Its broader conclusion that the exact pinned repository revision contains no extracted tree and provides zero member-level witnesses is falsified.

At the same exact revision, the extracted tree is a sibling of `6458`, not a child of it:

`.../data/sxc_validation/outage_data/Outage_Dataset/`

A second 2023 copy also exists under:

`.../data/sxc_validation/docs/correlated_outage/eaglei_outages_with_events_2023.csv`

Both 2023 paths resolve to the same Git blob at the pinned revision, and both Git LFS objects declare SHA-256 `8ac7d34e…ad5d`. Fetching the archive and hashing its member converts that pointer evidence into a direct archive/member byte match.

The durable rule from R21 survives in refined form: an archive pointer does not itself prove an extracted tree. Exact-tree inspection and actual member-byte comparison are required. A failed request to an assumed nested path must not be generalized into repository-wide absence.

## Correct provenance state

| Check | State |
|---|---|
| Expected external archive SHA/size | VERIFIED by two public witness surfaces |
| Retrieved Git LFS archive vs expected tuple | MATCH |
| ZIP integrity | PASS |
| Archive members vs pinned extracted sibling tree | 51/51 MATCH |
| 2023 member vs independent downstream repository copies | MATCH |
| Literal member header and timestamp syntax | VERIFIED EXTERNAL ARCHIVE BYTES |
| Timestamp timezone semantics | UNKNOWN |
| Current first-party OEDI archive SHA-256 | UNKNOWN |
| Expected external archive vs current first-party OEDI bytes | UNKNOWN |

## EXP-012 impact

CAP-015 and EXP-012 may now use the member digests above as receipts for the externally witnessed archive and may bind schema/grain work to those exact external bytes. The prior `member-level witness count = 0` state should be withdrawn.

The authority gate remains fail-closed. No evaluation result should be labeled as bound to the current first-party OEDI resource until that directly served file hashes to `44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`.

If the first-party digest matches, the already measured member receipts become cryptographically bound to the authoritative current resource. If it mismatches, stop evaluation and reconcile release identity before proceeding.

The semantic-grain controls established in R19/R22 remain mandatory: release-bound composite event identity, unique county-outage-spell fact grain, a separate spell↔event bridge, and no direct additive burden over flat event-correlated rows.

## Rights boundary

Retrievability, Git LFS identity and byte equality do not determine upstream data rights. Repository licensing must not be treated as relicensing the embedded OEDI/USECPO data. Dataset rights and attribution remain governed by the first-party source record and must be verified separately for deployment.

## VALUE HANDOFF

**CAPABILITY DELTA:** CAP-015 gains full archive-to-extracted-tree byte binding for the expected USECPO archive, including exact receipts for every base 2014–2023 event-correlated member.

**GRAPH EDGE:** The retrieved Git LFS archive and its 51/51 member match STRENGTHEN USECPO evaluator identity and CORRECT R21's repository-wide absence conclusion.

**RADAR SIGNAL:** Proof-carrying evaluators benefit from independently typed receipts for archive, member, transform and authority rather than a single dataset-verified flag.

**EXPERIMENT IMPACT:** EXP-012's external member-schema gate is open; the current first-party digest gate remains closed.

**COMMERCIAL IMPACT:** The Grid Resilience Calibration / Acceptance Audit can now identify exact evaluator member bytes and detect substitution at both archive and member layers, reducing reproducibility risk.

**NEGATIVE KNOWLEDGE:** A 404 at an assumed nested path proves only that path is absent; it does not prove the same tree is absent elsewhere in the exact revision.

## NEXT HIGHEST-VALUE QUESTION

Does the file currently served directly by OEDI at `https://data.openei.org/files/6458/Outage_Dataset_R1.zip` hash to `44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`, and if so what first-party documentation fixes the timezone and missing-value semantics for these exact member bytes?

