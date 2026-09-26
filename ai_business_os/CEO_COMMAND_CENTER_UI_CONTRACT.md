# CEO Command Center UI Contract

## Purpose

Step 4 exposes the existing production AI Business OS control plane through a human-facing, mobile-
friendly CEO dashboard without moving database or runtime credentials into browser code.

## Authentication

- Public `/health` remains minimal.
- `/ui` requires a separate CEO UI access code.
- Railway stores only `AIBOS_UI_ACCESS_SHA256`, never the plaintext access code.
- Successful login mints a signed, short-lived `HttpOnly; Secure; SameSite=Strict` session cookie.
- The cookie is principal-bound and expiry-bound.
- Mutating UI forms require a session-bound CSRF token.
- The production runtime token and operator token never enter HTML, JavaScript, cookies, URLs, or
  browser storage.

## Step-4 capabilities

The dashboard displays:

- production runtime health and schema fingerprint;
- portfolio businesses and initiatives;
- active agent fleet and heartbeat state;
- open goal queue;
- evidence/data gaps;
- pending human approvals in **read-only** form;
- persistent-worker leases and recent runs;
- governed objective proposal and activation.

Objective activation still creates only a PENDING internal goal and preserves the existing action-
class and human-approval constraints.

## Explicitly deferred to Step 5

The UI does not approve, reject, consume, or execute pending approvals. No approval-decision controls
are rendered in Step 4.

## Network boundary

The Railway service may have a public HTTPS domain only after this UI authentication layer is live.
All production data routes remain authenticated; the browser never talks directly to Supabase.
