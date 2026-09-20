# Hunt 06 referral — SiLA execution identity scope / EXP-007

## Why this matters
EXP-007 now has a concrete **client-restart recovery primitive** but a separately unresolved **server-restart / pre-confirmation ambiguity**.

At `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0`, observable SiLA commands are still tracked only in the process-local `_running_commands` map after the SDK call returns. MADSci currently depends on `sila2>=0.10.0`; its checked-in example server was generated with `sila2` 0.14.0.

Current `sila2` 0.14.0 documentation exposes `ClientObservableCommandInstance(parent_client, client_command, execution_uuid, lifetime_of_execution=None)`, so a client that has durably stored a server-assigned `CommandExecutionUUID` can plausibly reconstruct the command instance after a **client-only** restart and query the same operation instead of redispatching.

The SiLA 2 v1.1 protocol puts a strict boundary around that: `CommandExecutionUUID` is unique within one SiLA Server instance/lifetime, while `ServerUUID` is generated once and remains stable even after the server lifetime ends. Therefore stable `ServerUUID` continuity across a server restart does **not** establish execution continuity, and an old/invalid execution UUID is not NOT_APPLIED proof.

## Recommended EXP-007 tuple
Persist:

`(client_intent_id, intent_hash, ServerUUID, feature_fqi, command_identifier, CommandExecutionUUID, lifetime_of_execution, receipt_received_at, receipt_durable_at, client_runtime_version, sila_runtime_version)`

Then fault separately:
1. confirmation never received;
2. client crash after confirmation but before receipt durability;
3. client crash after receipt durability with server lifetime still valid;
4. server restart after receipt durability;
5. execution-lifetime expiry.

Only branch 3 should be eligible for ordinary same-operation rebind through the base SiLA receipt. Branches 1/2/4/5 stay `RECONCILIATION_REQUIRED` unless a stronger server/device-specific idempotency/history mechanism exists.

## Exact unanswered technical question
**Does a current production SiLA implementation expose a durable server boot/session epoch, operation-history lookup, client correlation token or idempotency mechanism that can distinguish “old execution receipt invalid because the server restarted” from “the physical effect definitely did not occur,” without redispatching the action?**

## Negative knowledge
- Same `ServerUUID` is not same server execution lifetime.
- `InvalidCommandExecutionUUID` / expired UUID is not proof of physical non-application.
- Server-assigned execution identity only helps after the confirmation receipt is captured durably.
- The legacy `sila2` Python package is currently maintenance-only; MADSci's broad `>=0.10.0` range should be pinned for any acceptance artifact, and behavior must not be silently transferred to the maintained UniteLabs implementation.

## Source run
`hunters/21-run20-2026-09-20.md`
