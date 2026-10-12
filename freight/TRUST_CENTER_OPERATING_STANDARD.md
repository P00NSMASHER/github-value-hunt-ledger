# Freight Recovery Trust Center — Operating Standard

Version: 1.0
Effective: 2026-10-06

## Purpose

This document defines the claims Freight Recovery may make publicly about trust, data handling, human review, recovery authority, and customer diligence.

## Public business identity

- Brand: Freight Recovery
- Business contact: [redacted historical personal inbox]
- Business address: [residential business mailing address withheld from public repository]
- Service area: United States
- Public website: GitHub Pages deployment controlled by the repository public-build allowlist.

No longevity, customer-count, recovered-dollar, certification, carrier-partnership, employee-history, or security-compliance claim may be published without evidence.

## Public-site boundary

The public site:
- accepts no freight-file uploads;
- performs qualification locally in the browser;
- does not persist qualification fields in browser storage;
- can prepare a non-sensitive email that the visitor reviews and sends;
- is not the customer-data environment.

## RecoveryOS customer-data environment

The current authenticated RecoveryOS application is separate from the public
marketing/qualification site.

Current production application:

- URL: `https://freight-recoveryos.floot.app`;
- application host/runtime: Floot;
- persistent data plane: Floot-managed PostgreSQL (identified by Floot as
  Neon-backed);
- authentication: application email/password sessions;
- current second-factor/enterprise-SSO status: not evidenced.

RecoveryOS may accept governed customer data only through its authenticated,
tenant-scoped application/API boundary and only under the applicable engagement
authorization. Public marketing forms/pages remain outside this customer-data
environment.

The production security evidence snapshot and provider register are maintained
separately. No SOC 2, ISO 27001, penetration-test, provider encryption or
provider backup/restore claim is implied merely by using a hosted platform.

## Customer-data intake

Confidential freight records are accepted only after:
1. fit is confirmed;
2. population and allowed record categories are defined;
3. an approved transfer route is identified;
4. access is limited to the agreed purpose and authorized users;
5. retention/deletion expectations are documented for the engagement.

Ordinary email is not an approved route for invoices, contracts, credentials, bank/payment details, or unrestricted mailbox access.

## Data minimization

Request the least data needed for the current stage.

Qualification should use business identity, contact information, spend/volume bands, modes, record-readiness categories, and non-sensitive problem descriptions before invoice-level records are requested.

## Purpose limitation

Accepted customer records may be used only for the agreed freight-audit, review, recovery, reconciliation, support, security, and engagement-administration purposes.

Customer records are not to be used to train a general-purpose model unless separately disclosed and authorized.

## Access and authorization

A free audit request does not authorize:
- carrier contact;
- dispute submission;
- settlement acceptance;
- money movement;
- credential use;
- access outside the agreed record population.

Recovery actions require the applicable customer authorization.

## Human review and automation

Automation may assist ingestion, normalization, matching, calculation, prioritization, and evidence assembly.

Material findings and ambiguous evidence remain subject to human review. Automation does not waive the Freight Recovery Evidence Standard.

## Retention and deletion

Do not promise a universal retention duration until a production retention schedule is approved for the specific data environment.

Before confidential records are accepted, the engagement should document the applicable retention/deletion treatment, including active claims, settlement evidence, contractual recordkeeping, and backup behavior.

Deletion requests must be reconciled against contractual, evidentiary, security, and legal retention requirements rather than represented as instantaneous universal deletion.

## Security claims

Publish only security controls that are currently evidenced.

Do not claim SOC 2, ISO 27001, HIPAA compliance, PCI certification, enterprise-grade security, penetration-test status, encryption characteristics, SSO, or other certification/control claims unless the applicable evidence exists and the claim accurately describes the customer-data environment.

## Providers and subprocessors

The Trust Center should identify material providers used to host the public site or process customer data when doing so is accurate and useful for buyer diligence.

A public-site hosting provider must not be described as a customer-data processor merely because it hosts marketing pages.

## Incident handling

Any suspected unauthorized access, disclosure, loss, corruption, or misuse of customer records should be contained, documented, investigated, and escalated according to the applicable environment and engagement requirements.

Customer notification commitments must come from the signed engagement or an approved incident-response policy, not improvised website copy.

## Recovery evidence

Potential recovery, validated finding value, approved claim value, settlement, reversals, actual recovered funds, and fee-eligible recovered funds remain separate states.

Pre-existing, incumbent-known, automatic, duplicate, unsupported, or reversed value is not silently promoted into Freight Recovery-originated recovery.

## AI disclosure

Freight Recovery may use automation or AI-assisted workflows where appropriate for analysis and evidence assembly.

Public materials must not represent an AI-generated brand persona as a real employee, freight veteran, customer, or credentialed professional.

## Customer diligence package

The Trust Center should make the following public or readily available:
- business identity and contact;
- data/privacy notice;
- secure-intake boundary;
- human-review and AI-use policy;
- Evidence Standard/methodology;
- engagement framework;
- recovery-attribution rules;
- sample fictional audit;
- current limitations and non-guarantees;
- incident/security contact route;
- provider/subprocessor information when applicable.

## Change control

Material trust or data-handling claims require evidence review before publication. Version this standard when the operating boundary materially changes.
