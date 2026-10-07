# RecoveryOS Production Data Flow & Provider Register

Prepared: 2026-10-07  
Scope: current RecoveryOS customer-data application

This is an engineering/data-flow register, not a substitute for contract or DPA
review.

## Floot

Observed role:

- hosts the RecoveryOS web/backend application;
- supplies server runtime;
- supplies project secret/resource injection;
- brokers the Floot-managed database resource;
- brokers Floot AI calls used by Ask RecoveryOS.

Data potentially processed:

- authenticated HTTP requests;
- application responses;
- customer freight records submitted to RecoveryOS;
- tenant/user identifiers;
- application/backend logs;
- natural-language analytics questions.

Current evidence source: connected project resources and published-project state.

Required contractual diligence before making buyer-specific legal promises:
current terms/DPA, location/subprocessor commitments, breach-notification terms,
retention/logging terms, and applicable security documentation.

## Neon-backed PostgreSQL through Floot

Observed role:

- persistent RecoveryOS customer-data plane.

Data stored includes:

- tenant and membership references;
- governed freight/canonical record payloads;
- incumbent snapshots/findings;
- review dispositions;
- API-key hashes;
- payment instructions/authorizations/provider events;
- tamper-evident audit events;
- authentication/session tables.

Plaintext API tokens are not stored. Passwords are stored as password hashes via
the authentication implementation.

Provider encryption and production backup/PITR assertions remain
`PENDING_EXTERNAL` until evidence tied to this exact service path is captured.

## TypeSafe Jev through Floot AI

Observed role:

- typed routing/classification for Ask RecoveryOS.

The current analytics endpoint sends:

- the user's natural-language question;
- a fixed catalog describing allowed analytics intents.

It does **not** send freight rows, payment rows, finding rows, database result
sets, or evidence documents to the classifier. Once the intent is selected,
tenant-scoped arithmetic executes in RecoveryOS/PostgreSQL.

Users should nevertheless avoid placing unnecessary confidential row-level data
inside the free-text analytics question itself.

## GitHub

Observed role:

- source-control and CI/release-evidence environment for the Freight Recovery
  engineering repository.

The repository control standard excludes customer/pilot source data from release
and diligence bundles. GitHub is not designated here as the RecoveryOS customer
record database.

## Public marketing site

The public Freight Recovery marketing/qualification surface is distinct from the
authenticated RecoveryOS customer-data application. Marketing-site hosting does
not, by itself, make that host a RecoveryOS customer-data subprocessor.

## Change rule

When a new provider receives customer content, credentials, payment information,
or persistent identifiers, update this register before making a buyer-facing
subprocessor representation.
