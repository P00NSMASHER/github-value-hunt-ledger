# RETALLY Phase 5E: admission-time signer revocation and database trust boundary

This is an **unpublished, fictional-data-only** research acceptance. Its work is stacked on Phase 5D PR #310, not merged into production.

## Reproduced defect in actual QA financial endpoint

The prior `phase5cFinancialEvidence.tsx` verifier correctly checked a document's claimed `occurredAt` against an issuer's effective period, but **did not establish whether the signing key was still trusted at the time a newly submitted record was admitted**. A fictional BUYER key revoked on October 6 could submit an entirely new contract on October 8 by setting `occurredAt=October 3`.

Observed in the unpublished QA Floot project:
- **Before**: a new correctly signed, backdated fixture with revoked issuer key was HTTP 200 (`replay:false`), creating `SIM-P5E-BACKDATED-BEFORE`.
- **Focused repair**: the QA financial endpoint checks the key's current revoked/expired status for NEW admissions, **after** recognizing an identical, correctly signed previously admitted record. The PostgreSQL `phase5c_qa.guard_signed_financial_record` trigger independently checks `transaction_timestamp()` against issuer `revoked_at` and `expires_at`. No old financial balances were rewritten.
- **After**: a fresh correctly signed, backdated contract `SIM-P5E-BACKDATED-AFTER` was HTTP 400 (`SYNTHETIC_SIGNER_NO_LONGER_TRUSTED_FOR_NEW_ADMISSION`); the exact original previously admitted contract remained HTTP 200 (`replay:true`) with its unchanged ID. A read-only QA query confirmed that only the baseline historical test document remained.

The application patch is preserved at `qa_application/endpoints_phase5c_financial_document_POST.ts`. The guarded PostgreSQL migration was updated **in place** at `phase5c_signed_reconciliation.sql`.

**Limits:** This repair addresses new admissions after a registered revocation/expiry. It does not prove an issuer's identity, the time an external signer actually created a signature, real contract validity, or customer cash. The QA application still uses synthetic auth.

## Important independently identified database bypass remains OPEN

At the current QA deployment:
- The Floot `FLOOT_DATABASE_URL` connection uses `neondb_owner`, which also owns `phase5c_qa.documents`.
- PostgreSQL's record trigger checks amount/source/fee invariants, **not Ed25519 signatures**. The Ed25519 check is in the TypeScript application.
- Installed `pgcrypto` provides no Ed25519 signature verification; `pgsodium` and `plv8` were not available in the QA cluster's extension catalog.
- A hypothetical directly privileged DB owner can insert a fake signature-shaped record that bypasses TypeScript. This weakness is **not fixed** by revocation timing rules or the fact that application HTTP rejects fake signatures.
- The disposable PostgreSQL test `test_phase5e_admission_boundary.py` deliberately reproduces that direct-owner bypass inside a transaction and **always rolls the inserted row back**. It labels the bypass as `OPEN_UNMITIGATED`, never as a successful defense.

A production-credible fix requires a **separately privileged application write identity**, a trusted signer-verification boundary that the database writer cannot forge, and retesting of actual authenticated application operations against that distinct credential. Do not substitute a writable `signature_verified` flag or spoofable session variable.

## Executable acceptance

- The inherited Phase 5 disposable PostgreSQL workflow installs the exact updated `phase5c_signed_reconciliation.sql`, then runs existing payment and financial tests and Phase 5E tests proving new backdated signer records are rejected while owner-level direct-write bypass remains reproducible.
- `test_phase5e_receipt.py` checks staged source and business boundary labels.
- Earlier Phase 5D D-07 original affected-implementation repair evidence and all three fictional customer scenarios remain inherited unchanged.
- All 26 historical findings remain formally `OPEN_UNVERIFIED`. One newly reproduced QA admission defect was repaired in its actual staging implementation, not in an original historical archive.

## Safety and release

QA project `7257eaf3-a4d7-43db-9136-fe81e5df35bf` is unpublished on PostgreSQL system identifier `7694294930552894346`; production `c719b60c-9b3b-4193-a543-0be9d3ceaef2` remains on `7693746749463444100`, read-only for this mission. No customer/issuer data, real money, carrier claims, purchased resources, production publishes, merges or scheduled-task changes.
