# Freight Recovery — Pilot Data Room Manifest

Updated: 2026-09-20

Every controlled pilot should have one machine-checkable **READY launch authorization receipt** before any source enters the data room, followed by one machine-checkable source manifest before truth-building begins.

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

## Launch + blind-order chain

1. Re-run the final Pilot Launch Gate and issue a deterministic launch authorization receipt for the exact engagement, buyer/BU, release provenance, rights state and environment evidence.
2. Build the source/data-room manifest bound to that unexpired authorization receipt/hash.
3. Freeze population.
4. Seal incumbent source SHA-256 against buyer/BU + population.
5. Build/freeze buyer-owned truth.
6. Open incumbent output from the previously sealed source.
7. Build final pilot-package hash tying:
   - data-room manifest;
   - population;
   - truth;
   - sealed incumbent submission;
   - opened incumbent output;
   - engagement ID + launch-authorization receipt hash/expiry.

This chain proves deterministic content binding/order inside the application. It does **not** independently attest historical wall-clock time.
