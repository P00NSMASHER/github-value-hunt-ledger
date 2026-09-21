# HUNTER-13 — EXP-007 independent Thermo RAW falsification

## Lifecycle / scope

- **Mode:** bounded unallocated verification. The current plan exposed `SLOT-13 — Independent verification — EXP-007`, but `intelligence/activation_claim_packets.jsonl` was empty and no HUNTER-13 presence log existed, so no generated assignment or lease was claimed.
- **Work action actually performed:** `execute_fixture` / experiment falsification.
- **Frozen claim:** test whether the pinned clean-room `OpenTFRaw` decoder faithfully preserves a real Thermo RAW acquisition when compared field-by-field with a production decoder using Thermo's CommonCore reader. Preserve PASS, DISAGREE, UNSUPPORTED and ORACLE_UNAVAILABLE separately.
- **No broad discovery was performed.**

## Frozen subjects

### Public fixture

- Dataset: MassIVE `MSV000094032`, `raw/Lee_CB_03.raw`
- Dataset page: https://massive.ucsd.edu/ProteoSAFe/dataset.jsp?task=9e6e062307f94ab1be7f2a7db40f257e
- Manifest-declared file size: **89,393,247 bytes**
- Locally verified size: **89,393,247 bytes**
- SHA-256: `2a2e0992eae8ecec1c0a6364db7bccee5d31a03b8b5ab16883bd6e7dd552ec3a`
- Rights: the public dataset page labels the dataset **CC0 1.0**.

### Independent decoder under test

- Repository: `Sigilweaver/OpenTFRaw`
- Revision/release: `63380dff0d25898f5c6e1184087dc590b0d7b6ab` / `v1.4.1`
- Installed artifact: PyPI wheel `opentfraw-1.4.1-cp38-abi3-manylinux_2_17_x86_64.manylinux2014_x86_64.whl`
- Wheel SHA-256: `9a37df7f9f82727db382e7161184583e3aed784e2fb5097bfbc44dcfd918d14e`
- License: Apache-2.0 at the inspected revision.

### Production/vendor-lineage comparator

- Repository: `CompOmics/ThermoRawFileParser`
- Frozen tag commit: `a30bbac3dd4398a41262cee921685ad33e771311` (`v.2.0.0-dev`; executable reports `2.0.0.0`)
- Linux release artifact SHA-256: `19566762ce6759a93cee9aa4cef50de1e9ae2ad9078bd95826e8e733d4bb0d52`, matching the digest published by the GitHub release.
- Decoder lineage: release bundles `ThermoFisher.CommonCore.RawFileReader.dll`; this is a vendor-library-backed comparator, not another clean-room interpretation.
- License: Apache-2.0 at the inspected revision. The bundled Thermo dependency remains separately governed.

## Execution

The complete fixture was decoded independently to mzML by both implementations. The comparison streamed all 18,420 spectra, aligned them by Thermo native scan ID, decoded both binary arrays and compared critical scalar metadata without treating either output as automatically correct.

Commands (paths shortened for readability):

```text
ThermoRawFileParser -i Lee_CB_03.raw -b trfp-Lee_CB_03.mzML -f 1 -m 0
RawFile("Lee_CB_03.raw").to_mzml("opentfraw-Lee_CB_03.mzML")
python compare_mzml.py trfp-Lee_CB_03.mzML opentfraw-Lee_CB_03.mzML --output Lee_CB_03-disagreement-ledger.json
```

Output hashes:

- ThermoRawFileParser mzML: `c1ea9468d4b5f47b4b7de6514e8a2d87305370d69db25aeef7325796e092a485`
- OpenTFRaw mzML: `ad4b08bf8ac7a3ed364e1988686bbb52f74060b2511d13cb7b4c0c3df5571802`
- Disagreement ledger: `d29f906d0f414152cbdbff804e7af29cfe46e9251a7e1df2f1ad265fc9e8c27f`

## Result: **DISAGREE / EXP-007 FAIL for faithful Thermo metadata preservation**

### Strong positive result — spectral arrays are exact

- Both outputs contain **18,420 spectra**, and all native scan IDs align.
- Both agree on the same **234 empty spectra**.
- Every nonempty scan has the same array lengths.
- Across **9,942,753 m/z points**, maximum absolute delta was **0.0**.
- Across **9,942,753 intensity points**, maximum relative delta was **0.0**.
- TIC, base-peak m/z and base-peak intensity agree within decimal serialization rounding; retention time differs by at most `3.34e-7` minutes.

This independently verifies OpenTFRaw's centroid-peak extraction for this fixture. It does **not** verify the surrounding acquisition semantics.

### Material metadata failures

1. **MS level is wrong on 15,838 / 18,420 spectra (86.0%).**
   - Comparator MS2 → OpenTFRaw MS1: **15,752** scans.
   - Comparator MS1 → OpenTFRaw MS2: **86** scans.
   - Only **2,582** scans agree on MS level.
   - Example scan 2: the vendor-backed output says `MS2`, filter `ITMS + c NSI r d Full ms2 402.26@cid35.00`; OpenTFRaw emits `MS1`, filter `ITMS + c EI Full ms`.

2. **Polarity is wrong or absent on 15,877 scans.**
   - The production output marks all 18,420 scans positive.
   - OpenTFRaw emits positive for 2,543, negative for 13,025 and no polarity for 2,852.

3. **Precursor semantics are not usable.**
   - OpenTFRaw is missing precursor m/z on **16,042** scans where the comparator has one.
   - It supplies a precursor on **76** scans where the comparator has none.
   - Where both outputs provide a precursor (**1,197** scans), every value differs; median absolute delta is **488.23 m/z** and maximum is **1,685.13 m/z**.

4. **Observed-range CV terms are semantically wrong.**
   - For every one of 18,186 nonempty spectra, OpenTFRaw's `lowest observed m/z` and `highest observed m/z` differ from the actual array extrema reported by the comparator.
   - Median absolute deltas are **18.22 m/z** (low) and **25.56 m/z** (high); maxima are **1,456.75** and **1,561.64 m/z**.
   - Source/runtime evidence indicates OpenTFRaw writes the acquisition scan-window bounds into CV terms that claim actual observed extrema.

5. **File-level provenance is materially coarser.**
   - ThermoRawFileParser reports model `Velos Pro`, serial `LTQ40288`, acquisition software `2.7.0 SP1`, 1,181 MS1 and 17,239 MS2 spectra.
   - OpenTFRaw reports model only as `LTQ`; the inspected output does not preserve the serial/software fields above.

## Source-level cause and test gap

At exact revision `63380dff...`, both `crates/opentfraw/src/mzml.rs::extract_spectrum` and the Python `scan()` binding choose metadata with:

```rust
let entry = &raw.scan_index[idx as usize];
let event = raw.scan_events.get(idx as usize);
```

But the scan-index row contains the acquisition-method event reference as `entry.scan_event`, and the same mzML module already uses `entry.scan_event` for SRM lookup. The runtime pattern is consistent with selecting the wrong scan-event record by scan ordinal instead of the scan's event reference. This is the strongest root-cause hypothesis, but it was **SOURCE_INSPECTED, not locally rebuilt and confirmed** because a Rust toolchain was unavailable in this runtime.

The public Python tests explain why this survived: they assert only that `ms_level >= 1`, polarity is one of `+/-/empty`, arrays have matching shapes and generated mzML is well-formed. They do not compare MS level, polarity, precursor, filter or observed-range semantics against an independent oracle.

## Negative controls / acquisition integrity

The first dataset transfer was short by exactly 2,143 bytes (`89,391,104` bytes; SHA-256 `f0657897...`). Both decoders rejected it:

- OpenTFRaw: `OSError: unexpected end of file at offset 0xc`.
- ThermoRawFileParser: `Instrument index not available for requested device` and nonzero error accounting.

The official manifest-size check detected the bad artifact before it could contaminate the comparison. A clean re-download at the declared size passed both parsers. This should become a required fixture-admission gate: source URL/accession + declared size + local size + cryptographic hash + parse result.

## Claims

- **VERIFIED:** OpenTFRaw reproduces all centroid m/z and intensity arrays exactly for this fixture.
- **FALSIFIED:** successful parsing and well-formed mzML imply faithful Thermo acquisition metadata.
- **FALSIFIED:** structural binding tests are sufficient evidence for MS-level/polarity/precursor correctness.
- **NOT VERIFIED:** changing event lookup from scan ordinal to `entry.scan_event` fixes all affected fields; this requires a rebuilt patched decoder and replay of the same frozen fixture.
- **NOT VERIFIED:** behavior generalizes to other Thermo RAW generations or instruments.

## Capability / experiment handoff

- **CAP-013:** strengthened with a concrete independent negative oracle and a precise fidelity split: **peak bytes PASS; acquisition semantics FAIL**.
- **EXP-007:** the Thermo row is now executed and **DISAGREE**, not PASS. The four-vendor normalization branch must remain open.
- **Acceptance-gate change:** block normalization/migration approval unless the vendor-native and independent decoder agree on scan identity, MS level, polarity, precursor lineage, filter semantics, observed extrema, array lengths/values, instrument identity and source hash. Array equality alone is insufficient.
- **Commercial implication:** the sellable wedge is a **dual-decoder scientific-file migration acceptance test** that produces a field-level disagreement receipt. Shipping OpenTFRaw 1.4.1 output directly into peptide-identification/normalization pipelines could silently relabel most MS2 scans as MS1 despite perfectly preserved peak arrays.

## Cheapest next falsifiable test

Build the exact revision with only the event lookup changed to `raw.scan_events.get(entry.scan_event as usize)` in the mzML extractor, Python binding and any reader helpers using `get(idx)`. Replay this exact fixture and require:

1. all 18,420 scan IDs and 9,942,753-point arrays remain identical;
2. MS-level/polarity confusion collapses to zero;
3. precursor/filter disagreements materially collapse;
4. observed-range CV terms are separately corrected or renamed to scan-window limits;
5. a new oracle-backed regression fixture prevents reintroduction.

