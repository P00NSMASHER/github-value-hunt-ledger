# Portfolio Autonomy Matrix

Canonical source: `AUTONOMY_MATRIX.json`.

The matrix applies the global `OBSERVE / EXPERIMENT / MODIFY / ACT` taxonomy to every canonical project. The governing rule is simple: **the most restrictive applicable rule wins**.

| ID | Project | Observe | Experiment | Modify | Act |
|---|---|---|---|---|---|
| PRJ-000 | Portfolio Brain | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |
| PRJ-001 | RecoveryWorks | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |
| PRJ-002 | Freight Recovery | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |
| PRJ-003 | PermitPlate | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |
| PRJ-004 | CaptureBrief | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |
| PRJ-005 | StarBlox | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |
| PRJ-006 | ABVM Grade 2 Parent Companion | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |
| PRJ-007 | Market Surveillance Research Platform | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | PROHIBITED |
| PRJ-008 | Hunter / GitHub Value Hunt | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |
| PRJ-009 | AI Business OS | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |
| PRJ-010 | Browser Gateway | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |
| PRJ-011 | Evidence Data Ledgers | ALLOW | ALLOW_BOUNDED | ALLOW_BOUNDED | HUMAN_APPROVAL |

## System-wide interpretation

- **OBSERVE** may run autonomously for every project.
- **EXPERIMENT** is bounded to synthetic, local, shadow, reversible, or otherwise non-consequential work.
- **MODIFY** means candidate branches/commits/PRs only. It does not grant direct production or `main` authority.
- **ACT** is never generally autonomous. It is human-gated everywhere and fully prohibited for the market-surveillance project's external/live-action class.

## High-risk boundaries preserved

- RecoveryWorks/Freight cannot autonomously contact customers, submit claims, move money, or manufacture settlement evidence.
- PermitPlate cannot autonomously publish sensitive operational state or mutate customer operational state.
- CaptureBrief remains public/non-sensitive and human-supervised for customer delivery.
- StarBlox and ABVM require human authorization for consequential child-facing changes or experiments.
- Market Surveillance Research may research, retrain, test, and challenge models, but live trading, brokerage execution, autonomous positions, trade directions, and position sizing are prohibited.
- Hunter may hunt and create candidate research work, but it does not gain external commercial authority.
- AI Business OS may propose self-improvements on isolated branches but may not self-promote consequential changes.
- Browser Gateway remains least-privilege and cannot exceed explicitly authorized credentials or external-write scopes.
- Evidence Data Ledgers preserve immutable evidence and may not turn benchmark/context data into unsupported applicability claims.

This file defines governance intent. Runtime enforcement belongs in the later Portfolio Brain governance/control-plane implementation.
