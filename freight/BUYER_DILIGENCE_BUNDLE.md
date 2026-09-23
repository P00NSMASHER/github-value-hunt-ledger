# Freight Recovery — Buyer / Acquirer Diligence Bundle

Updated: 2026-09-23

`freight/diligence_bundle.py` creates a deterministic ZIP intended to make
technical/commercial diligence boring and reproducible.

## Included

The bundle contains:
- commercial model / qualification / learning policies;
- data-readiness, final pilot launch gate, actionable launch-remediation brief, buyer-safe pilot activation packet, scope-freeze Pilot Charter, Pilot Amendment change-control, authoritative engagement-state resolver, revocable external-action authorization, separate-environment evidence template with SHA-256 evidence receipts/freshness semantics, and pilot protocols;
- pilot data-room/report/audit-lifecycle documentation;
- security/data-handling and release/security gates;
- rights registry + rights evidence manifest/promotion rules + release manifest;
- rights-evidence transfer checklist for documents held outside the repository;
- incident-response runbook + tabletop template;
- deployment-security evidence addendum + completed Netlify-specific tabletop;
- controlled synthetic pilot demonstration specification and public-site release instructions;
- deterministic release provenance;
- exact component inventory;
- partial CycloneDX 1.6 SBOM;
- intentionally unsigned DSSE attestation.

Every entry is listed in `BUNDLE_MANIFEST.json` with byte size + SHA-256.

## Explicit exclusion

`customer_data_included` is always **false**.

The builder does not package:
- customer invoices;
- contracts/rate cards;
- shipment/POD/BOL data;
- incumbent outputs;
- settlement/remittance data;
- customer identifiers or secrets.

A diligence bundle is therefore not a customer pilot evidence package. The
included controlled-demo specification describes fictional inputs only; the
separate generated demo ZIP is not embedded in this diligence ZIP.

## Claim boundary

The ZIP is deterministic and tamper-checked against the current repository
checkout. It does not turn unsigned provenance into signed provenance, partial
SBOM coverage into complete deployment inventory, or repository tests into a
security certification.


## Evidence still supplied outside this ZIP

The repository bundle intentionally does not contain:
- executed license/permission documents;
- buyer-specific contracts/DPAs/security questionnaires;
- external signing keys/signatures;
- live incident evidence beyond the recorded tabletop;
- customer notification/legal advice;
- production SOC/SIEM or WORM exports.

Those items belong in the actual controlled diligence room. The rights evidence
manifest may reference them by location + SHA-256 after they are supplied and
verified.
