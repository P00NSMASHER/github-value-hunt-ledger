# RETALLY Mission 16 | Verified inquiry operator actions and identity boundary

**As of October 8, 2026. DRAFT engineering candidate. No production activation, migration, customer data or email sends.**

## Source and dependencies

- Stacked branch: `mission16/verified-inquiry-operator-20261008` on **PR #321**, which is itself stacked on **PR #307**.
- Uses pre-existing `0001_inquiry.sql` and the Mission 14/15 retention guard `0002_inquiry_case_retention.sql`.
- New additive, unapplied SQL: `freight/site/migrations/0003_inquiry_verified_case_actions.sql`.
- New restricted endpoint: `functions/api/internal/inquiry-case.js`.
- Non-public source (excluded from the static build) for Cloudflare Access verification: `freight/site/operator_access_auth.js`.
- Regression: `freight/site/test_inquiry_case.mjs`; integrated with the **existing** RETALLY Inquiry CI, not a scheduler.

## Independent defect and threat model

Before this work, disposition values `operator_id` and `purge_approved_by` were merely database strings. Different strings in a row do not establish independent authorized people. A credential that can write unrestricted D1 SQL can still impersonate operators, forge timestamps or attest unearned evidence.

The verifier is kept outside the Pages Functions file-based route directory so it cannot be mistaken for a separately public HTTP endpoint. The new endpoint does not trust user-submitted operator identifiers, `X-Forwarded-Email`, unsigned JWT claims or provider notification status. It requires an **actual RS256 signature-verified Cloudflare Access application JWT** with validated issuer, application audience, time limits, `sub` and `email`. It obtains the public JWKS only from a strictly configured `*.cloudflareaccess.com` team origin, and the signed identity must match an explicit server-side email+subject allowlist for its role.

No operator user IDs or sensitive records are exposed in the endpoint response. The caller supplies a 64-hex evidence digest, which is only a reference assertion until the actual source/evidence binding is separately independently verified.

## State transitions

`ACKNOWLEDGE` (reviewer) inserts the first case disposition for an existing inquiry. Duplicate acknowledgment is rejected.

`CLOSE` (reviewer) requires an acknowledged case and records the verified closing actor and an earliest normal-retention timestamp derived from the original receipt date.

`SET_HOLD` (reviewer) records a structured hold reason and verified requester. A hold cannot be set after purge approval.

`RELEASE_HOLD` (approver) requires an existing hold and a different verified actor from the hold requester. A reviewer cannot release their own hold merely by editing submitted form fields.

`APPROVE_PURGE` (approver) requires a closed case, separate actor from both initial reviewer and closing actor, no hold, unexpired approval time, eligible original age and elapsed retention. **It does not delete the inquiry**. Any later authorized administrator deletion must still pass the independent Mission 14 database trigger and produce an immutable purge receipt.

Each successfully committed action updates one case through one database statement. Trigger-based append-only action receipts record event ID, case reference, verified actor subject, action type, reference digest and timestamp. Duplicate action IDs are rejected across cases, and event rows cannot be updated or deleted through ordinary SQL.

## Configuration and explicit release gate

The endpoint is disabled unless **both** independent opt-in flags are exactly `1`:

- `RETALLY_CASE_WRITES_ENABLED`
- `RETALLY_CASE_POLICY_APPROVED`

Required server-side configuration (values must not be committed or echoed in logs):

- `RETALLY_ACCESS_TEAM_DOMAIN`: exact HTTPS Cloudflare Access team origin
- `RETALLY_ACCESS_AUD`: exact expected Access application AUD
- `RETALLY_INQUIRY_REVIEWERS`: JSON objects with verified email and subject pairs
- `RETALLY_INQUIRY_APPROVERS`: a separate authorized approver set
- `INQUIRY_DB`: approved D1 binding

**DO NOT set these flags in production now.** The actual Cloudflare Access application, policy, team domain, issuer, JWKS retrieval, human IdP and role assignments have NOT been independently configured or exercised. Production may not have these settings. A fabricated signed QA token only proves that the verification code rejects the tested attacks.

## Executed independent acceptance

1. **16 isolated signed-JWT and real SQLite endpoint tests: PASS.** Synthetic RSA signing keys, deliberately wrong signatures/issuers/audiences, expiry, wrong role, spoofed email header, wrong origin, duplicate IDs, hold/release, closed-case purge approval, aging, and response redaction. No fake claims presented as real user identity.
2. **10 independent SQL transactions/assertions against real isolated Cloudflare D1: PASS.** Applied exact three repository migrations (0001, 0002, 0003) on disposable US-jurisdiction database `retally-m16-inquiry-identity-qa-20261008`. The additive 0003 migration returned success for its 13 SQL operations and created four new action-audit triggers. Old pending source data not touched.
3. **Follow-up standard regression:** the inherited PR #321 tests and other build checks are required at exact PR head. Do not infer approval from draft local checks.

## Known remaining release blockers

- **Privileged D1 bypass:** A Cloudflare administrator with arbitrary SQL write permissions can still forge disposition columns. Database triggers cannot cryptographically verify an Access JWT. Do not claim immutable audit against account owners or compromised database administrator credentials. Production design requires a least-privilege operator write boundary, audited administrative actions and independent credential governance.
- **Actual human identity:** signed synthetic Access tokens are not an operational IdP proof. Configure Access protected route, human factors/MFA, offboarding and separate real-world actors; verify signed *real* session tokens with authorized testing.
- **Evidence authority:** caller-provided `evidenceDigest` proves neither underlying customer contact nor permission to close/erase. Source binding and independent evidence review are still required.
- **Privacy legal review:** this workflow implements a 90-day **minimum** normal purge gate, but does not address authorized early erasure exceptions. Legal/privacy counsel must validate actual retention and hold rules before any customer use.
- **Messaging:** real Zoho inbox receipt and Cloudflare outbound sender permission remain unverified.
- **Production:** no D1 migration, authenticated operator write deployment, owner agreement, live customer contact, or direct online inquiry activation performed.
- **Tests:** Node `node:sqlite` remains experimental in Node 22. Real Cloudflare D1 migration/SQL tests do not demonstrate Cloudflare Access actually blocking unauthenticated web traffic end to end. Test actual HTTP origin/JWT path and revocation response in the approved staging setup before release.

**VERDICT:** reviewable, fail-closed case operator candidate; **NO-GO** for production deployment and customer-data operations.
