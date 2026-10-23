# RETALLY OCI — remote canary and synthetic stage acceptance, 22 October 2026

**Customer production release: HOLD.** The existing Always Free `VM.Standard.E2.1.Micro` in Ashburn remains private. No inbound SSH/HTTP, new spend, real customer records, public route, durable installation or customer service startup is authorized by this verification.

## Confirmed provider observations

- The original owner Cloud Shell command was independently reconciled as `SUCCEEDED`, delivery `ACKED`, exit `0`, with the exact fixed marker; no duplicate was submitted.
- Earlier GitHub-created commands also executed successfully, but their workflows correctly remained red because OCI's per-command read returned 404. Those executions are evidence, not successful workflow acceptance.
- The caller policy remains bound to the dedicated identity domain, repository ID `1376771019`, repository, exact main workflow and target VM. Command creation is target-VM restricted. Readback is limited to instance-agent command records in compartment `ocid1.compartment.oc1..aaaaaaaayttmwe7jtksd5ufgkpakktondl7ydy5rm67hicxbqaxonbjaklxa`; no storage, network or IAM administration was granted. The separate read-only monitor trust was not changed.
- Protected-main fixes were merged through [PR #622](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/622), [PR #635](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/635), [PR #641](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/641), [PR #644](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/644), [PR #645](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/645) and [PR #650](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/650), each after exact-head CI. The fallback only lists at most 100 execution records for the approved compartment and VM after an exact GET 404, rejects pagination and duplicates, selects the exact command ID, and never retries creation.
- No-create reconciliation [run #39883110587](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39883110587) passed on protected main SHA `921418e73c5d9680950a3fa17ed0f546b875b8ce`, proving readback without creating a command.
- The single fresh GitHub canary [run #39883234315](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39883234315) passed on that same SHA. Oracle independently returned command `ocid1.instanceagentcommand.oc1.iad.amaaaaaaxrbeaqaak6uco5vpjuitrgwvtnryfcureul4w3ejmr7e2ygyqega` as `SUCCEEDED`, delivery `ACKED`, exit `0`, target instance `ocid1.instance.oc1.iad.anuwcljtxrbeaqace4i2bpvhoj7sq7slikstmkea5tw3c3vqfjujjg6pduqq`, and exact output `RETALLY_OCI_SYNTHETIC_CANARY_V1_OK`.

## Remaining source-locked readiness sequence

1. Merge this readiness workflow only after all exact-head required checks pass through protected `main`.
2. Pin the resulting exact main SHA, run one fresh no-write canary on that SHA, and require its live job to pass.
3. Enable the synthetic-readiness variables for that same SHA and dispatch this workflow with the verified canary run ID.
4. Preserve the generated operator-only receipt and rollback plan. This workflow does not install software, start a service, open a route, use customer data or authorize production.

Persistent host staging, encrypted off-device restore and separate host-scope authorization remain distinct HOLD gates. Never weaken the default-deny workbench Access application, backup controls, source immutability or billable-infrastructure gate to satisfy readiness.
