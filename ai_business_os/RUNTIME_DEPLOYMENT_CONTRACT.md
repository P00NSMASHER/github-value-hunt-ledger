# Private Runtime Deployment Contract

## Purpose

This runtime makes the CEO Command Center continuously available without placing Supabase database
credentials in the public GitHub repository, Railway browser code, or client storage.

## Credential boundary

Railway stores:

- `AIBOS_RUNTIME_TOKEN`: high-entropy server-to-server token for the Supabase runtime gateway;
- `AIBOS_OPERATOR_TOKEN`: independent token for the existing JSON operator API;
- `AIBOS_GATEWAY_URL`: non-secret Edge Function URL;
- `AIBOS_SCHEMA_FINGERPRINT`: canonical non-secret schema fingerprint;
- `AIBOS_UI_ACCESS_SHA256`: SHA-256 of the separate CEO UI access code;
- `AIBOS_UI_SESSION_SECRET`: high-entropy server-side session-signing secret;
- `AIBOS_UI_PRINCIPAL`: human principal bound to CEO UI sessions.

The plaintext CEO access code is not stored in Railway. The browser never receives the runtime token,
operator token, database URL, or session-signing secret.

## Gateway surface

Named operations only: health, portfolio view, planning inputs, worker status, exact approval lookup,
creation of one PENDING internal goal, approval decision after exact intent-hash validation, and the
bounded persistent-worker lease operations. There is no arbitrary SQL operation and no
approval-consume operation.

## Railway runtime surface

Machine/API surface:

- `GET /health` — public minimal health only;
- `GET /dashboard` — operator-token protected JSON;
- `POST /objective/propose` — operator-token protected;
- `POST /objective/activate` — operator-token protected;
- `POST /approval/decide` — operator-token protected.

CEO browser surface:

- `GET /ui` — login or authenticated Command Center;
- `POST /ui/login` — exchanges the separate access code for a signed HttpOnly session;
- `POST /ui/logout`;
- `POST /ui/objective/propose`;
- `POST /ui/objective/activate`.

Step 4 shows the approval queue read-only. Browser approval decisions are intentionally deferred to
Step 5.

## Browser security

- session cookie: `HttpOnly; Secure; SameSite=Strict`;
- session is expiry-bound and principal-bound;
- UI mutations require a session-bound CSRF token;
- strict CSP disables browser scripts;
- responses use no-store, frame denial, no-referrer, and restrictive permissions headers.

## Public-domain boundary

A Railway HTTPS service domain may be enabled only after the authenticated UI is deployed and
verified. Production data and mutation routes remain authenticated.

## Explicitly absent

The browser cannot access Supabase directly, submit arbitrary SQL, consume approvals, fabricate
execution receipts, move money, perform destructive operations, or bypass independent verification
and governance.
