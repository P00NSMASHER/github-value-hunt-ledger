# RETALLY — GitHub-hosted Oracle read-only monitor

**Status: LIVE READ-ONLY METADATA PASS; CUSTOMER OPERATIONS HOLD (October 21, 2026).** GitHub-hosted Actions has authenticated to Oracle without PAAM-L044, Cloud Shell, SSH or a public workbench and verified the configured private bucket/VM metadata. The monitor itself cannot create or change OCI resources. Independent IAM denied-operation tests, encrypted off-device recovery, and protected customer-runtime acceptance remain unverified.

## Execution contract

- .github/workflows/retally-oci-readonly.yml runs credential-free offline tests on pull requests. A daily 12:23 UTC schedule and main-branch manual dispatch are present, but live checks are **skipped by default** unless GitHub repository variable RETALLY_OCI_MONITOR_ENABLED is exactly true.
- The approved repository is P00NSMASHER/github-value-hunt-ledger (ID 1376771019, owner ID 22281248), specifically the trusted workflow at refs/heads/main. The job requests GitHub OIDC, exchanges the signed JWT in an Oracle Identity Propagation Trust for a 20-minute Resource Principal Session Token (RPST), and signs calls using an ephemeral RSA key in memory.
- It checks private Standard bucket retally-synthetic-sealed-recovery for NoPublicAccess, versioning/events/replication disabled; and the known VM ID, RUNNING state, VM.Standard.E2.1.Micro shape. Calls only OCI GetBucket and GetInstance. There are **no object lists, reads, writes, uploads, restores, SSH or network changes**. Output is generic, with no OCI OCIDs or secrets.
- A passing monitor is NOT a passing encrypted-restore test or customer-ready release. The pre-existing synthetic orphan tracked in PR #520/#522 remains untouched.

**Duplicate observer resolved:** [PR #523](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/523) was closed unmerged because the narrower [PR #525](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/525) monitor is already integrated. Keep one scheduled Oracle identity; this monitor still cannot inspect objects or establish backup quality.

**OIDC subject compatibility:** GitHub repositories created, renamed or opted in after July 15, 2026 may produce an immutable default subject. The monitor accepts ONLY either `repo:P00NSMASHER/github-value-hunt-ledger:ref:refs/heads/main` or `repo:P00NSMASHER@22281248/github-value-hunt-ledger@1376771019:ref:refs/heads/main`, and checks numeric IDs, workflow, issuer, audience and timestamps independently. Never use a wildcard subject. Oracle trust conditions bind the numeric repo/owner IDs instead of relying on a mutable subject.

## Verified live acceptance — October 21, 2026

[GitHub Actions run #39632003542](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39632003542) was manually dispatched on trusted `main` commit `be112ac82999515b2cd899b770bea4e3c794c4e8`. Job `oracle-readonly` #119332520880 completed all steps including installing the pinned OCI SDK and the actual private GetBucket/GetInstance checks. Its redacted result was `RETALLY OCI HEALTH: PASS (private bucket and expected VM)`; `RETALLY_OCI_MONITOR_ENABLED` was `true`, while the no-provider-call fallback job was skipped. This is **authentic provider metadata acceptance**, not a mocked offline suite.

Previous [run #39621860701](https://github.com/P00NSMASHER/github-value-hunt-ledger/actions/runs/39621860701) had failed with fixed non-secret token-exchange diagnostic `OCI_TOKEN_EXCHANGE_AUTH_HTTP_400_invalid_request`; the verified later run supersedes that narrow error. At the point of evidence review, the executed script Git blob `3df9495a89529e22ffbae4df84977b852e454f70` and workflow blob `7609061e9d304f943a92d5af652fad2b37e29ce8` exactly matched production main. No raw OAuth/JWT/RPST, private object names, source/customer data, or credential material are needed in this proof.

**Not yet verified:** actual effective-deny IAM controls against object bodies, object listings and VM/network mutations; OCI Audit independent review; scheduled-run longevity; private encrypted off-device restore; host disk encryption/access/MFA; customer-authorized workspace deployment; private Business OS database identity or customer source mapping. These remain distinct production-release conditions. Never interpret this positive metadata check as customer launch approval.

## 1. Identity domain and token-exchange trust: configuration/repair reference

For new deployments or trust repair only: an authorized Oracle identity-domain administrator creates a **dedicated non-administrator confidential OAuth application** for this monitor. The real October 21 read-only run succeeded using a configured OAuth client; that successful exchange does not disclose or prove all effective permissions or credential rotation settings. Do not create a duplicate client merely because this template exists. If an administrator needs a separate elevated OAuth application to provision the trust, do not use that app in GitHub. The runtime OAuth client ID/secret must stay in GitHub Actions Secrets, never issues/chat/repository variables. This design avoids OCI user API signing keys but does require an OAuth client secret.

If rebuilding or independently auditing, validate the existing IdentityPropagationTrust against this source-bound template (replace only the OAuth client ID, and verify actual settings in OCI):

~~~json
{
  "name": "retally-github-readonly-monitor",
  "active": true,
  "issuer": "https://token.actions.githubusercontent.com",
  "publicKeyEndpoint": "https://token.actions.githubusercontent.com/.well-known/jwks",
  "type": "JWT",
  "subjectType": "Resource",
  "allowImpersonation": true,
  "impersonatingResource": "ref_github",
  "oauthClients": ["<RETALLY_OAUTH_CLIENT_ID>"],
  "claimValidations": [
    {"name": "repository_id", "value": "1376771019"},
    {"name": "repository_owner_id", "value": "22281248"},
    {"name": "workflow_ref", "value": "P00NSMASHER/github-value-hunt-ledger/.github/workflows/retally-oci-readonly.yml@refs/heads/main"},
    {"name": "ref", "value": "refs/heads/main"},
    {"name": "aud", "value": "https://cloud.oracle.com"}
  ],
  "claimPropagations": ["ext_repository", "ext_workflow_ref", "ext_repository_id"],
  "schemas": ["urn:ietf:params:scim:schemas:oracle:idcs:IdentityPropagationTrust"]
}
~~~

Oracle must validate the GitHub JWT signature against the provider public keys. The Python preflight only reads unverified claims for an extra guard and does not replace Oracle's signature validation.

## 2. OCI IAM policy: owner/admin action

Use the resource compartment and exact OCI identity domain OCID. If bucket and VM are in different compartments, split these statements accordingly. Review the policy in OCI's editor. The policy must not grant object body access, object modifications, VM actions or IAM admin rights.

~~~text
Allow any-user to read buckets in compartment <RESOURCE_COMPARTMENT> where all {
  request.principal.type = 'identityfederateddomainapp',
  request.principal.domain.id = '<IDENTITY_DOMAIN_OCID>',
  request.principal.ext_repository_id = '1376771019',
  request.principal.ext_repository = 'P00NSMASHER/github-value-hunt-ledger',
  request.principal.ext_workflow_ref = 'P00NSMASHER/github-value-hunt-ledger/.github/workflows/retally-oci-readonly.yml@refs/heads/main',
  target.bucket.name = 'retally-synthetic-sealed-recovery'
}

Allow any-user to read instances in compartment <RESOURCE_COMPARTMENT> where all {
  request.principal.type = 'identityfederateddomainapp',
  request.principal.domain.id = '<IDENTITY_DOMAIN_OCID>',
  request.principal.ext_repository_id = '1376771019',
  request.principal.ext_repository = 'P00NSMASHER/github-value-hunt-ledger',
  request.principal.ext_workflow_ref = 'P00NSMASHER/github-value-hunt-ledger/.github/workflows/retally-oci-readonly.yml@refs/heads/main'
}
~~~

Note: read instances permits reading instance metadata for other instances in the compartment; a dedicated compartment reduces exposure. Confirm actual IAM policy behavior independently. Run negative controls proving this identity cannot read object bodies, list objects, upload/delete, change VMs or networking. Review OCI Audit records. The current monitor already produced a positive live pass with the activation variable true; that result does **not** prove these negative controls. Preserve the customer-data hold and do not broaden OCI grants. For any new/renewed trust or re-activation, complete these negative controls first.

## 3. GitHub repository configuration: owner action

For initial setup or controlled credential rotation, use https://github.com/P00NSMASHER/github-value-hunt-ledger/settings/secrets/actions to verify the required configuration. Never print secret values or overwrite a working credential speculatively:

**Repository Secrets:** RETALLY_OCI_CLIENT_ID (dedicated client ID), RETALLY_OCI_CLIENT_SECRET (dedicated non-admin client secret).

**Repository Variables:** RETALLY_OCI_DOMAIN_URL (identity domain HTTPS origin such as https://idcs-xxxx.identity.oraclecloud.com, no path); RETALLY_OCI_NAMESPACE (existing Object Storage namespace); RETALLY_OCI_COMPARTMENT_OCID (bucket compartment OCID); RETALLY_OCI_VM_COMPARTMENT_OCID (dedicated compartment containing the VM); RETALLY_OCI_VM_OCID (specific existing VM OCID).

**Activation variable:** RETALLY_OCI_MONITOR_ENABLED was `true` in the October 21 live successful workflow. That proves the actual read-only check executed, not that all negative IAM controls were independently audited. The guard still skips provider calls when absent/false. For a fresh setup, credential replacement or re-enablement, leave this variable false until trust/effective permissions and denied-operation tests are verified; never silently broaden an already-enabled monitor.

No OCI credentials may be entered in GitHub code, PR comments or chat.

## 4. First execution, follow-up and boundary

**The first positive live run has passed**; to recheck, use **Actions > RETALLY Oracle Read-Only Health > Run workflow**, selecting main. Both the offline test job and OCI read-only job must pass. Independently cross-check OCI Audit records against the intended identity/resource scope and review denied operation controls. Observe a subsequent scheduled run; GitHub schedules are best effort and can be delayed. A skipped live job is NOT a health pass. External alerts are not implemented; job failures remain visible in GitHub Actions.

Failures leave customer release on HOLD. The verified remote-encrypted recovery rehearsal still belongs to separately governed PR #520 and stricter object-key gate #522; this workflow does not and must not execute those writes. No new paid resources, real-customer uploads or production release are authorized here.

Sources: [OCI RPST trust documentation](https://docs.oracle.com/en-us/iaas/Content/Identity/api-getstarted/token_exchange_grant_type_workload_id-federation.htm), [Oracle RPST claim policy examples](https://blogs.oracle.com/cloud-infrastructure/wif-with-ephemeral-rpst), [GitHub OIDC discovery](https://token.actions.githubusercontent.com/.well-known/openid-configuration), [OCI SDK](https://docs.oracle.com/en-us/iaas/tools/python/latest/index.html).
