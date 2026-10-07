# RecoveryOS Phase 3 — SOC 2 Readiness Control Map

Prepared: 2026-10-07  
Status: readiness mapping only, **not a SOC 2 report**

This control map gives a future auditor a compact starting point. The final
control descriptions, populations, sampling periods and evidence requests belong
to the independent audit process.

| Area | RecoveryOS control/evidence today | State |
| --- | --- | --- |
| Logical access | Authenticated app, bcrypt password hashes, login lockout/rate limiting, 12-hour signed Secure/HttpOnly/SameSite session cookie, database session expiry | Evidenced internally |
| Identity uniqueness | Lowercased registration email + unique index on `lower(email)` | Evidenced internally |
| MFA | No second factor currently evidenced | External/control gap |
| Enterprise SSO | No SAML/OIDC enterprise SSO currently evidenced | External/control gap |
| Tenant authorization | Tenant membership + role checks in server endpoints; tenant-scoped queries | Evidenced internally |
| Tenant isolation | Composite tenant/object FKs; two-tenant negative insertion test rejected | Evidenced internally |
| Service/API credentials | Random API tokens; SHA-256 hash-only persistence; `ingest` and `payment_event` scopes; revocation | Evidenced internally |
| Secrets | DB URL and JWT signing secret are connected server-side resources; values not committed or surfaced by project resource inventory | Evidenced internally |
| Evidence integrity | Immutable DB triggers on financial/evidence tables | Evidenced internally |
| Audit trail | Per-tenant hash-linked append-only audit events with serialized append lock and verification function | Evidenced internally |
| Payment authorization | Separate owner authorization and DB-enforced exact amount/lifecycle guards | Evidenced internally |
| Change management | GitHub PRs, release gates, Freight commercial contracts CI, release provenance, SBOM and attestation payload | Evidenced internally |
| Software inventory | Deterministic CycloneDX SBOM for repository/pinned CI scope; documented as partial | Evidenced, partial scope |
| Incident response | Incident states, severity/exposure rules, notification authorization and tabletop artifacts | Readiness evidence; staffing/execution not externally proven |
| Data retention/deletion | Policy and fail-closed lifecycle semantics; buyer-specific retention required | Partial |
| Backup/recovery | Semantic SQLite backup/restore drill exists; production Floot/Neon backup/PITR/restore evidence absent | External/control gap |
| Encryption | Provider architecture observed; exact provider encryption evidence not captured | External/control gap |
| Vulnerability management | CI/release gates and SBOM exist; independent scanning/pen-test evidence absent | Partial |
| Availability | No independently verified production SLA/SLO or recovery measurements yet | Phase 3 later work |
| Subprocessor management | Initial provider/data-flow register prepared; contractual diligence still required | Partial |
| Security monitoring | Operational app audit chain exists; no independently evidenced SIEM/on-call monitoring program | Partial |
| External penetration testing | Not performed | External/control gap |

## Evidence sources

Primary repository evidence includes:

- `freight/PHASE3_SECURITY_READINESS_2026-10-07.json`;
- `freight/PHASE3_SECURITY_TEST_EVIDENCE_2026-10-07.md`;
- `freight/SECURITY_AND_DATA_HANDLING.md`;
- `freight/TRUST_CENTER_OPERATING_STANDARD.md`;
- `freight/INCIDENT_RESPONSE.md`;
- `freight/INCIDENT_TABLETOP_TEMPLATE.md`;
- `freight/PERSISTENT_AUDIT_AND_BACKUP.md`;
- `freight/SBOM_AND_ATTESTATION.md`;
- generated CycloneDX / provenance / unsigned DSSE artifacts;
- RecoveryOS production data-plane schema and application controls.

## Audit-readiness rule

A row marked "evidenced internally" means the control implementation and/or
negative test is reproducible from current artifacts. It does not mean an
independent auditor tested that control over a Type II observation period.
