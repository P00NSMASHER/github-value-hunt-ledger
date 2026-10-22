# OCI Run Command API 404 reconciliation — October 22, 2026

**State:** Oracle executed both GitHub-initiated fixed no-write probes; GitHub's immediate execution lookup returned HTTP 404 before it could verify either probe. This document is *not* an assertion that the GitHub Actions workflow passed.

## Provider evidence

- [Original failed run #39819734570](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39819734570), attempts 1 and 2, used the exact approved main commit `5a349d3d0836c68224bff6507f998c09b081ac0a`.
- Read-only Oracle Audit shows a command accepted (`CreateInstanceAgentCommand` HTTP 200), followed approximately 0.35 seconds later by a command execution lookup (`GetInstanceAgentCommandExecution` HTTP 404) on attempt 2. The GitHub job failed `EXECUTION_LOOKUP_UNVERIFIED`.
- Owner-authenticated Cloud Shell later retrieved both original command IDs with `SUCCEEDED`, `ACKED`, exit code `0`, exact marker `RETALLY_OCI_SYNTHETIC_CANARY_V1_OK`. No command resubmission was necessary for reconciliation.
- The isolated OAuth principal's Oracle IAM policy was updated with `INSTANCE_AGENT_COMMAND_INSPECT` and `INSTANCE_AGENT_COMMAND_READ`, preserving all prior exact identity-domain, numeric repository, workflow ref and VM restrictions. Fresh provider readback verified the change. The 404 persisted after permission repair, pointing to propagation timing rather than failed on-host execution.

## Remediation and safeguards

The code in `oci_runcommand_canary.py` retries only a documented provider HTTP 404 on the **read-only execution lookup** for the *same accepted command ID*, up to 45 times at four-second intervals. Other lookup errors fail closed. A returned `FAILED`/unexpected state, mismatched VM or command ID, nonzero exit, or wrong output fails immediately.

No changes were made to the established read-only monitor, customer release gate, storage, hostname, public ingress, boot volume, or network permissions. A GH job must itself finish `run-synthetic-canary: success` against a freshly owner-approved **exact main SHA** before the staging readiness workflow can accept it. Never treat this offline fix, synthetic data or a skipped PR job as a successful live acceptance.

## Separate host acceptance

The existing `VM.Standard.E2.1.Micro` completed a read-only, temporary seven-branch synthetic stage test using `7778049571f79731a3023b03d5dc33b617f0a715`, with exact marker `RETALLY_OCI_SEVEN_BRANCH_EPHEMERAL_STAGE_OK`. The script deleted its temporary workspace and never started or installed a persistent service. This is host-level ephemeral acceptance, not durable customer deployment.

## Current-base reconciliation

The repair branch was reconciled with protected `main` `1b3b9bee41081f9f1ace7950ecac37d14ab5d7ba` after that branch advanced with the separate RT05 dispute-hold repair. The current-main change did not overlap the four OCI candidate files. Earlier green checks are not reused: the reconciled candidate requires fresh exact-head CI before any protected integration.
