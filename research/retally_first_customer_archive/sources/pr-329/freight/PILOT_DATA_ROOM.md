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

## Transitive proof-chain verification

The package consumer also reconstructs the population, each finding, the truth
manifest, the sealed incumbent submission and the opened incumbent output using
the existing canonical builders. Every supplied digest must match its rebuilt
contents. Original scope and inter-object links are checked before rebuilding;
reconstruction must not silently repair a mismatched population or submission.

Recomputed self-hashes cannot bypass frozen-population membership, authority
scope/identity, duplicate-record rejection, required fields or valid finding
states. Money must use non-negative integer cents, not booleans, strings or
fractional values. Incumbent finding IDs must be text rather than coerced values.
Clean population rows and REVIEW findings remain present; an empty finding set
or empty incumbent result is valid and does not imply missing source records.
Canonical reordering preserves identity, and a fully rebuilt valid revision
changes identity without mutating caller objects.

These checks apply at `build_pilot_package`, not to every independent consumer of
the lower-level dataclasses. They do not authenticate source files, establish a
complete row-to-original-file lineage mapping, prove historical sealing time,
authorize a customer engagement or repair hosted settlement controls. A caller
can still construct a different internally consistent fictional chain: only
independent source and authorization evidence can establish real-world truth.

Regression suite: `PYTHONPATH=. python -m pytest -q freight/test_pilot_package.py
freight/test_pilot_proof_chain.py`. The existing required release workflow also
runs the complete Freight directory; no new workflow or dependency is needed.

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

## Reference recovery-ledger consumer

`freight.contracts.RecoveryLedger` now validates truth/finding digests, duplicate
members, buyer/unit scope, controlling-authority relationships, and incumbent
output/submission digests before creating accounting state. It copies verified
findings so subsequent caller-side changes cannot alter that ledger snapshot.
Settlement amounts require non-negative integer cents; all four attribution and
ambiguity flags require exact booleans, including on zero or ambiguous paths.
Rejected events do not consume source identities, settlement IDs or capacity.
Valid partial allocations, incumbent exclusions, clean/review-only populations,
canonical ordering and certificate hash formats remain unchanged.

This is the existing **in-memory reference ledger**, not the hosted settlement
service or `SettlementStore`. Its constructor receives no original population
rows, source bytes, or authenticated approval receipts; it cannot independently
prove membership in those original rows, source authenticity, human consent,
historical sealing time, or that a refund actually posted. Legacy source-token
strings remain supported in this reference API. Real financial posting and
customer activation still require their separate controls and evidence.

Regression suite: `PYTHONPATH=. python -m pytest -q
freight/test_recovery_ledger_integrity.py`. The complete Freight release suite
includes these tests without another workflow or dependency.
