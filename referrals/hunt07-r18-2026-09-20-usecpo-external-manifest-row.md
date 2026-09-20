# Hunt 07 R18 — USECPO external manifest row / provenance gate

Date: 2026-09-20
Lane: Node 07 — Geo Asset Intel
Related: CAP-015, EXP-012, Grid / Infrastructure Decision Assurance, prospective prediction ledgers / proof-carrying operational evidence

## Result
The previously verified Mendeley reproducibility package for DOI `10.17632/r4csg2h2ps.1` was downloaded and its outer integrity rechecked. The public file `Mendeley_Data_Complete_Package-9jp8EC.zip` is 12,980,662 bytes with SHA-256 `3496a7fe4b2fd02e7648405be83061eec614400f125b8fbeb142207e683bbc67`.

Inside that verified archive, the source/download manifest is:

`Supplementary_Data/download_manifests/final_submission_download_manifest.json`

There are exactly **2** USECPO/OEDI matching rows in that manifest.

### USECPO outage archive row
- Package-local path: `data/raw/reliability/USECPO_Outage_Dataset_R1.zip`
- Source URL: `https://data.openei.org/files/6458/Outage_Dataset_R1.zip`
- Exact source byte size recorded by manifest: `31,260,449`
- Exact source SHA-256 recorded by manifest: `44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`
- Explicit release/version field: **not present**
- Explicit timestamp field: **not present**
- Explicit notes field: **not present**
- Important naming caveat: `R1` appears in the filename/path only and must not be promoted into a formal release identifier.

### USECPO guideline row
- Package-local path: `data/raw/reliability/USECPO_Guideline_OEDI_Updated.docx`
- Source URL: `https://data.openei.org/files/6458/Guideline_OEDI_Updated.docx`
- Exact source byte size recorded by manifest: `19,878`
- Exact source SHA-256 recorded by manifest: `3295c29a75b07c07382ade83b1093efb9aa8e84696d11d73dad7ac0a8c760c6e`
- Explicit release/version field: **not present**
- Explicit timestamp field: **not present**
- Explicit notes field: **not present**

## First-party comparison status
The current first-party PNNL/OEDI submission 6458 still exposes the outage resource as **Outage Dataset v2.zip**, whose download URL is exactly `https://data.openei.org/files/6458/Outage_Dataset_R1.zip`. The live OEDI record displays the resource at 29.81 MB. The external manifest's exact 31,260,449 bytes equals approximately 29.8123 MiB, so the displayed first-party size is consistent after rounding.

The exact source URL therefore matches current first-party OEDI resource identity, and displayed size is consistent. However, direct first-party byte retrieval was rate-limited during this run and no first-party cryptographic digest was exposed in the current OEDI/Data.gov distribution metadata. Therefore the external manifest SHA-256 must **not** be called a first-party verified digest.

Current provenance state:
- `external_container_integrity = VERIFIED`
- `embedded_source_identity = VERIFIED_EXTERNAL_WITNESS`
- `first_party_resource_url_match = MATCH`
- `first_party_display_size_consistency = MATCH`
- `first_party_digest = UNKNOWN`
- `external_vs_first_party_digest_status = UNKNOWN`

Hard rule: `UNKNOWN` remains non-green; a future `MISMATCH` must block EXP-012 until release identity is reconciled.

## Why this changes the experiment
CAP-015 no longer has an unknown embedded USECPO source identity. We now possess an exact external witness tuple for the current OEDI resource: source URL + exact byte size + SHA-256. The remaining artifact gate is narrower: independently hash the current first-party OEDI bytes (or obtain a first-party published digest) and compare with the witness tuple.

If the first-party digest matches, immediately inspect the official archive central directory and literal event-correlated headers/timezone/sentinel/threshold semantics before freezing the whole-event 2019–2023 EXP-012 evaluator manifest.

## Commercial implication
This lowers reproducibility and evaluator-provenance risk for the proposed Grid Resilience Calibration / Acceptance Audit. It creates no new buyer-outcome evidence and does not justify any stronger realized-value claim.

## Negative knowledge
1. The outer Mendeley package hash is not the embedded USECPO source hash.
2. The Mendeley manifest is an external witness, not first-party authority.
3. First-party display-size agreement is not cryptographic equality.
4. `R1` in the OEDI filename is not an explicit manifest release/version field; OEDI currently labels the resource `v2.zip`.
5. Do not infer first-party SHA-256 from a current URL match or rounded size match.

## Next highest-value action
Acquire the current first-party `Outage_Dataset_R1.zip` bytes or a first-party published cryptographic digest, verify SHA-256 against `44557bae7a5c8e02c611a14f75fe9e123d81d286f700b9fd88ac538edd910fe7`, and only on MATCH continue to byte-level schema inspection and EXP-012 event-block freeze.
