# Private Runtime Deployment Contract

## Purpose

This runtime makes the merged CEO Command Center continuously available without placing Supabase
database credentials in the public GitHub repository or in the Railway service.

## Credential boundary

Railway stores only:

- `AIBOS_RUNTIME_TOKEN`: high-entropy token used to authenticate to the Supabase runtime gateway;
- `AIBOS_OPERATOR_TOKEN`: independent operator/API token for the future UI;
- `AIBOS_GATEWAY_URL`: non-secret Edge Function URL;
- `AIBOS_SCHEMA_FINGERPRINT`: canonical non-secret schema fingerprint.

The Supabase Edge Function receives `SUPABASE_DB_URL` from Supabase's built-in server-side secret
environment and connects directly to Postgres. GitHub contains only the SHA-256 hash of
`AIBOS_RUNTIME_TOKEN`, never the plaintext token.

## Gateway surface

Named operations only: health, portfolio view, planning inputs, exact approval lookup, creation of
one PENDING internal goal, and decision of one exact PENDING approval after intent-hash validation.
There is no arbitrary SQL operation and no approval-consume operation.

## Railway runtime surface

- `GET /health`
- `GET /dashboard`
- `POST /objective/propose`
- `POST /objective/activate`
- `POST /approval/decide`

Every operator route except health requires `AIBOS_OPERATOR_TOKEN`. The process probes the gateway
every 30 seconds and reports unhealthy when the live schema fingerprint no longer matches the
canonical fingerprint.

## Explicitly absent

This deployment does not expose a public domain, store a Supabase service/secret key in Railway,
accept arbitrary SQL, consume approvals, fabricate execution receipts, deploy other services, move
money, claim Hunter leases, or bypass independent verification/governance.
