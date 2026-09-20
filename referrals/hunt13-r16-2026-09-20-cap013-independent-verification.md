# Hunt 13 R16 — Independent verification of CAP-013 cross-vendor scientific-data normalization

Date: 2026-09-20
Assignment: `ASSIGN:e4c9406f29d5:slot-13`
Strategy: `STRAT:evaluation-target-independence`
Objective: `OBJ:independent-evaluation`
Target hypothesis: CAP-013 / Installed-Base Lab Automation claim that heterogeneous proprietary analytical-instrument exports can be normalized into a common evidence model, while buyer-grade acceptance requires semantic verification beyond parse success.

## Verdict

**SUPPORTED WITH NARROWING.** Independent implementation families confirm that cross-vendor analytical-instrument normalization is a real, mature engineering boundary with significant reusable value. They also show that successful parsing/schema-valid output is not sufficient evidence of semantic fidelity. Production acceptance should be field-level, vendor/revision-specific, and fail closed on missing or ambiguous scientific semantics.

## Strong independent verifier — Sigilweaver OpenMassSpec family

### openmassspec-core
- Repository: https://github.com/Sigilweaver/OpenMassSpecCore
- Exact revision inspected: `0be789a407baad573107a0cfed7e0673bb83be27` (v1.5.0, 2026-08-12)
- Public license: Apache-2.0. Third-party scientific standards, public fixtures and vendor-format rights remain separately governed.
- Role: common normalized spectrum/run model plus cross-vendor conformance harness.
- Source evidence: `src/conformance.rs` checks array-length consistency, per-peak mobility length, TIC vs summed intensity, base-peak intensity vs max intensity, MS2+ precursor presence, retention-time monotonicity within acquisition stream, and spectrum index ordering. Failures surface structured `ConformanceError` values with native IDs. Unit tests deliberately inject TIC mismatch, missing precursor, RT regression and mobility-array mismatch.
- Important boundary: empty spectra are intentionally allowed and the harness does not prove every scientifically relevant vendor field is preserved. Treat it as a semantic invariant layer, not universal ground truth.

### OpenTFRaw — Thermo RAW
- Repository: https://github.com/Sigilweaver/OpenTFRaw
- Exact revision inspected: `63380dff0d25898f5c6e1184087dc590b0d7b6ab`
- Evidence: `crates/opentfraw/tests/conformance.rs` runs the shared `openmassspec-core` invariant suite against a real Thermo RAW fixture. CI downloads a public PRIDE PXD054004 RAW file before `cargo test`, then separately converts centroid/profile/indexed mzML and validates against PSI-MS XSD. Fuzz smoke tests also seed from the real RAW fixture.

### OpenWRaw — Waters MassLynx RAW
- Repository: https://github.com/Sigilweaver/OpenWRaw
- Exact current revision inspected: `13db611f632e2a3e19c4470f2666e0536c65292e`
- Evidence: `crates/openwraw/tests/conformance.rs` runs the same normalized invariant suite against a real Waters PXD058812 bundle; CI explicitly downloads that public Waters bundle on Linux/macOS before `cargo test`, then emits plain/indexed mzML and validates each against PSI-MS schemas.

### Umbrella release evidence
- Repository: https://github.com/Sigilweaver/OpenMassSpec
- Exact current revision inspected: `0793a6c4715a806ca3ab3d4bba9ae19ec423f819` (2026-09-18)
- `STACK.md` pins a multi-reader release family including `openmassspec-core 1.5.0`, `opentfraw 1.4.1`, `opentimstdf 1.3.3`, `openwraw 1.2.9`, `openaraw 0.1.7`, and `opensxraw 0.2.5`.

### Value score
**27/30 — A3 B4 C5 D5 E5 F5.** Rare because the valuable artifact is not merely another parser: it is a shared cross-vendor semantic contract with real vendor fixtures and negative invariant tests. It is narrower than Allotropy and concentrated on mass spectrometry, so it does not displace the current CAP-013 leader.

## Mature independent comparator — ProteoWizard/pwiz

- Repository: https://github.com/ProteoWizard/pwiz
- Exact revision inspected: `e5420479ff26596a1e23a254d71e8e254872c93a` (2026-09-19)
- Public license: Apache-2.0; vendor-supplied libraries/formats remain separately governed.
- `pwiz/data/vendor_readers/ExtendedReaderList.cpp` instantiates readers for ABI/WIFF2/T2D, Agilent, multiple Bruker formats, Mobilion, Shimadzu, Thermo, UIMF, UNIFI and Waters.
- `Reader_Thermo_Test.cpp` verifies controlled-vocabulary mappings for instrument model/configuration/ionization/analyzer/detector semantics and runs the shared vendor-reader harness against RAW data.
- `VendorReaderTestHarness.cpp` converts vendor data into a common `MSData` model, serializes/reloads standard formats, and compares normalized structures using `Diff<MSData,...>`; round-trip paths assert zero semantic diff under format-specific tolerances/configuration.
- Current first-party documentation states that proprietary-format access depends on vendor-supplied libraries and separate vendor requirements.

### Adversarial evidence / limits
- ProteoWizard issue #3387 (2025-03-06) reports Waters DDA mzML missing isolation-window lower/upper offsets.
- ProteoWizard issue #3571 (2025-07-31) reports Waters Xevo DIA conversion with incorrect/repeated isolation-window values, identical scan times, and missing instrument model/serial metadata.
- ProteoWizard issue #1891 documents a Bruker BAF decode failure that required a vendor SDK update.
- These are not reasons to reject normalization. They prove the acceptance boundary: schema-valid or successfully converted output can still lose economically/scientifically material semantics, and vendor runtime revisions can change correctness.

### Value score
**25/30 — A3 B4 C5 D3 E5 F5.** Mature, broad and well tested, but less rare as a discovery and operationally dependent on vendor libraries for proprietary formats.

## Capability / experiment implications

### Capability delta
Strengthen CAP-013 with an explicit **Cross-Vendor Semantic Conformance Gate**. The reusable ability is not just `vendor file -> common schema`; it is `vendor file -> normalized model -> independent invariant/equivalence checks -> PASS/REVIEW with field-level evidence`.

### Graph edge
- `Sigilweaver/OpenMassSpecCore@0be789a...` -> STRENGTHENS CAP-013 as an independent semantic-conformance oracle.
- `Sigilweaver/OpenTFRaw@63380df...` + `Sigilweaver/OpenWRaw@13db611...` -> TEST CAP-013-style normalized invariants on real vendor fixtures from two independent raw-format families.
- `ProteoWizard/pwiz@e542047...` -> INDEPENDENTLY VALIDATES the cross-vendor abstraction premise and CHALLENGES parse/schema-success-as-fidelity.
- CAP-013 + CAP-017 continues to ENABLE Installed-Base Lab Automation / EXP-007, but normalization acceptance should be a distinct precondition to workflow evidence.

### Radar signal
RAD-010 Installed-base scientific operations adapters is independently strengthened. No numeric score change is warranted from repository evidence alone.

### Experiment impact
Add a normalization acceptance layer ahead of EXP-007 using customer-authorized or rights-clean fixtures. Per installed vendor/revision, freeze the source hash and assert at minimum: spectrum/record count, instrument identity where available, timestamps/retention time, m/z-intensity array alignment, mobility arrays where present, TIC/base-peak consistency, precursor/isolation-window linkage, acquisition-method metadata needed by downstream workflows, source-file provenance, and deterministic/round-trip equivalence where the target format supports it. Missing required semantics => REVIEW/unsupported, never silent default.

### Commercial impact
Refine the first paid wedge to an **Installed-Format Normalization Acceptance Test**: buyer provides 5–10 representative authorized instrument exports; deliver a format/revision compatibility matrix, field-level semantic diff report, normalized evidence pack and regression fixtures before any automation project. This is easier to sell and safer than promising broad lab automation before the installed estate is proven readable with sufficient fidelity.

### Negative knowledge
Do not treat `file opened`, `conversion exited 0`, `mzML XSD valid`, `record count > 0`, or one successful fixture as scientific semantic equivalence. Vendor DLL/SDK versions, acquisition modes and uncommon metadata surfaces require explicit regression evidence. A common schema without a conformance oracle can merely standardize the wrong answer.

## Strongest objection
The independent evidence is concentrated in mass spectrometry, whereas CAP-013/Allotropy spans broader analytical instrumentation. Therefore this run validates the **general architecture and acceptance discipline**, not full format-by-format coverage of every Allotropy adapter.

## Next highest-value question
Can the same hand-authored semantic-conformance matrix expose one real field-level disagreement between Allotropy and an independent parser/export path on a rights-clean overlapping instrument format, without using either implementation as the gold standard?
