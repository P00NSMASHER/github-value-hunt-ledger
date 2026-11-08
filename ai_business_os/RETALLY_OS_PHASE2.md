# RETALLY OS Phase 2 — live private owner desk

Date: 2026-11-08. Deployment source: `functions/api/internal/retally-os.js`, with the Cloudflare Pages project `retally-web`. This is a **native Cloudflare operational desk**, not a production deployment of the GopherCRM or Postmill upstream applications.

## Owner access

Open https://retallyrecovery.com/api/internal/retally-os from an iPhone or desktop. A self-hosted Cloudflare Access application protects exactly this endpoint. Its policy permits only the configured owner's email identity; the session lasts one hour and cookies are HTTP-only. The Pages Function verifies the RS256 Access assertion a second time against its fixed audience, issuer, and owner identity digest. The UI does not embed access tokens or real customer records in the HTML response.

Access application: `5a3aa136-1ced-4f55-80f5-9c792674331d`, audience `395437add099194675ac88c69a590bf6eefb587e54710ec436b99f50a4281594`. Both are public identifiers, not signing secrets. The sign-out link uses Cloudflare Access's logout route. No API key or owner email is present in this public source.

## Data boundaries

The existing production Pages `INQUIRY_DB` binding points to the authoritative `retally-inquiries` D1 database. GET `?view=data` fetches the most recent 100 inquiries and marks any reference from `inquiry_qa_registry` as synthetic. Real inquiry counts exclude QA records. A displayed inquiry does not certify a paying customer.

New tables in `freight/site/migrations/20261108_retally_os_phase2.sql` store only owner task state, versioned case notes, internal social drafts, and their append-only event history. These tables do not change the original `inquiries`, notification state or rate-limit tables. Optimistic concurrency requires the exact record version, so stale owner updates fail closed with HTTP 409.

Only three private actions exist: save a case, save a social draft, and mark a draft reviewed. Neither review nor save sends messages, schedules/publishes content, modifies customer invoices, collects payment, or sends anything to Postmill. A client cannot invent another action. Financial results remain **unknown** until independent source evidence exists.

The source query has an explicit 100-row limit. It is not a complete historical export, and customer onboarding beyond this window requires a reviewed pagination upgrade. Contact and case records must never be stored in a public repository, generated public HTML or application logs.

## Deployment order and acceptance

1. Merge the code through normal GitHub CI and exact-head release gates. This does not activate the route until Pages completes deployment.
2. Apply only the isolated `retally_os_*` D1 migration against the existing binding. Inspect `sqlite_master`, verify table existence and use `SELECT` on original inquiry counts to ensure no mutation.
3. Verify Cloudflare Access application policy and live production URL. Unauthenticated requests must not return customer JSON or unprotected HTML. Preview/alternate-host requests also fail authentication/host validation.
4. Authenticate as the configured owner, load the six tabs, verify live non-test metrics and synthetic annotations, save a case follow-up and draft with version conflict tests, and confirm the corresponding event history.
5. Verify that no outbound provider tokens, social posts, emails or payments were used. Recheck the public `/api/inquiry` status endpoint. Do not use synthetic records as real-customer outcome proof.

### Reproduce local regressions

```sh
node --experimental-default-type=module --experimental-sqlite --test freight/site/test_retally_os.mjs
node --experimental-default-type=module --check functions/api/internal/retally-os.js
```

## Upstream limitations

GopherCRM and Postmill Phase 1 pilots ran on disposable Linux hosts with persistent-test storage. They are **not** deployed to live RETALLY: the former's frontend had six high dependency advisories and the latter's pinned production dependency audit had four high (plus moderate/low). Their native Go/Node/PostgreSQL/Redis services require a private persistent host, patched dependencies, provider credentials and platform-specific tests. The Cloudflare-native desk provides real inquiry management and private social preparation without requiring a paid host or switching production sources.

The Phase 2 owner desk has no positive evidence of a real customer, verified recovered money, external platform publication, or a signed contract. Keep those outcome fields unknown until source records prove them.

## Existing social platform integration

The RETALLY Metricool brand ID `7322512` was verified from the connected Metricool account. Its Facebook/Instagram publishing connections already exist and it has separately scheduled posts. The operator desk links to that existing planner but does not create, publish, modify, duplicate, cancel or synchronize provider posts. The three new RETALLY OS drafts are separate unpublished internal editorial records; their IDs are native D1 IDs, not Metricool or Postmill IDs. A verified provider API integration is a distinct future deliverable.
