# RETALLY — GitHub-hosted Oracle read-only monitor

**Status: candidate / live OCI access HOLD.** GitHub-hosted Actions runs without PAAM-L044, Cloud Shell, SSH, or a public workbench. It only checks existing Oracle Always Free resources and cannot create/change anything in OCI.

## Execution contract

- .github/workflows/retally-oci-readonly.yml runs credential-free offline tests on pull requests. A daily 12:23 UTC schedule and main-branch manual dispatch are present, but live checks are **skipped by default** unless GitHub repository variable RETALLY_OCI_MONITOR_ENABLED is exactly true.
- The approved repository is P00NSMASHER/github-value-hunt-ledger (ID 1376771019, owner ID 22281248), specifically the trusted workflow at refs/heads/main. The job requests GitHub OIDC, exchanges the signed JWT in an Oracle Identity Propagation Trust for a 20-minute Resource Principal Session Token (RPST), and signs calls using an ephemeral RSA key in memory.
- It checks private Standard bucket retally-synthetic-sealed-recovery for NoPublicAccess, versioning/events/replication disabled; and the known VM ID, RUNNING state, VM.Standard.E2.1.Micro shape. Calls only OCI GetBucket and GetInstance. There are **no object lists, reads, writes, uploads, restores, SSH or network changes**. Output is generic, with no OCI OCIDs or secrets.
- A passing monitor is NOT a passing encrypted-restore test or customer-ready release. The pre-existing synthetic orphan tracked in PR #520/#522 remains untouched.

## 1. Identity domain and token-exchange trust: owner action

Using an Oracle identity-domain administrator account, create a **dedicated non-administrator confidential OAuth application** for this monitor. If the administrator needs a separate OAuth application to provision the trust, do not use that elevated app in GitHub. The runtime OAuth client has a client ID and secret which stay in GitHub Actions Secrets, not in issues/chat/repository variables. **This design avoids OCI user API signing keys, but does require an OAuth client secret.**

An authorized identity-domain admin provisions the IdentityPropagationTrust using this template (replace only the OAuth client ID; validate the payload in OCI):

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

Note: read instances permits reading instance metadata for other instances in the compartment; a dedicated compartment reduces exposure. Confirm actual IAM policy behavior independently. Run negative controls proving this identity cannot read object bodies, list objects, upload/delete, change VMs or networking. Review OCI Audit records and do not enable until controls pass.

## 3. GitHub repository configuration: owner action

After independent PR approval and merging, visit https://github.com/P00NSMASHER/github-value-hunt-ledger/settings/secrets/actions and add:

**Repository Secrets:** RETALLY_OCI_CLIENT_ID (dedicated client ID), RETALLY_OCI_CLIENT_SECRET (dedicated non-admin client secret).

**Repository Variables:** RETALLY_OCI_DOMAIN_URL (identity domain HTTPS origin such as https://idcs-xxxx.identity.oraclecloud.com, no path); RETALLY_OCI_NAMESPACE (existing Object Storage namespace); RETALLY_OCI_COMPARTMENT_OCID (existing compartment OCID); RETALLY_OCI_VM_OCID (specific existing VM OCID).

**Activation variable:** RETALLY_OCI_MONITOR_ENABLED must remain absent/false until identity trust, effective permission review and negative controls are independently accepted. Only then set RETALLY_OCI_MONITOR_ENABLED=true.

No OCI credentials may be entered in GitHub code, PR comments or chat.

## 4. First execution, follow-up and boundary

Use **Actions > RETALLY Oracle Read-Only Health > Run workflow**, selecting main. Both the offline test job and the OCI read-only job must pass. Independently cross-check OCI Audit details against the intended identity and resource scope. Observe at least one scheduled run; GitHub schedules are best effort and sometimes delayed. A skipped live job is NOT a health pass. External alerts are not implemented; job failures remain visible in GitHub Actions.

Failures leave customer release on HOLD. The verified remote-encrypted recovery rehearsal still belongs to separately governed PR #520 and stricter object-key gate #522; this workflow does not and must not execute those writes. No new paid resources, real-customer uploads or production release are authorized here.

Sources: [OCI RPST trust documentation](https://docs.oracle.com/en-us/iaas/Content/Identity/api-getstarted/token_exchange_grant_type_workload_id-federation.htm), [Oracle RPST claim policy examples](https://blogs.oracle.com/cloud-infrastructure/wif-with-ephemeral-rpst), [GitHub OIDC discovery](https://token.actions.githubusercontent.com/.well-known/openid-configuration), [OCI SDK](https://docs.oracle.com/en-us/iaas/tools/python/latest/index.html).
