# RecoveryOS Phase 3 — External Assurance Plan

Version: 1.0  
Prepared: 2026-10-07

This document defines the external evidence required before Freight Recovery may
claim independent security assurance. Internal engineering work cannot substitute
for these artifacts, no matter how tempting the marketing department might find
the adjective "enterprise."

## 1. Independent penetration test

Status: **PENDING_EXTERNAL**

### Target

- Production app: `https://freight-recoveryos.floot.app`
- Authenticated RecoveryOS customer-data environment
- Floot-hosted backend endpoints under `/_api/*`
- Tenant-scoped PostgreSQL data plane
- Recovery import, review, API-key, payment and analytics workflows

### Required tester independence

The tester must not be the author of the RecoveryOS implementation being tested.
The final report must identify tester/firm, test dates, target, methodology,
findings, severity, retest status, and unresolved risks.

### Required attack areas

- authentication and session handling;
- registration/login abuse and brute-force controls;
- tenant isolation / IDOR / BOLA;
- role escalation: viewer -> reviewer -> owner;
- API-key generation, leakage, scope bypass and revocation;
- ingest-vs-payment-event scope separation;
- SQL injection and unsafe dynamic query construction;
- stored/reflected DOM/server XSS;
- CSRF on cookie-authenticated mutation endpoints;
- request smuggling/header confusion where applicable;
- sensitive response/log leakage;
- payment lifecycle bypass, amount manipulation and replay;
- finding/recovery attribution manipulation;
- audit-chain tampering and concurrency;
- AI analytics tenant-boundary and prompt-injection abuse;
- denial-of-wallet abuse against AI endpoints;
- rate-limit bypass;
- malformed/oversized canonical import payloads;
- authorization behavior after session/API-key revocation.

### Out of scope unless separately approved

- destructive volumetric denial of service;
- social engineering;
- physical attacks;
- attacks on unrelated Floot tenants;
- destructive testing against provider infrastructure;
- credential stuffing using real leaked credentials.

## 2. SOC 2 Type II

Status: **PENDING_EXTERNAL**

A Type II claim requires an independent CPA/audit firm and an observation period.
Phase 3 Step 1 prepares evidence; it does not create the report.

Minimum readiness package should cover:

- system description and in-scope services;
- logical access;
- privileged access;
- joiner/mover/leaver process;
- authentication and credential policy;
- change management;
- code review / release controls;
- incident response;
- vulnerability management;
- logging and monitoring;
- backup / restore;
- availability and recovery;
- vendor/subprocessor management;
- data retention/deletion;
- risk assessment;
- security awareness where personnel scope warrants it.

Target trust-service criteria: Security as baseline. Availability and
Confidentiality should be added only if the service commitments and evidence are
ready to support them.

## 3. ISO/IEC 27001

Status: **PENDING_EXTERNAL**

Certification requires an accredited certification body, an operational ISMS,
risk treatment evidence, internal audit, management review, corrective-action
process and certification audit.

Do not market the Phase 3 control map as ISO certification or "ISO compliant."

## 4. Provider encryption evidence

Status: **PENDING_EXTERNAL**

The current data plane is a Floot-managed PostgreSQL resource identified by Floot
as Neon-backed. A buyer-facing encryption claim requires provider evidence or
contractual/security documentation covering the exact service path.

Required evidence:

- encryption in transit for application <-> database;
- encryption at rest for database/storage;
- key-management responsibility boundary;
- private storage encryption if production backups are added there;
- secret-storage characteristics for `JWT_SECRET` and database credentials.

Until captured, public wording is limited to the observed architecture. Do not
promote ordinary HTTPS assumptions into an attestation.

## 5. Provider backup / restore evidence

Status: **PENDING_EXTERNAL**

Required production evidence:

- backup/PITR feature actually enabled for the exact RecoveryOS database;
- retention window;
- recovery-point behavior;
- restore procedure;
- restore target/isolation;
- successful restore drill;
- measured RPO/RTO from that drill.

Repository SQLite semantic backup/restore tests remain useful application-level
evidence but do not prove recovery of the deployed PostgreSQL data plane.

## Acceptance rule

An external control moves from `PENDING_EXTERNAL` only when the artifact exists,
is tied to the exact in-scope RecoveryOS environment, is current, and its
limitations are recorded. Vendor marketing pages, assumptions, or "we use a
secure cloud" do not satisfy this rule.
