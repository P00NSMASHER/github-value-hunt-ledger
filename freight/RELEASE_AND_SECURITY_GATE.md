# Freight Recovery — Release, Security and Diligence Gate

Updated: 2026-09-20

This checklist separates **research architecture** from a buyer-deployable Freight Recovery release.

## Release identity

Every buyer-facing release must include:
- product version;
- source commit;
- dependency/component manifest with exact revisions;
- component-rights registry version;
- test command and captured result;
- SHA-256 checksums for release artifacts;
- SBOM;
- release notes;
- known limitations;
- deployment model.

Do not treat chat/sandbox ZIPs as the canonical release unless they are reproduced from the committed source and entered into this manifest.

## P0 — before a paid pilot with confidential buyer data

### Repository/supply-chain
- [ ] GitHub Actions are pinned to full immutable commit SHAs.
- [ ] Workflow payload writers reject absolute paths and parent traversal.
- [ ] Workflow writers can touch only explicit allowed files/prefixes.
- [ ] CI dependencies are version-pinned.
- [ ] Commercial runtime components are represented in the rights registry.
- [ ] Separate permission/license documents are stored in a buyer-diligence location outside public repo prose.

### Customer data
- [ ] Buyer scope/authorization is documented.
- [ ] Pilot access is read-only by default.
- [ ] Tenant/business-unit scope is explicit in every source request.
- [ ] Cross-tenant negative tests exist for production data services.
- [ ] Data retention/deletion/export rules are defined.
- [ ] Secrets/credentials are never ingested as evidence.

### Parsing/untrusted inputs
- [ ] PDFs/EDI/XML/CSV are treated as hostile inputs.
- [ ] File size/depth/time limits are enforced.
- [ ] XML external entities/network resolution are disabled.
- [ ] CSV/formula export is neutralized.
- [ ] Parsing occurs outside privileged control-plane credentials.
- [ ] Untrusted document/repository text cannot grant tool authority.

### Money/proof
- [ ] Controlling authority is versioned and source-located.
- [ ] Expected charge is deterministic and independently falsifiable.
- [ ] Physical truth is independent of commercial entitlement.
- [ ] Blind-order protocol is enforced: population -> truth -> incumbent output.
- [ ] Unsupported findings remain REVIEW / $0.
- [ ] Settlement readback has source hash + allocation lineage.
- [ ] Duplicate/preexisting/automatic credits cannot become fee-eligible.
- [ ] Recovery certificate cannot exceed validated or realized amounts.

## P1 — before annual continuous assurance

- [ ] isolated production database/control plane;
- [ ] immutable/versioned evidence object storage;
- [ ] independent verifier identity with read-only evidence permission;
- [ ] sandbox/isolation for untrusted code and parsers;
- [ ] central kill switch/budget limit;
- [ ] signed release/provenance;
- [ ] backup/restore drill;
- [ ] audit logging and alerting;
- [ ] customer-specific integration secrets held outside source;
- [ ] incident-response and breach-notification runbook;
- [ ] security questionnaire/diligence package.

## Commercial launch rule

A pilot may be sold before the full enterprise platform exists **only** when it is run as a controlled, read-only, human-reviewed acceptance engagement and every unsupported dollar fails closed.

Do not market the research-agent production architecture as already deployed Freight Recovery infrastructure. They are separate systems until integrated and proven.
