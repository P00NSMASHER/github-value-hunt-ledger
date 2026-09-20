# Freight Recovery — Deployment-Specific Incident Tabletop

Exercise date: **2026-09-20**  
Target: **Netlify / freightleak-audit**  
Exercise type: **tabletop only — not a live incident**

## Scenario

A reviewer reports that the Freight audit deployment may have become reachable
outside the intended team boundary after an access-control or deployment change.
Because future versions may process buyer audit evidence, the exercise assumes a
possible confidentiality event until facts disprove it.

Initial classification:

- Severity: **SEV2**
- Exposure state: **UNKNOWN**
- Incident state: **OPEN**
- External notification: **not sent**

## Evidence available at exercise start

Deployment-specific evidence collected the same day showed:

- Netlify project `freightleak-audit`.
- SSO team login required for **all** visitors.
- Password access not configured.
- Netlify Forms: **0**.
- Netlify environment variables: **0**.
- Team members: **1**.
- Team MFA enforcement: **not enforced**.
- No Freight backend/data plane discovered in Vercel, Render, Floot, Replit,
  AppDeploy, or Supabase.
- No production parser runtime discovered.

Important limitation: an independent unauthenticated HTTP/browser probe could
not be preserved with the available tooling.

## Tabletop actions

### 1. Containment

Simulated immediate actions:

1. Freeze non-essential deployment changes.
2. Verify Netlify visitor-access control remains SSO-required for all.
3. If control drift is observed, restore the SSO requirement before resuming use.
4. If credential compromise is suspected, revoke/rotate affected credentials
   through the real provider; do not place secrets in GitHub.
5. Pause any future parser/import path whose integrity is uncertain.
6. Preserve the release manifest, deployment-security evidence, project/team
   configuration evidence, and relevant provider logs/receipts.

No production setting was changed during this tabletop.

### 2. Exposure assessment

The exercise does **not** assume SSO configuration equals proof of no exposure.

Questions that must be answered in a live event:

- Can an unauthenticated identity reach application content?
- Does any customer data plane exist outside Netlify?
- Did any object/API/database authorization boundary change?
- Did any parser/runtime have credentials or network access that could expose
  evidence?
- Are audit/provider logs complete enough to bound the event?

Because no multi-tenant data plane or parser runtime is currently discovered,
the exercise cannot produce a live cross-tenant or parser-containment result.

### 3. Notification decision

Result: **NO NOTIFICATION SENT**

Reason:

- This was a tabletop, not a live incident.
- The standing incident model requires explicit human authorization and a
  contract/legal/policy basis before external notification.
- The model must not independently decide statutory/customer notification.

### 4. Recovery verification

A live recovery would require:

- SSO/access configuration re-verified;
- known-good release/provenance identified;
- customer-data-plane isolation tests passed if a data plane exists;
- parser sandbox/resource/network/credential controls verified if a parser
  runtime exists;
- audit/settlement semantic invariants rechecked where money-bearing state could
  be affected.

### 5. Closure / exercise outcome

Tabletop outcome: **PASS WITH MATERIAL GAPS**

What worked:

- fail-closed UNKNOWN exposure semantics;
- explicit containment-before-recovery sequence;
- evidence preservation;
- human authorization before external notification;
- clear separation between deployment access control and tenant isolation.

Open gaps exposed by the exercise:

1. **P0:** Netlify team MFA is not enforced.
2. **P0 before multi-tenant customer data:** no real A-vs-B tenant isolation
   evidence exists.
3. **P0 before parser use:** no parser sandbox/resource/network/credential
   evidence exists.
4. **P1:** no independent unauthenticated black-box probe is preserved.
5. **P1:** no deployed on-call/alerting/contact-tree evidence is yet attached.

This tabletop does not close a real incident and does not change the external
commercial outcome ledger.
