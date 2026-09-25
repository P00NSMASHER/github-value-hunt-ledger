# Stable Project ID Registry

Canonical machine-readable source: `PROJECT_ID_REGISTRY.json`.

## Identity rules

- Project IDs are immutable and never recycled.
- Renames are represented as aliases, not new IDs.
- Repository identity and project identity are separate; one repository may contain several projects and one project may span repositories.
- Subsystems inherit their top-level project ID until a later entity schema assigns a narrower stable entity ID.

## Current top-level IDs

| ID | Project | Parent | Repository scope |
|---|---|---|---|
| PRJ-000 | Portfolio Brain | — | reserved |
| PRJ-001 | RecoveryWorks | — | REPO-001 |
| PRJ-002 | Freight Recovery | PRJ-001 | REPO-001 |
| PRJ-003 | PermitPlate | — | REPO-005, REPO-006 |
| PRJ-004 | CaptureBrief | — | REPO-007 |
| PRJ-005 | StarBlox | — | REPO-002 |
| PRJ-006 | ABVM Grade 2 Parent Companion | — | REPO-003 |
| PRJ-007 | Market Surveillance Research Platform | — | REPO-004 |
| PRJ-008 | Hunter / GitHub Value Hunt | — | REPO-001 |
| PRJ-009 | AI Business OS | — | REPO-001 |
| PRJ-010 | Browser Gateway | — | REPO-001 |
| PRJ-011 | Evidence Data Ledgers | — | REPO-001 |

## Important identity decisions

- RecoveryWorks is the umbrella project; Freight Recovery keeps its own child project ID because it has a substantial independent commercial/control-plane implementation.
- PermitPlate spans the public application and its operational-state repository.
- Market Surveillance Research is explicitly research-only; trading/execution authority is not part of its project identity.
- Hunter and AI Business OS share a repository but remain separate top-level projects because they have different objectives, state and future runtime responsibilities.
- The four evidence ledgers are grouped as one data-infrastructure project family for now; their individual component identities remain visible through aliases and will receive stable entity IDs in the later universal schema.

## Reserved control-plane identity

`PRJ-000` is reserved for Portfolio Brain so future implementation can start with a stable identity rather than inventing one after events already exist.
