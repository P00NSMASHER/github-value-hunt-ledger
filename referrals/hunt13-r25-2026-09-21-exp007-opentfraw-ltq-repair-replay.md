# HUNTER-13 — EXP-007 OpenTFRaw LTQ repair replay

## Lifecycle / scope

- **Mode:** bounded unallocated verification. Pair 7 CONTROL tasks 44–50 remain complete, and the live activation log still contains no HUNTER-13 activation, so no assignment or lease was claimed.
- **Work action:** replay the cheapest falsifiable follow-up from the prior Thermo RAW disagreement: rebuild the exact OpenTFRaw revision with a minimal parser repair and test it on the same frozen fixture and independent vendor-lineage comparator.
- **No broad discovery, upstream write, issue filing or release action was performed.**

## Frozen inputs

- Fixture: MassIVE `MSV000094032/raw/Lee_CB_03.raw`, 89,393,247 bytes, SHA-256 `2a2e0992eae8ecec1c0a6364db7bccee5d31a03b8b5ab16883bd6e7dd552ec3a`, dataset-labelled CC0 1.0.
- Target source: `Sigilweaver/OpenTFRaw@63380dff0d25898f5c6e1184087dc590b0d7b6ab` (`v1.4.1`, Apache-2.0).
- Comparator: `CompOmics/ThermoRawFileParser@a30bbac3dd4398a41262cee921685ad33e771311` (`v.2.0.0-dev`) using the bundled Thermo CommonCore reader.
- Frozen comparator mzML SHA-256: `c1ea9468d4b5f47b4b7de6514e8a2d87305370d69db25aeef7325796e092a485`.

## Prior hypothesis falsified

The prior run proposed that `scan_events.get(idx)` should be replaced by `scan_events.get(entry.scan_event)`. Rebuilding that exact change disproved the hypothesis:

- MS-level disagreements improved only from **15,838** to **13,794**.
- Polarity disagreements/missingness improved from **15,877** to **11,491**.
- The fixture has `ntrailer=18,420` for 18,420 scans and `nsegs=1`; there is one trailer event per scan. `entry.scan_event` is the acquisition-method event number within the segment, not the ordinal of the per-scan trailer record.

This matters because the first run's strongest source-cause claim was wrong even though the field-level failure itself was real. The independent replay preserved the disagreement and corrected the diagnosis rather than forcing the expected patch to pass.

## Actual cause

OpenTFRaw v1.4.1 infers v66 scan-event sizes from the address span. When the span is not uniform, it recognizes only a tribrid layout (232-byte primary events and 344-byte dependent events), then otherwise falls back to a floor-average event size.

For this LTQ file:

- scan-event stream bytes: **4,207,304**
- trailer events: **18,420**
- vendor-backed truth: **1,181 MS1** and **17,239 MS2**
- actual LTQ total event sizes: **176 bytes for primary** and **232 bytes for dependent**
- exact identity: `1,181 × 176 + 17,239 × 232 = 4,207,304`

The floor-average path selected 228 bytes per event, desynchronizing the 136-byte preamble after the first record. Direct boundary inspection confirmed the next valid MS2 preambles at offsets 176, 408, 640 and 872 from the stream start: one 176-byte primary event followed by 232-byte dependent events.

## Repair tested

The local patch, applied only to the frozen source checkout, made three bounded changes:

1. Add the exact LTQ variable layout `(primary=176, dependent=232)` beside the existing tribrid layout and accept it only when its solved primary/dependent counts reproduce the full stream byte span exactly.
2. Treat only the 208-byte dependent body as the special tribrid body layout; parse the 96-byte LTQ dependent body with the existing legacy v66 body parser.
3. Emit mzML `lowest observed m/z` / `highest observed m/z` from the first and last decoded m/z values, not the scan-index acquisition-window bounds.

The earlier `entry.scan_event` changes were reverted. No peak decoding code was changed.

## Replay result: released v1.4.1 remains DISAGREE; locally patched exact revision materially PASSES this fixture

Compared with the same Thermo CommonCore-backed mzML:

- **18,420 / 18,420 scan IDs align.**
- **MS level: zero disagreements** — 1,181 MS1 and 17,239 MS2 on both sides.
- **Polarity: zero disagreements** — all 18,420 positive on both sides.
- **Precursor m/z: present for the same 17,239 MS2 spectra and within `5.01e-7 m/z` serialization delta.**
- **Observed low/high m/z: zero value disagreements on all 18,186 nonempty spectra, within `5.01e-7 m/z`.**
- **Arrays remain exact:** all 9,942,753 m/z values have maximum absolute delta `0.0`; all 9,942,753 intensity values have maximum relative delta `0.0`.
- Retention time, TIC and base-peak fields remain within the prior decimal serialization tolerances.

Patched mzML SHA-256: `e45c50ab4bb2bc3b5fce00687cfa92ac491b03208ff40c1c049bf1f4460ad675`.

Comparison ledger SHA-256: `083fee7f5a63e1fa358b05b7406ca06eb4146e6d3d273f162e7d9f747449e5a0`.

All OpenTFRaw workspace tests passed after the patch: **107 unit tests, 1 conformance test and 5 doc tests; zero failures**. `cargo fmt --check` and `git diff --check` also passed.

## Residual disagreements and limits

- The 234 spectra whose arrays are empty remain a representation difference: ThermoRawFileParser omits the observed-range CV terms, while the shared `openmassspec-core` writer emits `0.0/0.0` when no effective range exists. This is not a peak-value disagreement, but it should be repaired because zero is not an observed m/z.
- File-level model/serial/acquisition-software provenance was not changed; the released OpenTFRaw output remains coarser (`LTQ`) than the vendor-backed output (`Velos Pro`, serial and acquisition software).
- The repair is verified on one real LTQ v66 fixture only. The exact-span guard protects the already-supported layouts, but a multi-instrument regression corpus is still required before release confidence.
- No upstream patch or issue was submitted. The released v1.4.1 artifact is still unsafe for metadata-dependent use on this fixture.

## Claims

- **FALSIFIED:** the scan-index `entry.scan_event` field is the correct index into the per-scan trailer vector for this file.
- **VERIFIED:** the dominant metadata failure is event-stream desynchronization caused by a missing LTQ v66 variable-size layout.
- **VERIFIED on this fixture:** the exact-span LTQ layout repair restores MS level, polarity, precursor lineage and nonempty observed-range semantics without changing a single decoded peak value.
- **FALSIFIED:** OpenTFRaw's current shape/type/well-formedness tests would detect this parser desynchronization; all existing tests pass both before and after the semantic repair.
- **NOT VERIFIED:** the patch generalizes to other LTQ generations or mixed MSn methods.

## Capability / experiment handoff

- **CAP-013:** gains a concrete, independently replayed repair primitive rather than only a negative oracle.
- **EXP-007:** keep the released OpenTFRaw v1.4.1 Thermo row as **DISAGREE**. Add a separate patched-candidate result: **material field PASS on the frozen fixture, with empty-spectrum/provenance caveats**.
- **Acceptance gate:** require real oracle-backed fixtures that exercise every supported event-body layout. A parser's self-tests must assert scan-level semantic truth, not merely successful construction and valid XML.
- **Commercial implication:** the dual-decoder acceptance test is not only diagnostic. It can isolate a byte-layout defect, prove a bounded repair against the same immutable acquisition and produce a before/after field receipt suitable for migration approval.

## Cheapest next falsifiable test

Promote this fixture into an oracle-backed regression test and replay the patch across one LTQ v66 fixture with MS3 and one already-supported tribrid v66 fixture. Require exact stream-span classification, zero scan-level MS/polarity/precursor regressions, identical peak arrays, and omission—not `0.0`—of observed-range terms for empty spectra.
