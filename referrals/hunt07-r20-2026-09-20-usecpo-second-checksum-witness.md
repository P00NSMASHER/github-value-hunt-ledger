# Hunt 07 R20 — USECPO second independent checksum witness

Date: 2026-09-20
Node: 07 — Geo Asset Intel
Target: CAP-015 / EXP-012 evaluator-byte provenance

## Summary
A second public, independently hosted witness now pins the same `Outage_Dataset_R1.zip` byte identity already recorded from the Mendeley reproducibility manifest.

At repository revision `brayo003/Substrate-X-Theory-of-Information-Gravity@9d372ae3cb0c640e39b53808f962726d858d0680`, the file

`SXC_IGC/Domain-Calibrated_Instability_Framework(DCIF)/dcif_modules/energy_module/data/sxc_validation/6458/Outage_Dataset_R1.zip`

is a Git LFS pointer with:

- SHA-256: `44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`
- size: `31260449` bytes

This exactly matches the previously extracted USECPO row in Mendeley DOI `10.17632/r4csg2h2ps.1`.

The LFS pointer was introduced by commit `994a3ecc9636410fb36b94d1a521d178216cbee1` dated 2026-03-13. The same repository snapshot also contains copies of the USECPO companion resources under a `6458/` directory, including `Guideline_OEDI_Updated.docx` at 19,878 bytes, and an extracted `outage_data/Outage_Dataset/` tree whose event-correlated CSVs are themselves represented by Git LFS pointers. Example: `eaglei_outages_with_events_2023.csv` is pinned at SHA-256 `8ac7d34ec2a4dae750d4de4a07562d70d9f1cdb71162bbba85362337e045ad5d`, size 12,452,488 bytes.

## Why this matters
This is independent corroboration of the expected USECPO v2 source artifact identity. It reduces the chance that the Mendeley manifest contains a transcription or packaging mistake and gives EXP-012 a second external byte-identity witness.

It does **not** close the first-party gate. Current Data.gov/OEDI metadata still points `Outage Dataset v2.zip` to `https://data.openei.org/files/6458/Outage_Dataset_R1.zip`, but does not publish a cryptographic digest. The current catalog was last updated 2026-07-27 and checked 2026-09-10; August 2026 DOE download metrics show the exact URL remained actively served. Direct first-party binary retrieval remains unavailable from the current runtime, so `first_party_digest = UNKNOWN` and `digest_match_status = UNKNOWN` must remain unchanged.

## Evidence classification
- Git LFS pointer at pinned GitHub revision: **VERIFIED**.
- Exact match to prior Mendeley external witness SHA/size: **VERIFIED**.
- First-party OEDI URL identity/currentness: **VERIFIED via federal metadata**.
- First-party OEDI SHA-256 equality: **UNVERIFIED**.
- Mirror provenance proving it was fetched directly from OEDI rather than copied from another mirror: **UNVERIFIED**.
- Mirror repository's broader scientific claims: **NOT USED / NOT EVIDENCE**. The repository is retained only as a byte-identity witness for public USECPO artifacts.

## Score — checksum witness component
A3 / B3 / C4 / D4 / E4 / F5 = **23/30 WATCH**.

Reason: meaningful provenance/risk reduction and excellent artifact-level specificity, but no independent outcome semantics, no first-party authority, and no standalone commercial wedge.

## Capability delta
CAP-015 gains a second independently hosted external checksum witness for the USECPO v2 archive plus per-file LFS digests for extracted evaluator files. This strengthens artifact reproducibility but does not replace first-party verification.

## Graph edge
`brayo003/Substrate-X-Theory-of-Information-Gravity@9d372ae...` -> **STRENGTHENS** USECPO artifact identity -> **STRENGTHENS** CAP-015 -> EXP-012.

## Experiment impact
EXP-012 can now freeze the expected archive identity as:

- resource URL: `https://data.openei.org/files/6458/Outage_Dataset_R1.zip`
- expected bytes: `31,260,449`
- expected SHA-256: `44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`
- external witness count: **2 independent public surfaces** (Mendeley manifest + Git LFS pointer), while explicitly keeping first-party digest status UNKNOWN.

The extracted-file LFS pointers may later support a finer-grained evaluator manifest, but they are not yet cryptographically proven to be the exact members of the referenced ZIP because the ZIP itself has not been opened from this mirror/first party in the current run.

## Commercial impact
No new product feature. Lower provenance/substitution risk for a Grid Resilience Calibration / Acceptance Audit and cheaper future reproducibility checks.

## Negative knowledge / guardrails
1. Two matching external checksum witnesses are not first-party authority.
2. A Git LFS pointer proves the intended object hash/size in that repository, not that the LFS object was fetched from OEDI.
3. Companion extracted-file hashes should not be asserted as ZIP-member hashes until the archive/member relationship is independently verified.
4. The mirror repository's unrelated scientific claims are not validated by the presence of copied OEDI data and must not contaminate USECPO evidence.
5. Do not resume generic outage-model discovery while the first-party artifact gate is still the highest-value missing edge.

## Searches / methods used
1. Direct first-party artifact retrieval attempt from OEDI — blocked by runtime DNS/download access.
2. Fresh federal metadata/currentness verification via Data.gov/OEDI and DOE download metrics.
3. Global exact-digest GitHub code search, which surfaced the independent Git LFS pointer.
4. Commit/file archaeology on the mirror to pin the pointer's introduction date and inspect companion/extracted resource identities.

## Next highest-value question
Can the currently served first-party OEDI `Outage_Dataset_R1.zip` be hashed directly and, on exact SHA-256 match, can its central directory and raw event-correlated CSV timestamp/null semantics be frozen before EXP-012 scoring?
