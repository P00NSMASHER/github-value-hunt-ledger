# RETALLY OCI — remote canary and synthetic stage acceptance, 22 October 2026

**Customer production release: HOLD.** Existing Oracle Always Free `VM.Standard.E2.1.Micro` in Ashburn remains private, with zero inbound SSH/HTTP ports. No new spend, real customer records, public DNS, Cloudflare Tunnel, or customer service startup are authorized by this verification.

## Confirmed provider observations

- The original owner Cloud Shell command returned `SUCCEEDED`, delivery `ACKED`, exit `0` and the exact fixed synthetic canary marker, verified by querying its original OCI command ID without submitting a duplicate.
- **Both GitHub-initiated** no-write commands from GitHub Actions run [#39819734570](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39819734570) were accepted by Oracle and later independently reconciled on the target instance as `SUCCEEDED`, `ACKED`, exit `0`, exact marker. However, their GitHub jobs reported failure because the immediate `GetInstanceAgentCommandExecution` call returned HTTP 404 after creation. These are proven host executions, **not green GitHub workflow results**.
- Oracle authenticated Audit confirms `CreateInstanceAgentCommand` HTTP 200 followed by `GetInstanceAgentCommandExecution` HTTP 404 approximately 0.35 seconds later. After adding the narrowly scoped `INSTANCE_AGENT_COMMAND_INSPECT` and `INSTANCE_AGENT_COMMAND_READ` IAM permissions and independently verifying live readback, the transient lookup remained. The bounded GET-only fix is reviewed under [PR #622](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/622); it never resubmits an accepted command.
- The same existing Oracle E2 Micro also completed an **actual** ephemeral, exact-commit seven-branch synthetic acceptance run pinned to `7778049571f79731a3023b03d5dc33b617f0a715`. The exact `RETALLY_OCI_SEVEN_BRANCH_EPHEMERAL_STAGE_OK` marker was independently returned with an OCI `SUCCEEDED` command. Its temporary workspace was removed. No durable installation or systemd service activation was performed.

## Acceptance sequence still required

1. Merge the bounded read-404 repair PR only after all exact-head CI, including Windows encrypted-backup tests, passes through protected `main`.
2. Approve the resulting exact main commit SHA in GitHub Actions variables, then dispatch a fresh `RETALLY OCI Remote No-Write Canary` and **verify the GitHub `run-synthetic-canary` job itself completes successfully**. A skipped job, red run, timeout or matching marker in an unrelated Cloud Shell test is not sufficient.
3. Once this separate source-locked, read-only staging readiness workflow merges and its own `main` commit is CI green, run a **fresh** canary on that same SHA. Enable `RETALLY_OCI_SYNTHETIC_STAGE_ENABLED=true` and `RETALLY_OCI_SYNTHETIC_STAGE_APPROVED_SHA=<exact main SHA>` with the owner's permission, then dispatch the stage-readiness workflow with that SHA and the verified canary run ID.
4. The stage-readiness workflow only emits an operator-only receipt and rollback plan. It does **not** perform deployment. Actual persistent host staging, encrypted off-device restore and separate host acceptance remain distinct requirements before an operational service is started. Customer production remains HOLD.

Never weaken the default-deny workbench Access application, remove encrypted backup controls, submit customer claims, alter stored source originals or billable OCI infrastructure to satisfy these checks.
