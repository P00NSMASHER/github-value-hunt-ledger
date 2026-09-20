# Freight Recovery — SBOM and Release Attestation

Updated: 2026-09-20

## CycloneDX-shaped SBOM

`freight/sbom.py` creates a deterministic CycloneDX 1.6 document covering:
- exact repository/revision components in `COMPONENT_RIGHTS_REGISTRY.json`;
- direct pinned Python CI dependencies in `production/requirements-ci.txt`.

The document includes rights/provenance information as custom Freight properties.

**Coverage limit:** this is not claimed to enumerate every transitive runtime, OS package, cloud service, third-party API, standard, model weight, dataset or buyer-specific integration.

## in-toto / DSSE-shaped attestation

`freight/release_attestation.py` creates:
- an in-toto Statement v1-shaped payload;
- subjects for deterministic control provenance and SBOM content;
- an unsigned DSSE envelope.

The repository intentionally emits `signatures: []`.

This prevents a locally generated payload from being mistaken for a real signed attestation. A future production release may send this deterministic payload to an approved external signing identity/key and record the signer/verifier evidence separately.

## Current claim boundary

CI can prove:
- deterministic generation;
- exact current-checkout reproduction;
- no fake repository-created signature.

CI cannot prove:
- external signer identity;
- trusted timestamp;
- certificate-chain validity;
- deployed artifact identity unless the build/deploy system binds the attestation to that artifact.
