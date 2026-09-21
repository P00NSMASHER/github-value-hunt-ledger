# Hunt 06 R25 Referral — OpenTFRaw independent Thermo oracle

## Target
CAP-013 / EXP-007 integrator and Installed-Base Lab Automation stack owner.

## Finding
`Sigilweaver/OpenTFRaw@63380dff0d25898f5c6e1184087dc590b0d7b6ab` is a strong independent Thermo RAW decoder candidate for the missing fourth-vendor normalization acceptance row.

Unlike ThermoRawFileParser/rawrr-style paths, the inspected `opentfraw` crate directly parses RAW binary structures and does not depend on Thermo's RawFileReader/vendor SDK. Exact-head CI downloads a real PRIDE RAW fixture and passes build/test on Ubuntu, macOS and Windows, Python bindings, mzML structural/XSD validation and cargo audit. The project documents a much broader ~124 GB / 283-file PRIDE-derived corpus and has recent scientific regression history, including a profile m/z correction whose reported bias fell from about `+3.1e-3` to `+2e-6 m/z` in the clearest checked case.

## Why this matters
The prior Thermo acceptance design risked circular validation because `chromConverter`'s default Thermo path delegates to ThermoRawFileParser. OpenTFRaw supplies a separate raw-byte decoder lineage, so the acceptance comparison can occur before shared normalization.

## Recommended EXP-007 Thermo branch
1. Freeze the rights-clean Thermo RAW input and SHA-256.
2. Pin the production decoder/runtime revision.
3. Pin `OpenTFRaw@63380...` independently.
4. Compare predeclared scan-level invariants before either result enters a common normalization layer.
5. Use explicit states `PASS | DISAGREE | UNSUPPORTED | ORACLE_UNAVAILABLE`.
6. Retain Entab as an optional third challenger when the first two decoders disagree.

Minimum comparable fields: scan count/range, retention time, MS order, filter string where semantics align, centroid m/z/intensity or agreed aggregates, TIC/BPC, and precursor/isolation metadata only where both implementations support that field.

## Red-team boundary
Do not infer vendor certification or complete v8–66 correctness. The exact-head CI exercises a small real fixture, not the documented whole corpus. mzML XSD success is structural, not measurement equivalence. OpenTFRaw explicitly documents unresolved isolation-center recovery for some DIA files, so those fields must remain unsupported rather than coerced to agreement. Third-party PRIDE/MassIVE file rights remain source-specific.

## Exact unanswered technical question
**Does the rights-clean `MSV000094032/raw/Lee_CB_03.raw` fixture produce agreement on the predeclared scan-level invariants between pinned ThermoRawFileParser and `OpenTFRaw@63380...`, and which disagreements remain before any shared normalization layer?**

## Durable evidence
See `hunters/21-run25-2026-09-20.md`.
