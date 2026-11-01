# RETALLY Phase 5G: independent verifier process and PostgreSQL runtime identities

## Scope: isolated disposable PostgreSQL 16, NOT live Floot credential separation

This change extends the existing Phase 5C signed financial contract and Phase 5F no-login roles. It does not create a new financial ledger or modify original 26 historical findings.

### Actual implementation

- `phase5g_independent_verifier.py`: separately executable verifier requiring a PINNED buyer Ed25519 public key outside the database, exact canonical signature bytes, issuer/tenant/case/invoice/currency agreement, signer key lifecycle and current revocation, historical contract terms, and a separately restricted verifier PostgreSQL login. Verifies **before** INSERT, and serializes exact/replayed document admission by a scoped PostgreSQL advisory lock. The independent source registry is supplied by the verifier caller, not invented by the ordinary app or fetched solely from mutable financial tables.
- `phase5g_disposable_definer.sql`: in disposable CI only, changes the existing financial trigger to SECURITY DEFINER with its already pinned search_path and qualified tables. This lets the limited verifier role insert via the existing case FOR UPDATE financial guard without receiving broad UPDATE privileges on customer cases. It is NOT installed on hosted QA or production; needs separate privilege review before use outside disposable tests.
- `test_phase5g_independent_verifier.py`: creates TWO independently authenticated PostgreSQL LOGIN identities in disposable CI with separately generated, ephemeral credentials. Ordinary app login has no financial-table access. Only verifier login has narrowly permitted evidence SELECT and INSERT, never case UPDATE or evidence DELETE. Actual sessions test wrong principal, legitimate signed document, duplicate and concurrent replay, modified signature, wrong issuer tenant, revoked signer, and a fee event lacking evidence.
- Test explicitly demonstrates that possession of the verifier LOGIN credential alone can still bypass Python Ed25519 checking through direct SQL INSERT; it rolls back that invalid write. The security model therefore DEPENDS on genuine credential isolation and trusted verifier code. Do not claim the database verifies Ed25519.

### Environment separation

Published Floot RecoveryOS: PostgreSQL cluster `7693746749463444100`. Unpublished QA: `7694294930552894346`. Only read-only isolation queries were used; no runtime Floot credentials changed.

Disposable PostgreSQL testing **refuses either actual Floot cluster identifier** and requires the exact `retally_phase5_ci` database. Passwords are generated for test processes, not committed or printed. The CI service has no real customer financial evidence or carrier integrations.

### Exact limitations

- **Not yet integrated into actual Floot runtime.** Its managed FLOOT_DATABASE_URL continues to use `neondb_owner`, which owns financial evidence tables. The owner-level bypass remains OPEN_UNMITIGATED for real hosted QA, and production impact has not been established.
- The reference verifier currently accepts **fictional signed CONTRACT documents only**, not actual bank/carrier credit evidence. Other transaction kinds fail closed pending independently verifiable source adapters. Existing Phase 5C and 5D synthetic customer workflows remain intact under their earlier evidence classification.
- Actual independent service hosting, secret rotation, deployment, alerting and a genuine production-grade signer authority registry are not implemented.
- Financial table owner and prospective verifier role can still insert arbitrary signature-shaped documents if the verifier credential is compromised; real credential separation and auditing must be verified.
- No original historic findings are closed: 26 remain OPEN_UNVERIFIED, D-07 is repaired only in original offline research. Actual real RETALLY revenue and recovered customer money remain $0.

### Decision

This is a distinct-credential, standalone verifier **proof of execution in disposable PostgreSQL**, not certification of the hosted RecoveryOS financial trust boundary. Do not merge, deploy, publish, access production records, contact customers, move money, or change scheduled tasks.
