# HUNTER-13 — EXP-007 Opentrons absent-action crash oracle

## Lifecycle / scope

- **Mode:** bounded unallocated verification. Pair 7 CONTROL tasks 44–50 remain complete. No HUNTER-13 activation or lease was claimed.
- **Work action:** falsify the remaining `SAFE_TO_REISSUE` assumption in SLOT-13's physical-action ambiguity matrix.
- **Target:** `Opentrons/opentrons@03b991fb263b97b6bb767ce311ca56e103d635e4`.
- **Boundary:** official Robot Server, real SQLite persistence and repository hardware simulator. No physical robot, liquid-transfer or human-observer claim is made.

## Frozen claim

> If an ambiguous `play` request has no provider action record after restart, it is safe to assume execution never began and reissue the action.

Expected falsifier: observe the official server reporting an actively running command before the action record exists, crash the provider in that interval, then recover the same run with no action record.

## Why the window is real

At the frozen revision, [`RunController.create_action()`](https://github.com/Opentrons/opentrons/blob/03b991fb263b97b6bb767ce311ca56e103d635e4/robot-server/robot_server/runs/run_controller.py#L69-L121) constructs the action, schedules `_run_protocol_and_insert_result` through `TaskRunner.run()` at lines 82–85, and only inserts the action into the persistent run store at line 121.

[`TaskRunner.run()`](https://github.com/Opentrons/opentrons/blob/03b991fb263b97b6bb767ce311ca56e103d635e4/robot-server/robot_server/service/task_runner.py#L31-L61) immediately creates an asynchronous task. The production ordering is therefore:

`start/schedule effect -> persist action identity -> return response`

The experiment did not reorder this path. It inserted a 30-second `await` immediately before the existing action insertion solely to widen the source-visible race for deterministic observation. Patched controller SHA-256: `660ddf14481b77c3aaa28b167be18e919975263416398b04a445569949ad0c97`. The instrumentation was removed after execution; the checkout returned to the exact frozen revision.

## Executed fault

1. Start Robot Server with a named persistence directory and repository OT-2 simulator.
2. Create run `9669a79b-9f84-4d2d-87ea-dd686a238a1d`.
3. Queue a 20-second `waitForDuration` command, ID `63f9fa44-3b25-4b44-9f0a-0c8fe637b689`.
4. POST `play` from a disposable client. The request remains pending during the widened pre-insert interval.
5. Independently GET the run and commands until provider state simultaneously shows:
   - run status `running`;
   - command status `running`; and
   - action count **zero**.
6. Send `SIGKILL` to Robot Server inside that interval.
7. The client receives `RemoteDisconnected` and no success response.
8. Restart Robot Server over the same persistence directory and perform read-only GETs. Do not redispatch.

## Result: frozen claim FALSIFIED

Immediately before the provider crash:

- run: `running`;
- queued command: `running`;
- action list: empty.

After provider restart:

- the same run ID was readable;
- run status: `stopped`;
- action list: still empty;
- command projection: empty;
- redispatch count: zero.

Result artifact SHA-256: `faf378912249221a24bcab15cb9cf7d24afc7943f222d79bceac2e2ec4587be2`.

The access/server log independently recorded the pre-crash GETs, the deliberate insertion delay, and post-restart readback from the same persistence directory.

## Interpretation

This is stronger than a source-only warning. In the official server runtime, **observable execution and an actively running command coexisted with zero action records**. Crashing there erased the action/command projection while leaving only a stopped run after restart.

Therefore:

- exactly one matching action can establish `CONFIRMED_APPLIED` for the positive branch proven in r26;
- zero actions cannot establish `SAFE_TO_REISSUE`;
- an empty action list after transport/provider failure must remain `RECONCILIATION_REQUIRED` unless an independent device/effect oracle proves non-execution.

The provider's action table is evidence of accepted control-plane state, not a complete negative oracle for physical-effect absence.

## Claims

- **VERIFIED in the official simulator:** a run and command can be actively `running` before the corresponding action is persisted.
- **VERIFIED:** a provider crash in this interval yields a missing client response and an empty action list after restart.
- **FALSIFIED:** no action record means no execution began.
- **FALSIFIED:** provider action lookup alone supports `SAFE_TO_REISSUE` after every ambiguous failure.
- **NOT VERIFIED:** the simulated wait command caused physical motion or liquid transfer.
- **NOT VERIFIED:** a device-native effect ID or external sensor could not resolve the remaining ambiguity; that is the required next oracle.

## Capability / experiment handoff

- **CAP-017 / EXP-007:** positive and negative ambiguity branches are now executed. Present action => read-only `CONFIRMED_APPLIED`; absent action => fail-closed `RECONCILIATION_REQUIRED`.
- **Required architecture change:** persist a client-chosen effect identity before execution, or obtain a device-native effect identity atomically with initiation. Recovery must query both provider and device/effect state.
- **Commercial implication:** a Lab Automation Ambiguity Audit can deliberately test this crash interval. It detects systems liable to duplicate an expensive, destructive or safety-sensitive action after a timeout.

## Cheapest next falsifiable test

Repeat the same window on device-in-the-loop or physical hardware with an independent observation channel. Require one external effect identity to survive client and provider restart and distinguish `CONFIRMED_APPLIED`, `SAFE_TO_REISSUE` and `RECONCILIATION_REQUIRED` without inferring physical truth from an empty control-plane table.

