# Freight Recovery — Pilot Data Room Manifest

Updated: 2026-10-13

Every controlled pilot should have one machine-checkable source manifest before truth-building begins.

## Required scope

- buyer ID;
- business unit;
- source ID;
- source type;
- SHA-256;
- authorization state;
- read-only state;
- whether the source contains credentials/secrets;
- retention days;
- optional source locator.

The canonical implementation is `freight/pilot_package.py`.

## Allowed source types

- `invoice`
- `authority`
- `shipment_evidence`
- `identity_map`
- `incumbent_output`
- `settlement_observation`
- `other`

The pilot package itself requires at minimum an invoice source, an authority source and the sealed incumbent-output source. Shipment evidence is added when the supported rule requires it.

## Fail-closed rules

A source does not enter the pilot evidence room when:
- buyer or BU scope differs;
- authorization is not documented;
- pilot access is not read-only;
- SHA-256 is missing/malformed;
- credentials/secrets are present;
- retention is undefined/non-positive.

## Package-time revalidation

`build_pilot_package` reconstructs the data-room manifest through the existing
source validator and checks its canonical SHA-256 before consuming it. A
constructed or replaced dataclass is not proof that its entries were validated.
Changed entries cannot retain an old manifest digest; recomputing the digest
cannot bypass scope, permission, read-only, secret, retention or duplicate-ID
checks. A non-pilot read-only exception is never inherited by a pilot package.
Canonical source reordering preserves package identity; a valid revised manifest
produces a new package identity without mutating the supplied manifest.

This is metadata consistency and policy validation, not verification of original
source bytes, authentic customer consent, external provenance, hosted access
controls or recovered funds. Those still require separate evidence.

## Blind-order chain

1. Build source/data-room manifest.
2. Freeze population.
3. Seal incumbent source SHA-256 against buyer/BU + population.
4. Build/freeze buyer-owned truth.
5. Open incumbent output from the previously sealed source.
6. Build final pilot-package hash tying:
   - data-room manifest;
   - population;
   - truth;
   - sealed incumbent submission;
   - opened incumbent output.

This chain proves deterministic content binding/order inside the application. It does **not** independently attest historical wall-clock time.
