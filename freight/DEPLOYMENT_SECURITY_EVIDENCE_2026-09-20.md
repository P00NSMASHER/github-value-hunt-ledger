# Freight Recovery — Deployment Security Evidence Addendum

Collected: **2026-09-20**  
Valid through: **2026-09-27**

## Evidence validity

This snapshot is intentionally time-bounded. It must be recollected:
- before any confidential-customer-data launch after 2026-09-27;
- earlier if relevant deployment, access-control, team-membership, data-plane or
  parser-runtime configuration changes.

Expired evidence blocks the **current Netlify deployment route**. It does not
block a separately controlled environment that has its own independent,
unexpired VERIFIED evidence.

## Target deployment

The only Freight deployment discovered across the connected deployment providers is:

- Provider: **Netlify**
- Project: **freightleak-audit**
- Site ID: `4884fe92-34bc-411c-8fc4-202744c7e161`
- Team ID: `6aa9bbfacf14195400307f86`
- Primary URL: `https://freightleak-audit.netlify.app`

No Freight project/data plane was discovered in Vercel, Render, Floot, Replit,
AppDeploy, or Supabase.

## What is actually proven

### Netlify deployment access configuration — CONFIG PROVEN

Authoritative project/team reads showed:

- Netlify team SSO login is required for **all** project visitors.
- Password access is not configured.
- Netlify Forms: **0 / disabled**.
- Netlify environment variables: **0**.
- Team members: **1**.
- Team MFA enforcement: **not enforced**.

This proves a Netlify-level visitor-access configuration. It does **not** prove
application-level tenant isolation.

## Cross-tenant isolation

Status: **UNPROVEN — no multi-tenant Freight data plane discovered**

There is currently no discovered Freight database, object store, API
authorization layer, or other customer data plane against which an A-vs-B
tenant isolation test can be executed.

Therefore:

- Netlify SSO must **not** be described as cross-tenant isolation.
- Zero cross-tenant negative probes have been completed.
- A future customer data plane must be identified by provider/project and tested
  with at least two distinct tenant identities before this control can become
  PROVEN.

For the currently discovered deployment, the strongest defensible statement is:

> No multi-tenant customer data plane was discovered; cross-tenant isolation is
> therefore not yet testable or proven.

## Parser sandboxing

Status: **UNPROVEN — no production parser runtime discovered**

No production parser/function/worker runtime could be tied to the Netlify
deployment from the available evidence. The deployment had zero Netlify env
variables and zero Forms, but that alone does not prove no compute exists.

No evidence was collected for:

- CPU limits;
- memory limits;
- execution timeout;
- network egress isolation;
- credential isolation;
- low-privilege runtime identity.

The connected desktop that could contain local source/deployment metadata was
offline, and the private GitHub ledger did not contain a `freightleak-audit`
source linkage.

## Evidence-collection constraints

Three attempted independent checks were deliberately **not** converted into
claims:

1. Browser automation could not run because the connected Browser Use project
   lacked credits.
2. Generic web/container access could not independently reach/resolve the
   protected Netlify host.
3. A 24-character value inferred from the branch-version hostname returned 404
   from the Netlify deploy reader, so it was discarded rather than treated as a
   deployment ID.

## Findings

### DEP-SEC-001 — P0 before confidential customer data
**Netlify team MFA is not enforced.**

The team currently has one member, but MFA enforcement should be enabled before
confidential buyer data is accepted if the plan/platform supports it.

### DEP-SEC-002 — P0 before multi-tenant customer data
**Cross-tenant isolation is not proven.**

A real data plane plus two-tenant negative testing is required.

### DEP-SEC-003 — P0 before production parser use
**Parser sandboxing is not proven.**

The actual parser runtime must be linked and its resource/network/credential
boundaries tested.

### DEP-SEC-004 — P1
**Independent unauthenticated access evidence is not captured.**

Netlify configuration says SSO is required for all, but a black-box browser/HTTP
probe still needs to be preserved when a capable probe path is available.

## Claim boundary

This addendum is deployment-specific evidence, but it is **not** a security
certification and does not turn missing runtime/data-plane evidence into a pass.
