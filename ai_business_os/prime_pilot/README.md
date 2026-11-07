# Prime Agent engineering pilot

This local acceptance fixture runs the pinned Prime binary twice. It records a real JSONL prompt acknowledgment, kills the first worker, waits for the actual 30-second lease to expire, and starts a second worker. A deterministic upstream faux model supplies a prepared SQL diff. The independent verifier initializes a clean synthetic repository, clones it, reproduces a duplicate after a lost response, applies the candidate to the Git index, and runs the retry again against a new local SQLite database. The verified object and patch hashes are in [receipt.json](receipt.json).

## Reproduce

Requires Linux with unprivileged user, PID, and network namespaces, util-linux, bubblewrap with `--disable-userns`, Bash, Git, Python 3 and Node 22.8 or newer. Use a disposable checkout without account credentials. From the RETALLY repository root run the following.

```bash
pilot="$PWD/ai_business_os/prime_pilot"
prime=$(mktemp -d)
git clone https://github.com/PrimeIntellect-ai/prime-agent.git "$prime"
git -C "$prime" checkout --detach e311d6495124cf0bdc629c813fc97a39a9a3054d
bash "$pilot/prepare.sh" "$prime"
(cd "$pilot" && npm ci --ignore-scripts --no-audit && node pilot.mjs "$prime")
```

Run the verifier alone with `cd ai_business_os/prime_pilot && python3 verify.py < replay.patch`. The synthetic base commit is `75b32959e630c606fd20086b08d59dc30b645905`. The reviewer expects exactly one row per distinct inquiry after losing a create response, reconnecting and retrying. It rejects free-text success, extra paths, changed file modes, and patches that fail the trusted behavioral test. SQLite allows the single candidate statement to read the inquiry reference and insert in the fixture table, with an execution-step limit. The verifier never runs commands supplied by the model.

## Environment and authority

On November 7, 2026, the pinned source installed 432 packages using its lockfile. Node 24.22.1 built its bundled CLI. Running the absolute source launcher with `--mode rpc --session-dir` from a disposable fixture worktree failed at the tsx Unix socket with `listen EPERM`. Running the launcher's supported `--dist` option reached the default daemon and encountered the same host restriction on `daemon.sock`. The passing test uses `--dist` with the pin's internal legacy owned-worker frontend, which supports parent/child IPC in this host. A separate run with the faux provider omitted returned a correlated unsuccessful prompt response and the error `No API key found for the selected model.` A real model-generated change requires an authorized zero-cost connection.

The sandbox includes only a synthetic read-only worktree, explicitly mounted runtime dependencies, local fixture data, and 128 MiB of private writable tmpfs. It clears inherited environment variables, separates network and process namespaces, drops capabilities, disables nested user namespaces and disables model tools. The worker returns a proposed patch over stdout. It cannot edit the trusted checkout, run model-issued commands, spawn model subagents, push code, or reach a provider. The supervisor enforces a 25-second deadline, a capped response stream and process limits. The test cancels the first worker with SIGKILL, observes process exit, and reclaims only after its persisted lease expires. The 25-second hard deadline also bounds process lifetime below the 30-second lease. Global persistent refinement is unavailable because the worker's home expires with the sandbox.

The broker uses PGlite 0.3.14, a local embedded PostgreSQL engine, with the four canonical worker tables and the functions from the persistent-worker migration, including the actual claim, requeue and submit operations. The harness reopens its temporary database before reclamation. It omits the pg_cron scheduling statement. The canonical gateway and production database were not contacted by this pilot. Submission enters `VERIFYING`; the recorded verdict covers the synthetic SQL fixture. It grants no release authority. A customer-facing adapter that can run arbitrary model code, or a production lease cancellation listener, would require further integration.

## Pin and dependency evidence

The upstream reference is `e311d6495124cf0bdc629c813fc97a39a9a3054d`, with package-lock SHA-256 `b316b3e5c1b5f589c86fa6453160dd7309929b6a2b5bfa4b08892da1c13474d6`. The checkout's observed default-branch head was `74591cddef28d11249c3171112114fc4755375d7`. The fixture preserves the requested reference. Its upstream MIT copyright and permission notice must accompany redistributed copies or substantial portions. The pilot refers to an upstream checkout and does not redistribute its source or binary.

The November 7 production-dependency npm audit of the upstream pin reported 22 affected packages, including two critical, eleven high, and nine moderate. Critical entries named `proxy-addr` (GHSA-jqcg-44mw-7w3h) and `shell-quote` (GHSA-pqg4-j6r4-53mv). The isolated pilot's own one-dependency npm audit returned zero findings. Re-run both audits before widening execution.

[Pinned RPC contract](https://github.com/PrimeIntellect-ai/prime-agent/blob/e311d6495124cf0bdc629c813fc97a39a9a3054d/packages/coding-agent/docs/rpc.md), [pinned launcher](https://github.com/PrimeIntellect-ai/prime-agent/blob/e311d6495124cf0bdc629c813fc97a39a9a3054d/prime-agent.sh), [upstream license](https://github.com/PrimeIntellect-ai/prime-agent/blob/e311d6495124cf0bdc629c813fc97a39a9a3054d/LICENSE), [canonical lease migration](../../supabase/migrations/ai_business_os/20260925151646_add_ai_business_os_persistent_worker_control_v1.sql), [worker backlog](../../production/BACKLOG.md).
