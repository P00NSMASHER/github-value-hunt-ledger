# Freight Recovery — Rights Evidence Diligence

Updated: 2026-09-23

This process separates **what the repository says about component rights** from
**the evidence object that supports those statements**.

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

For the controlled-pilot **commercial-use** scope, the owner/operator may supply
a dated attestation that is stored as an evidence object, fingerprinted by
SHA-256, and marked `ATTACHED_VERIFIED`. That attestation can support
`commercial_use=CONFIRMED_ALLOWED` for the pilot gate.

Broader rights — hosted/SaaS, assignment, sublicensing, redistribution and
change-of-control — are **not** inferred from that attestation. Those remain
`UNKNOWN_REVIEW` until separately documented, and annual/acquirer diligence
continues to require stronger scope-specific evidence.

## Current external gaps

### Trenova
Commercial use for the pinned revision is now **CONFIRMED_ALLOWED** for the
controlled-pilot scope based on the owner/operator attestation in
`freight/RIGHTS_OWNER_ATTESTATION_2026-09-23.md`.
Hosted/SaaS, assignment, sublicensing and change-of-control remain unresolved.

### Opstrax
Commercial use for the pinned revision is now **CONFIRMED_ALLOWED** for the
controlled-pilot scope based on the same owner/operator attestation.
Hosted/SaaS, assignment, sublicensing and change-of-control remain unresolved.

## Stage behavior

### Controlled pilot
Any non-permissively licensed runtime component that relies on separate
permission requires an `ATTACHED_VERIFIED` commercial-use evidence object and
a `CONFIRMED_ALLOWED` commercial-use scope. The current repository manifest now
meets that controlled-pilot requirement through the dated owner/operator
attestation.

### Annual / acquirer diligence
Commercial-use must be confirmed allowed. Hosted-SaaS and change-of-control
scope must be resolved through verified evidence, and an explicitly denied
required right remains a blocker.

No code path should infer those rights from public visibility or from a generic
commercial-use statement.
