# RETALLY — Oracle remote execution canary

**Status: source candidate; live Oracle execution HOLD until independently provisioned and verified.** This is not an approval for customer workloads, infrastructure spending, or a public private-workbench endpoint.

## Why this exists

The existing GitHub-hosted, Oracle-authenticated metadata monitor works without PAAM-L044, but its identity cannot perform Run Command. Keep its workflow, trust, client and IAM permissions unchanged. This new, manual-only lane creates a **separate** federated identity for one fixed synthetic test. Do not reuse the original monitor client or enlarge its IAM policy.

The target is the existing `VM.Standard.E2.1.Micro` in Ashburn, currently known to have zero inbound network access. Oracle Run Command can operate without public SSH when its agent, IAM and outbound OCI API connectivity are correctly configured. The instance currently uses Ubuntu 24.04; the official Run Command supported-image list historically omitted Ubuntu, although Oracle Cloud Agent 1.61.0 added Ubuntu snap support in June 2026. The actual installed version and capability on this VM remain **unverified**. Never replace the VM or select a paid image just to make a check pass.

## One-time Oracle administrator prerequisites

1. In the existing Oracle Identity Domain, create a NEW nonadministrator confidential OAuth client with token exchange only. It must not have tenancy-admin grants. Keep the secret only in GitHub Actions encrypted secrets.
2. Create a NEW `IdentityPropagationTrust` binding GitHub's signed OIDC issuer `https://token.actions.githubusercontent.com`, audience `https://cloud.oracle.com`, exact owner ID `22281248`, repository ID `1376771019`, branch `refs/heads/main`, and exact workflow ref `P00NSMASHER/github-value-hunt-ledger/.github/workflows/retally-oci-runcommand-canary.yml@refs/heads/main`. Include the repository and workflow claims in OCI policy matching. No wildcards, forks, or broad impersonation.
3. Grant the new identity, in the narrowest compartment containing ONLY the approved target where possible, the minimum required operations: `INSTANCE_READ`, `INSTANCE_AGENT_PLUGIN_INSPECT`, `INSTANCE_AGENT_COMMAND_CREATE`, and `INSTANCE_AGENT_COMMAND_EXECUTION_INSPECT`. Bind its trust claims and verify the target-instance condition actually applies to **CreateInstanceAgentCommand**. If OCI cannot enforce the exact target at that API, use a dedicated compartment with no other VMs rather than granting all-compartment remote shell privileges.
4. For the VM itself, Oracle requires a dynamic group restricted to its exact instance ID with permission `use instance-agent-command-execution-family` in its compartment, scoped to its own instance. This separate target-side principal permission is NOT a license to grant object-storage, network, or IAM access to the GitHub caller.
5. On the already-authorized VM shell/console, independently verify that Oracle Cloud Agent is installed and the **Compute Instance Run Command** plugin is supported, enabled and running. Confirm a nonroot execution identity. The canary does not need `sudo`; do not add passwordless sudo or open any ports. Check OCI Audit and negative tests confirming other VM command creation, object access, IAM/network changes and admin actions are denied.

Relevant Oracle official references:
- https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/runningcommands.htm
- https://docs.oracle.com/en-us/iaas/Content/Compute/Tasks/manage-plugins.htm
- https://docs.oracle.com/en-us/iaas/Content/Identity/Reference/corepolicyreference.htm

## GitHub configuration AFTER passing the above checks

Add NEW encrypted GitHub Actions secrets `RETALLY_OCI_RUN_CLIENT_ID`, `RETALLY_OCI_RUN_CLIENT_SECRET`. Add NEW variables `RETALLY_OCI_RUN_DOMAIN_URL` (identity-domain HTTPS origin), `RETALLY_OCI_VM_COMPARTMENT_OCID` (the dedicated compartment containing only the approved VM), `RETALLY_OCI_RUN_COMMAND_COMPARTMENT_OCID` (the same compartment, for command records), `RETALLY_OCI_RUN_APPROVED_SHA` (exact CI-green main SHA), and `RETALLY_OCI_RUN_COMMAND_ENABLED`. The last flag must stay absent or `false` until the independent checks and complete configuration pass. The script reuses `RETALLY_OCI_VM_OCID` to pin the target, but NEVER the original monitor's secret. Keep command creation restricted to that exact VM; grant command-result reads only inside its dedicated compartment.

Run **Actions → RETALLY OCI Remote No-Write Canary → Run workflow** on `main`, only after the exact selected SHA is verified and recorded. The workflow's PR lane runs ONLY offline unit tests. An attempted dispatch while disabled produces an explicit failed HOLD job, not a false green live certificate. Scheduled execution is intentionally absent.

## Acceptance rules

The script checks repository, numeric owner/repository IDs, exact workflow ref, event, main branch, approved commit SHA, federation JWT claims and time limits before a provider operation. It obtains a separately scoped 20-minute OCI RPST with an in-memory RSA signing key. It verifies the exact running E2 Micro, plugin configuration `ENABLED`, and plugin runtime status `RUNNING`. It creates exactly ONE fixed short no-write script that rejects root identity and only probes readable `/proc` files, then requires a matching Oracle command ID, exact target VM, terminal `SUCCEEDED`, zero exit code and the exact marker `RETALLY_OCI_SYNTHETIC_CANARY_V1_OK`. No arbitrary command strings, customer data, bucket operations, SSH, DNS, tunnel, VM modification, or service restart are included.

On an ambiguous command creation error or status timeout, **do not rerun** until the original request is reconciled in OCI Audit. The command may have been accepted even if the network response failed. SDK automatic retries are disabled. No synthetic success can satisfy confidential customer or real financial-operation gates.

**Follow-on (not activated here):** after a genuine remote canary succeeds, add a separately approved, source-locked synthetic-only staging installer, host-health acceptance, encrypted recoverability and rollback verification. Never convert the canary into an arbitrary shell command or assume a passing code test proves on-host deployment. Customer authorization and private workbench access remain HOLD.
