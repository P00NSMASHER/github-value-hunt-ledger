# Business OS → Hunter Execution Bridge Contract

## Purpose

This bridge moves only explicitly Hunter-eligible AI Business OS portfolio evidence gaps into the
existing Technology Intelligence allocator. It does **not** create a second Hunter scheduler.

The path is:

```
AI Business OS portfolio plan
  -> deterministic Business OS Hunter seed
  -> existing TI allocator / assignment projection
  -> existing activation + dispatch packet
  -> existing READY / CLAIM / lease / START lifecycle
  -> canonical search-run telemetry
  -> existing independent verification / Integrator
```

## Eligibility

A Business OS work item may enter the bridge only when the planner already marks
`hunter_eligible = true` and the required source type is one of:

- PUBLIC_GITHUB
- PUBLIC_CODE
- OPEN_SOURCE
- REPOSITORY
- TECHNICAL_IMPLEMENTATION

Bank, ledger, CRM, customer-response, private analytics, invoices, manual records, or other
non-public/non-technical gaps never enter this bridge.

## Authority boundary

Bridge packets remain planning/scheduling evidence only.

They cannot:

- claim a Hunter slot;
- create or renew a lease;
- emit READY, CLAIM, START, COMPLETE, FAIL, or RELEASE;
- mark a Business OS gap resolved;
- perform external writes;
- contact people;
- spend money;
- deploy code;
- alter a repository;
- bypass Hunter independent verification.

All such actions remain under the existing Worker Runbook and governance.

## Capacity isolation

Only `SLOT-09` may accept `business_os_gap` work. Native Hunter coverage capacity in
`SLOT-07` and `SLOT-08` remains reserved, so portfolio demand cannot consume the Hunter
system's required blind-spot exploration budget.

## Provenance

Every packet preserves:

- Business OS plan hash;
- Business OS work ID;
- deterministic bridge seed hash;
- initiative and metric identity;
- gap type;
- required public technical source type;
- bounded acceptance target;
- no-external-write / human-approval flags.

The existing TI assignment projection then binds that provenance into the generated assignment and
claim lifecycle.

## Current production state

The bridge may legitimately contain zero seeds. A zero-seed feed means the current Business OS
portfolio has no unresolved evidence gap whose required source is explicitly public and technical.
That is a healthy fail-closed state, not an error.
