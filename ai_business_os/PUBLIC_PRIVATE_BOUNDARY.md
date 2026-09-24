# AI Business OS Public / Private Boundary

This repository is currently publicly visible, so public visibility is treated as a hard design
constraint rather than a future assumption.

## Allowed in public Git

- source code and deterministic tests;
- architecture/contracts that contain no private operating data;
- database schema/control migration source with private seed identifiers replaced by placeholders;
- sanitized aggregate production manifests and content hashes.

## Forbidden in public Git

- credentials, tokens, private keys or connection strings;
- live connector/payment account identifiers;
- customer or prospect names, email addresses, raw messages or uploaded records;
- raw bank/Stripe transaction payloads or customer financial records;
- live approval intent payloads or recipient-specific outbound content;
- mutable runtime databases or private evidence bytes.

## Private operating authority

Mutable operating state lives in the private Supabase schema `ai_business_os_prod`. Public files
may describe its contracts and sanitized aggregate state but never replace the private database as
the operating source of truth.

## Enforcement

`ai_business_os/test_public_boundary.py` checks the public AI Business OS production/migration
surfaces for live provider IDs, literal email addresses, connection strings, and private runtime
file types.

Repository visibility itself is an account setting not exposed by the connected GitHub API here.
The boundary therefore makes the repository safe under public visibility rather than claiming the
visibility setting was changed.
