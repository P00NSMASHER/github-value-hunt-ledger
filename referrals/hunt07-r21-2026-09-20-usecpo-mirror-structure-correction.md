# Hunt 07 R21 — USECPO GitHub mirror structure correction

Date: 2026-09-20
Node: 07 — Geo Asset Intel
State: CORRECTION / NEGATIVE KNOWLEDGE
Primary graph edge: CAP-015 → EXP-012 evaluator provenance

## Why this correction matters

A prior Node 07 referral (`hunt07-r20-2026-09-20-usecpo-second-checksum-witness.md`) correctly identified an archive-level Git LFS pointer for `Outage_Dataset_R1.zip` in `brayo003/Substrate-X-Theory-of-Information-Gravity`, but overclaimed that the pinned repository revision also contained an extracted USECPO `outage_data/Outage_Dataset/` tree and a per-member LFS pointer for `eaglei_outages_with_events_2023.csv`.

Fresh inspection of the exact pinned revision `9d372ae3cb0c640e39b53808f962726d858d0680` falsifies that member-level claim. The correction is important because archive-level byte identity must not be silently upgraded into member-level schema/hash evidence.

## Exact pinned revision inspected

Repository: `brayo003/Substrate-X-Theory-of-Information-Gravity`
Revision: `9d372ae3cb0c640e39b53808f962726d858d0680`
Base path:
`SXC_IGC/Domain-Calibrated_Instability_Framework(DCIF)/dcif_modules/energy_module/data/sxc_validation/6458`

## Verified root structure at the pinned revision

The exact `6458` directory contains five files and no `outage_data/` directory:

1. `417 Annual Summaries 2002-2023.xlsx` — 847,007 bytes
2. `Guideline_OEDI_Updated.docx` — 19,878 bytes
3. `NRI_Table_Counties.csv` — 18,278,419 bytes
4. `Outage_Dataset_R1.zip` — 133-byte Git LFS pointer file
5. `SAIDI_2023.xlsx` — 382,914 bytes

Direct GitHub Contents API requests at this pinned revision returned 404 for both:

- `.../6458/outage_data`
- `.../6458/outage_data/Outage_Dataset/eaglei_outages_with_events_2023.csv`

A fresh recursive Git tree for the same exact revision also did not contain `eaglei_outages_with_events_2023.csv`.

Therefore the prior statement that the pinned mirror contains the extracted outage tree is **FALSIFIED** for this revision.

## Archive-level witness remains verified

The actual pinned `Outage_Dataset_R1.zip` file was re-fetched as text and is a Git LFS pointer with:

```text
version https://git-lfs.github.com/spec/v1
oid sha256:44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7
size 31260449
```

So the GitHub repository remains a valid **archive-level external checksum witness** for:

- expected SHA-256: `44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`
- expected size: `31,260,449` bytes

This continues to agree exactly with the independently extracted Mendeley reproducibility-manifest row for the first-party OEDI URL `https://data.openei.org/files/6458/Outage_Dataset_R1.zip`.

## Claim correction

Withdraw / do not rely on the prior per-member claim:

- `eaglei_outages_with_events_2023.csv` LFS SHA-256 `8ac7d34ec2a4dae750d4de4a07562d70d9f1cdb71162bbba85362337e045ad5d`
- size `12,452,488` bytes
- assertion that this file is present under the pinned revision's extracted USECPO tree

Those member-level values were not reproducible from the exact pinned tree in this run and must not be used as evidence for EXP-012.

## Corrected provenance state

- First-party OEDI resource URL: VERIFIED CURRENT
- External archive checksum witness #1 (Mendeley manifest): VERIFIED
- External archive checksum witness #2 (GitHub LFS pointer): VERIFIED
- External archive witness count: 2
- GitHub extracted-member tree at pinned revision: NOT PRESENT
- Member-level schema/hash witness from this GitHub revision: 0
- Current first-party OEDI SHA-256: UNKNOWN
- First-party vs expected archive digest equality: UNKNOWN
- Literal first-party member headers/timezone/null semantics: UNKNOWN

## EXP-012 impact

Keep the artifact/schema gate closed.

The evaluator may use the expected archive SHA/size as an externally corroborated target, but it must not use the withdrawn per-member SHA or infer schema semantics from a nonexistent extracted tree. The next useful action is either:

1. retrieve and hash the current first-party OEDI archive, or
2. retrieve the public Git LFS object corresponding to the verified archive pointer and inspect its central directory/member bytes as **external archive evidence**, while still keeping first-party equality as the authority gate.

Once archive equality is established, preserve the previously identified semantic controls:

- composite/release-bound event identity rather than bare cross-year `event_id`;
- canonical outage-spell grain `(fips, start_time, end_time)`;
- separate many-to-many spell↔event bridge;
- no additive outage burden directly from flat event-correlated rows;
- source timezone/null semantics must be verified rather than inferred from downstream parsers.

## Negative knowledge / durable rule

**Archive pointer ≠ extracted tree.**

A repository can legitimately pin an archive object through Git LFS without containing extracted member files. Never infer member-level presence, hashes, or schema from an archive pointer. Always inspect the exact pinned Git tree/path before using per-member evidence.

A 404 at an exact path on the exact pinned revision is meaningful evidence that the path is absent at that revision; do not substitute a different revision or default-branch search silently.

## VALUE HANDOFF

**CAPABILITY DELTA:** CAP-015 now distinguishes archive-level artifact witnesses from member-level schema witnesses.

**GRAPH EDGE:** This run CHALLENGES the member-level portion of r20 while preserving its archive-level checksum witness; it STRENGTHENS CAP-015's evidence-type granularity.

**RADAR SIGNAL:** Proof-carrying evaluator infrastructure requires explicit evidence-layer typing (archive, member, schema, authority), not just a checksum field.

**EXPERIMENT IMPACT:** EXP-012 must keep member-level schema semantics unverified until actual archive/member bytes are inspected; the withdrawn per-member SHA cannot be used.

**COMMERCIAL IMPACT:** Prevents a false claim that Grid Resilience Calibration / Acceptance results are bound to externally verified member-level bytes when only the enclosing archive identity is corroborated.

**NEGATIVE KNOWLEDGE:** Never propagate an archive checksum into unverified member hashes/schema; exact-revision tree inspection is mandatory.

## NEXT HIGHEST-VALUE QUESTION

Can the verified public Git LFS object for `Outage_Dataset_R1.zip` be retrieved and inspected for its central directory and literal event-correlated member semantics, while maintaining the current first-party OEDI digest as a separate authority gate?
