# RecoveryOS — Buyer Security Questionnaire

Prepared: 2026-10-07  
Status: **buyer-ready answer set; not a certification**

This questionnaire is deliberately conservative. "Implemented" means there is
current code/configuration/evidence. "Pending external" means no amount of
repository prose can turn it into an independent assurance artifact.

| Question | Current answer | State |
| --- | --- | --- |
| Is customer access tenant-scoped? | Yes. RecoveryOS uses tenant membership, tenant-scoped queries and composite tenant/object foreign keys. Cross-tenant negative insertion tests have been executed. | Implemented |
| Are sensitive financial/evidence records mutable? | Core populations, ingress receipts, freight records, incumbent snapshots, findings, review dispositions, payment instructions/authorizations/events and audit events are protected by append-only/mutation-blocking controls. | Implemented |
| Is there an audit trail? | Yes. Per-tenant SHA-256-linked audit events are appended under a tenant-scoped database lock and can be reverified for hash/link continuity. | Implemented |
| Are passwords stored in plaintext? | No. Password authentication uses password hashing. Registration enforces minimum 12-character complexity and case-insensitive unique email identity. | Implemented |
| Is MFA available? | Not currently evidenced in the production RecoveryOS application. | **Pending product** |
| Is enterprise SSO available? | SAML/OIDC enterprise SSO is not currently evidenced. | **Pending product** |
| Are sessions protected? | Signed sessions are capped at 12 hours and cookies are Secure, HttpOnly and SameSite=Lax. Same-origin mutation guards are enforced for browser mutations. | Implemented |
| Are API keys plaintext at rest? | No. Only SHA-256 key digests are stored. Ingest and payment-event scopes are separate and keys support irreversible revocation. | Implemented |
| Is customer data encrypted at rest/in transit? | The application is hosted on Floot with a Floot-managed PostgreSQL resource. Exact provider encryption evidence for the complete service path has not been captured into the repository. Do not treat this answer as a provider encryption attestation. | **Pending external** |
| Is there a penetration test? | Internal negative tests exist. No independent third-party penetration-test report has been completed. | **Pending external** |
| Is there SOC 2 Type II? | No Freight Recovery/RecoveryOS SOC 2 Type II report has been issued. | **Pending external** |
| Is there ISO 27001 certification? | No. | **Pending external** |
| Are production backups/PITR proven? | Application-level semantic recovery tests exist, but the exact production-provider backup/PITR/restore path has not been independently evidenced. | **Pending external** |
| Is there a documented incident process? | Yes. Repository incident state, severity/exposure rules, notification authorization, table-top materials and stop-work semantics exist. This is not proof of a 24x7 SOC. | Internal readiness |
| Does AI receive raw customer freight rows? | Ask RecoveryOS sends the user's natural-language question and allowlisted intent catalog to the classifier. Tenant data aggregation remains inside the authenticated database path. Users should avoid placing confidential row-level details in the question itself. | Implemented boundary |
| Can AI authorize claims or move money? | No. Human review, external action authorization and payment lifecycle states remain separate. | Implemented |
| Does RecoveryOS custody funds? | No. PaymentOS orchestrates evidence/state; it is not a bank, custodian, ACH network or wire rail. | Explicit non-capability |
| Are subprocessors documented? | Current data-flow/provider register identifies Floot, Floot-managed PostgreSQL/Neon-backed service, Floot AI, and GitHub engineering scope. Contractual/DPA diligence remains buyer-specific. | Partial |
| Is there a retention/deletion policy? | Data lifecycle semantics are documented and buyer-specific retention must be frozen for a real pilot. Absence is never treated as deletion proof. | Internal readiness |
| Is there a customer-data upload on the public marketing site? | No. Marketing/contact surfaces are not the customer freight-document workspace. | Implemented boundary |

## Buyer-safe security conclusion

A bounded customer-controlled pilot can be evaluated when the buyer approves the
workspace, scope, access, retention, and data-readiness package.

A broad enterprise rollout should **not** be represented as security-complete
until enterprise identity controls and independent assurance evidence are
available.
