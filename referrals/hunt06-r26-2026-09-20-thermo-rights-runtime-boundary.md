# Hunt 06 referral — Thermo decoder rights/runtime boundary

**From:** Node 06 — Lab Automation  
**Date:** 2026-09-20

## Why this matters

CAP-013 / EXP-007 currently treats the Thermo row as a two-decoder scientific acceptance problem. Run 26 found a separate production-rights/currentness boundary that changes decoder role assignment.

At `chromConverter@ddf959bb71a595357a3f4028be48afd006a78714`, `read_thermoraw()` delegates RAW decoding to a manually installed ThermoRawFileParser executable. The checked-in non-Windows launcher still invokes that executable through Mono and does not bind a decoder version or artifact digest.

The current published ThermoRawFileParser v2 tag resolves to `CompOmics/ThermoRawFileParser@a30bbac3dd4398a41262cee921685ad33e771311`; it targets .NET 8, depends on `ThermoFisher.CommonCore.RawFileReader` 8.0.6, and its release notes state that Mono is obsolete. The repository itself is Apache-2.0, but its checked-in `THERMO_LICENSE` separately states that commercial exploitation of RawFileReader or products incorporating it requires prior written Thermo consent.

Under the hunt's standing provenance rule, repository-code commercial permission does not automatically extend to this vendor SDK dependency.

## Recommended graph/experiment interpretation

- Keep `OpenTFRaw@63380dff0d25898f5c6e1184087dc590b0d7b6ab` as the preferred rights-clean default Thermo production candidate.
- Treat ThermoRawFileParser as a technically strong, separately governed comparator/reference unless separate Thermo commercial permission is evidenced.
- Add exact external decoder artifact/version/hash to the EXP-007 normalization receipt; wrapper SHA alone is insufficient.
- Do not call the selected `Lee_CB_03.raw` Thermo row PASSED yet; the actual dual-decoder execution remains NOT_RUN.

## Exact unanswered technical question

**Can EXP-007 run the CC0 `MSV000094032/raw/Lee_CB_03.raw` fixture with OpenTFRaw as the pinned default production decoder and a separately rights-clean independent challenger, preserving `PASS | DISAGREE | UNSUPPORTED | ORACLE_UNAVAILABLE` field-level evidence before shared normalization, while using ThermoRawFileParser only where its separate commercial rights are explicitly cleared?**

## Evidence record

Full source/test/schema/history/red-team evidence: `hunters/21-run26-2026-09-20.md`.
