# Freight Recovery — Rights Evidence Diligence

Updated: 2026-09-23

This process separates **what the repository says about component rights** from
**the executed evidence that supports those statements**.

It is an operational diligence control, not a legal opinion.

## Why this exists

A commercial-use permission does not automatically establish:
- hosted/SaaS rights;
- assignment;
- sublicensing;
- redistribution;
- OEM use;
- change-of-control treatment.

The repository must not silently turn a user assertion or public-license
observation into a transferable buyer/acquirer claim.

## Canonical files

- `freight/COMPONENT_RIGHTS_REGISTRY.json` — operational rights state.
- `freight/RIGHTS_EVIDENCE_MANIFEST.json` — evidence metadata only.
- `freight/rights_evidence.py` — fail-closed consistency validator.
- `freight/RIGHTS_EVIDENCE_TRANSFER.md` — exact transfer checklist for
  executed evidence held in another account or diligence room.

Executed license/permission document bytes belong in the actual diligence room,
not this source repository.

## Evidence promotion rule

A scope can become `CONFIRMED_ALLOWED`, `CONFIRMED_DENIED`, or
`NOT_APPLICABLE` only when:
1. the executed evidence object is stored in the diligence room;
2. its location/reference is recorded;
3. its SHA-256 is recorded;
4. the evidence status is `ATTACHED_VERIFIED`;
5. the operational registry and evidence manifest are reconciled.

If any of those are absent, the scope stays `UNKNOWN_REVIEW` or
`USER_ASSERTED_NOT_ATTACHED`.

## Current external gaps

### Trenova
The repository records the user's separate commercial-use license assertion for
the pinned revision, but the source repo does **not** currently contain executed
evidence proving hosted/SaaS, assignment, sublicensing or change-of-control
scope.

### Opstrax
The repository records the user's separate commercial permission assertion for
the pinned revision, but the source repo does **not** currently contain executed
evidence proving hosted/SaaS, assignment, sublicensing or change-of-control
scope.

## Stage behavior

### Controlled pilot
Any non-permissively licensed runtime component that relies on separate
permission requires `ATTACHED_VERIFIED` executed evidence and a
`CONFIRMED_ALLOWED` commercial-use scope. The current repository manifest is
therefore **BLOCKED** for a controlled pilot; a private diligence-room manifest
may clear the gate after verification without committing document bytes.

### Annual / acquirer diligence
Commercial-use must be confirmed allowed. Hosted-SaaS and change-of-control
scope must be resolved through verified evidence, and an explicitly denied
required right remains a blocker.

No code path should infer those rights from public visibility or from a generic
commercial-use statement.
