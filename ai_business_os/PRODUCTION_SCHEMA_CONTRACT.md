# Production Database Source-of-Truth Contract

The live Business Brain is the private Supabase schema `ai_business_os_prod`.

## Versioned public source

`supabase/migrations/ai_business_os/bootstrap.sql` is the ordered production migration history
exported from Supabase. Live provider account identifiers found in historical seed-data statements
are replaced with explicit `__PRIVATE_...__` placeholders before entering this public repository.

`manifest.json` retains:

- every applied migration version and name;
- the SHA-256 of each exact live migration statement;
- the current live schema fingerprint;
- the list of required private placeholders.

This gives Git enough information to reconstruct and audit the database definition without publishing
private operating identifiers.

## Drift check

The live database exposes:

`ai_business_os_prod.schema_fingerprint_v1()`

Compare that value with `manifest.json.live_schema_fingerprint_sha256`. Canonical CI always checks
migration ordering and manifest integrity. A private CI environment may additionally set
`AI_BUSINESS_OS_LIVE_SCHEMA_FINGERPRINT` to enforce live drift failure.

## Change rule

Never edit historical live migration hashes. Apply future DDL through a new Supabase migration,
then refresh the public sanitized bootstrap + manifest.
