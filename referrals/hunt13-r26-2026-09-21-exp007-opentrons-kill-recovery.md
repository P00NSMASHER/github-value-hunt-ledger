# HUNTER-13 — EXP-007 Opentrons accepted-before-receipt kill recovery

## Lifecycle / scope

- **Mode:** bounded unallocated verification. Pair 7 CONTROL tasks 44–50 remain complete. The live activation log contains no HUNTER-13 activation, so no lease or assignment was claimed.
- **Work action:** execute the remaining SLOT-13 real-provider ambiguity branch against the exact Opentrons revision already inspected.
- **Target:** `Opentrons/opentrons@03b991fb263b97b6bb767ce311ca56e103d635e4`.
- **Boundary:** official Robot Server and its real SQLite persistence path were used with the repository's hardware simulator. This does not prove physical liquid transfer, robot motion or human-in-the-loop observation.
- No upstream write, issue filing, release action or broad discovery was performed.

## Question

If Robot Server accepts `play` but the client dies before it receives or persists the `201 Created` response, can a fresh process use only a precommitted run ID and an authoritative read-only provider query to classify the original effect without redispatch?

## Fault injection

1. Start the official Robot Server at the frozen revision with a named persistent directory and repository-supplied OT-2 hardware simulator.
2. Create run `9427e6a9-64c7-4d81-a198-7c7b4571aa5e` and queue a three-second `waitForDuration` command.
3. Before dispatch, the disposable client durably writes `runId` plus intended action `play` and calls `fsync`.
4. A one-shot transport proxy forwards `POST /runs/{runId}/actions` to Robot Server.
5. The proxy fully receives provider status **201** and action ID `36e06d58-7e04-4bce-9234-b7a9e7de3102`—proving provider acceptance—then sends `SIGKILL` to the client **without forwarding any response bytes**.
6. The killed client exits `-9`; its receipt file does not exist.
7. A fresh recovery process reads the precommitted run ID and issues only `GET /runs/{runId}`. It does not POST another action.
8. After the run completes, Robot Server is stopped and restarted over the same persistence directory. A second fresh `GET` checks durability across provider restart.

## Result: positive ambiguity branch PASS

| Checkpoint | Provider readback | Classification |
|---|---|---|
| Immediately after client death | HTTP 200; run `running`; exactly one `play`; same action ID | `CONFIRMED_APPLIED` |
| Eventual state | run `succeeded`; exactly one `play`; same action ID | `CONFIRMED_APPLIED` |
| After Robot Server restart | HTTP 200; run `succeeded`; exactly one `play`; same action ID | `CONFIRMED_APPLIED` |

All seven executable assertions passed:

- provider returned 201 before the client was killed;
- the client was killed;
- no provider receipt was durably recorded by the client;
- the same run ID was recovered;
- exactly one `play` action existed;
- its ID exactly matched the provider-accepted action ID; and
- read-only recovery classified the effect as `CONFIRMED_APPLIED`.

**Redispatch count: zero.**

The server access log independently recorded the action POST as 201, the first GET as 200 while execution was active, clean shutdown/startup using the same persistence directory, and a post-restart GET as 200.

## Source-backed interpretation

This positive result matches the implementation shape:

- [`RunController.create_action()`](https://github.com/Opentrons/opentrons/blob/03b991fb263b97b6bb767ce311ca56e103d635e4/robot-server/robot_server/runs/run_controller.py#L45-L124) assigns an action ID, starts/resumes execution, inserts the action into the run store and returns it.
- [`RunStore.insert_action()`](https://github.com/Opentrons/opentrons/blob/03b991fb263b97b6bb767ce311ca56e103d635e4/robot-server/robot_server/runs/run_store.py#L255-L274) persists that identity transactionally in SQLite.
- [`GET /runs/{runId}`](https://github.com/Opentrons/opentrons/blob/03b991fb263b97b6bb767ce311ca56e103d635e4/robot-server/robot_server/runs/router/base_router.py#L456-L467) returns the run projection used for authoritative recovery.

The crucial distinction is that recovery uses **provider-owned identity and state**, not a retry assumption based on the missing client receipt.

## Negative boundary preserved

This run proves only the `CONFIRMED_APPLIED` branch after the provider's accepted response. It does **not** prove `SAFE_TO_REISSUE` when no action is visible.

In fact, source order preserves the earlier warning: on a new play, the controller schedules protocol execution at lines 82–85, but inserts the action only at line 121. Therefore an empty action list after a lower-level crash is not proof of no effect. The safe classifier remains:

- one matching provider action: `CONFIRMED_APPLIED`;
- conflicting or multiple actions: `RECONCILIATION_REQUIRED`;
- no matching action: `RECONCILIATION_REQUIRED`, **not** `SAFE_TO_REISSUE`, absent stronger device evidence.

## Claims

- **VERIFIED in the official simulator:** accepted `play` survives total client receipt loss and is recoverable read-only by the precommitted run ID.
- **VERIFIED:** recovery remains correct across Robot Server restart and returns the identical action ID.
- **VERIFIED:** the recovery procedure performs no redispatch and observes exactly one action.
- **FALSIFIED:** absence of a client-side 201 receipt makes blind replay necessary.
- **NOT VERIFIED:** an absent provider action proves the physical effect did not begin.
- **NOT VERIFIED:** simulator execution proves robot motion, liquid transfer or human observation.

## Capability / experiment handoff

- **CAP-017 / EXP-007:** the Opentrons positive ambiguity branch now has an executed provider-backed receipt instead of source-only inference.
- **Acceptance rule:** persist run/effect identity before dispatch; after ambiguous transport failure, query the provider by that identity; permit no redispatch on `CONFIRMED_APPLIED`; keep absence/conflict fail-closed.
- **Commercial implication:** this is a reusable acceptance test for automation gateways whose apparent timeout may hide an accepted physical action. It separates transport success from effect truth and can prevent duplicate high-cost actions.

## Cheapest next falsifiable test

Repeat the same proxy-controlled window on physical hardware or a device-in-the-loop fixture with an independent observation channel. Require the recovered run/action ID to correlate with one—and only one—observable physical effect. Do not relax the absent-action branch until independent device evidence can prove non-execution.

