# Tenant Isolation Evidence — FRT-SEC-001

**Status:** Internal repository/service-boundary proof complete; deployed pilot-service proof still required.

Freight Recovery scopes persistent pilot state by the tuple:

`buyer_id + business_unit`

This document records the deterministic internal negative-isolation rehearsal for gap `FRT-SEC-001`.

## What the rehearsal proves

`freight/tenant_isolation_rehearsal.py` runs three logical scopes against shared SQLite files:

- `BUYER-A / OPS`
- `BUYER-A / FIN`
- `BUYER-B / OPS`

The rehearsal intentionally reuses the same local claim IDs, settlement-event IDs, source hashes, audit object IDs and evidence hashes across scopes.

It verifies:

1. identical local settlement IDs can coexist across buyer/BU scopes;
2. realized settlement totals remain scope-bound;
3. a settlement event in one buyer cannot discover a same-reference claim in another buyer;
4. manual reviewed allocation cannot bind another buyer's claim;
5. the same buyer cannot read a claim from another business unit;
6. composite SQLite foreign keys reject a direct-SQL cross-scope allocation;
7. settlement snapshots remain scope-bound;
8. identical audit object IDs can coexist across scopes;
9. AuditStore reads return only the constructor buyer/BU;
10. audit hash chains remain independently scope-bound;
11. all scope rows physically coexist in one shared audit DB while service reads remain isolated.

The rehearsal emits one deterministic `evidence_hash` over the exact check set and results.

## What this does not prove

This evidence does **not** close `FRT-SEC-001`.

The verified September 21 pilot environment is intentionally single-tenant and records multi-tenant isolation as `NOT_APPLICABLE`. Therefore the current repository rehearsal cannot honestly be described as deployed multi-tenant authorization proof.

The gap still requires evidence from the actual pilot data service:

- equivalent negative cross-scope attempts against deployed authorization/service boundaries;
- deployed tenant/buyer/BU authorization context for those attempts;
- audit/security logs showing the denied cross-scope attempts.

Until those artifacts exist, the gap remains `ACTIVE_INTERNAL`.

## Why keep the internal evidence

The rehearsal establishes that the current durable reference stores are structurally ready for scoped persistence and negative isolation testing. It also prevents regressions in:

- buyer scoping;
- business-unit scoping;
- composite settlement foreign keys;
- scope-filtered reads;
- scope-bound audit chains.

It is repository evidence, not a certification or a claim that a shared multi-tenant production service has been deployed.
