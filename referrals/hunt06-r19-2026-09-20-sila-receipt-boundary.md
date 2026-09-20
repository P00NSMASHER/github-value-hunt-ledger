# Cross-lane referral — Hunt 06 Run 19 — SiLA receipt identity / restart boundary

## Why this matters
`AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0` is migrating toward SiLA2. Its current `SilaNodeClient` tracks observable commands as an in-memory mapping from MADSci `ActionRequest.action_id` to a live SDK command instance. Its migration design proposes wiring the client ULID action ID 1:1 to SiLA `CommandExecutionUUID` by passing it at command creation.

Official SiLA 2 v1.1 observable-command initiation instead has the server return a `CommandExecutionUUID` in `CommandConfirmation`; the standard command-initiation request carries the command parameters and does not expose a client-selected execution-UUID field. Therefore restart-safe correlation should be treated as a persisted mapping/receipt problem, not simple ID equality.

## Exact gap
A safe adapter should durably preserve at least:

`(client_intent_id, server_uuid, feature_id, command_id, command_execution_uuid, execution_lifetime, receipt_persisted_at)`

and use that same external execution identity after orchestrator restart.

The hardest branch remains **pre-confirmation ambiguity**: if the server accepted/started a non-idempotent command but the `CommandConfirmation` response was lost, base SiLA has not yet given the client the execution UUID needed for normal status/result queries. This state must remain `RECONCILIATION_REQUIRED` unless an independent device/server fact proves APPLIED or NOT_APPLIED.

## Evidence
- Current client: `src/madsci_client/madsci/client/node/sila_node_client.py` — in-memory `_running_commands`; `command(**kwargs)`; missing tracked ID => UNKNOWN.
- Current action schema: `src/madsci_common/madsci/common/types/action_types.py` — client action ID is a generated ULID string.
- Current migration design: `openspec/changes/sila2-native-node-design/design.md` — proposes 1:1 Action ID ↔ CommandExecutionUUID mapping.
- Downstream tasks: `openspec/changes/sila2-native-node-design/tasks.md` — mapping still listed as implementation work.
- Project #293 remains open; #294 exploration is closed. This is a design/acceptance risk, not a proven deployed defect.
- Official SiLA 2 Specification v1.1 Part A/B — `CommandConfirmation` returns the server execution UUID used for later execution/result queries.

## Handoff target
Best owner: MASTER Integrator / standards-evidence or protocol-acceptance specialist.

## Exact unanswered technical question
**Can a rights-clean SiLA server/client fixture prove restart recovery by durably persisting `(MADSci action_id, ServerUUID, CommandExecutionUUID)`—and demonstrate that a lost pre-confirmation response remains blocked rather than reissued?**

## Recommended acceptance cases
1. request provably not accepted;
2. command accepted/effect started but confirmation response lost;
3. confirmation received but client crashes before receipt persistence;
4. receipt persisted and same execution is APPLIED;
5. receipt persisted and authoritative evidence proves NOT_APPLIED;
6. client restart with valid execution UUID;
7. SiLA server restart/UUID-lifetime boundary as a distinct test.

PASS requires APPLIED=>no replay, UNKNOWN=>blocked, and reissue only after independent NOT_APPLIED evidence.
