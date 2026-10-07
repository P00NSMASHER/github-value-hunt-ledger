# RecoveryOS — Enterprise Architecture & Data Flow

Prepared: 2026-10-07

## Purpose

RecoveryOS is an independent second-look freight recovery and financial-truth
layer. It does not need to replace the buyer's TMS, AP system, incumbent audit
provider or bank to run a controlled pilot.

## Logical flow

1. **Buyer scope / authorization**
   - buyer + business unit;
   - source authorization;
   - retention;
   - population selection rule.

2. **Ingress boundary**
   - API / SFTP / governed upload / explicit X12 profile;
   - production private PDF/PNG/JPEG/WebP evidence upload with server-created immutable upload intent;
   - stored-byte SHA-256 verification before extraction;
   - append-only source document retention and tenant-scoped deduplication;
   - SHA-256 ingress receipt;
   - file/input guard where applicable;
   - transport metadata never grants commercial authority.

3. **Canonical freight record**
   - invoice/shipment identity;
   - source hashes;
   - integer-cent money;
   - mode-specific shipment facts.

4. **Controlling authority**
   - effective-dated contract/rate authority;
   - explicit precedence;
   - ambiguous/missing/unverified authority routes to review.

5. **Deterministic rating**
   - Parcel, LTL, TL, Intermodal, Air, Ocean;
   - expected charge + components;
   - candidate variance;
   - result hash.

6. **Incumbent challenge**
   - freeze incumbent findings/automatic credits/open claims/known disputes;
   - classify challenger-only, incumbent-known, suppressed or review;
   - duplicate economic identities do not receive net-new credit.

7. **Human review**
   - confirm;
   - reject;
   - need evidence;
   - modify-rule candidate;
   - escalate.

8. **External action**
   - separate buyer authorization required before carrier/vendor contact.

9. **Payment / settlement state**
   - PREPARED;
   - AUTHORIZED;
   - SUBMITTED;
   - ACCEPTED;
   - SETTLED;
   - FAILED;
   - REVERSED.

10. **Reporting**
    - candidate difference;
    - validated finding;
    - challenger-only validated;
    - uniquely attributable realized;
    - fee-eligible realized.

These values are never collapsed into a single fictional "savings" number.

## Production application

- application: RecoveryOS;
- URL: https://freight-recoveryos.floot.app;
- host/runtime: Floot;
- persistent data plane: Floot-managed PostgreSQL;
- authentication: application password sessions plus Google and Microsoft federated sign-in;
- natural-language analytics: Floot AI typed routing;
- source/release engineering: GitHub.

## Isolation model

Every customer-facing record is tenant scoped. Database constraints bind records
to tenant-owned populations/findings. Step 1 executed an A-vs-B negative insert
and PostgreSQL rejected the cross-tenant reference.

## Trust boundaries

### AI
AI may route an analytics question, assist a reviewer, or extract observable
facts from a privately retained PDF/image. Document extraction is staged as a
separate immutable claim with confidence and page/region locators, then routed
through deterministic checks and human review. AI does not silently select
commercial authority, certify recovered dollars, authorize carrier actions, or
move money.

### Payment providers
External providers may execute payment/credit movement. RecoveryOS records and
verifies lifecycle evidence but does not claim custody.

### Incumbent systems
Incumbent output is treated as an input to freeze before challenger attribution,
not as a truth source RecoveryOS may rewrite.

### Customer evidence
Buyer-controlled truth and settlement evidence remain the highest-value external
proof sources in a real pilot.

## Current architectural gaps

- MFA, buyer-controlled enterprise SSO, and SCIM lifecycle management;
- real-customer calibration/accuracy evidence for the production document-extraction path;
- named ERP/TMS/accounting connectors;
- direct payment-rail integration;
- independent security assurance;
- concurrent multi-tenant HTTP/SLO proof;
- provider-level backup/encryption evidence.

Those gaps are preserved because diagrams are remarkably bad at making missing
controls materialize.
