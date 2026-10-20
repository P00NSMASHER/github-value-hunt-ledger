# RETALLY OCI via GitHub Actions — no laptop, no Cloud Shell

**Status: code candidate, NOT ACTIVE until independently approved, merged, configured and verified against real OCI.** Customer release and encrypted production recovery remain **HOLD**.

This implementation uses OCI's August 2026 GitHub OIDC JWT→RPST federation, **not permanent OCI API signing keys**. Oracle still requires a narrowly authorized confidential OAuth client; its client secret is stored privately in a GitHub Environment. Do not paste credentials into a chat, commit, issue or workflow log.

## What is automated

- On `main`, at **12:19 UTC daily**, GitHub runs the metadata-only observer from a hosted Linux runner. GitHub Actions → **Run workflow** permits additional manual read-only checks. PAAM-L044 can stay off.
- Pull requests run **offline identity/permission tests only** and cannot request OCI tokens.
- A repository Actions variable `RETALLY_OCI_BRIDGE_ENABLED` must be explicitly `true` for the job to contact OCI. Otherwise the workflow reports **NOT CONFIGURED** and does not touch Oracle. Do not interpret the offline green check as live acceptance.
- OCI resources are fixed in source: **us-ashburn-1** and dedicated synthetic-only bucket **retally-synthetic-sealed-recovery**. No arbitrary commands, regions, object names, repositories or write operations.
- The job verifies the private Standard-tier bucket, versioning disabled, events/replication/auto-tiering/lifecycle baselines, and the complete paginated object population (at most 128 entries). It reports *only counts* of the expected historical canary and unfinished recovery-test objects; any unknown name, second orphan or stranded recovery object fails closed.
- **No SSH, VM provisioning, storage reads of bytes, downloads, uploads, deletes, customer records, backup creation or restoration.** The historical synthetic canary remains preserved. A successful check is **not** proof of recoverability, off-device backups, customer acceptance, or zero billing.

## One-time setup from iPhone (authorized account administration)

1. Obtain **independent approval**, all PR checks green and merge the proposed change to protected `main`. Do not approve your own PR as independent evidence.
2. GitHub repo Settings → Environments: create **`retally-oci-readonly`** and restrict deployment branches to protected **`main`**. This environment gets **read-only** access only. A separate reviewer-protected environment is mandatory for any future write/restore pipeline.
3. In Oracle Console → **Identity & Security → Domains**, find the real identity-domain HTTPS origin, typically `https://<domain>.identity.oraclecloud.com`. Confirm this tenancy supports **JWT-to-RPST Workload Identity Federation**. Create a dedicated confidential OAuth application with **no identity-admin roles**, permitted solely for this token exchange; retain its client ID and secret privately. No paid services or upgrades.
4. In OCI configure a dedicated **IdentityPropagationTrust**: `type=jwt`, issuer `https://token.actions.githubusercontent.com`, `subjectType=Resource`, `allowImpersonation=true`, `impersonatingResource=githubactions`; `oauthClients` contains only the exact client from step 3. Set `clientClaimName=aud` and `clientClaimValues=["retally-oci-readonly-v1"]`; require the GitHub issuer's cryptographically verified JWT and the following **exact** claim conditions:
   - `sub = repo:P00NSMASHER/github-value-hunt-ledger:environment:retally-oci-readonly`
   - `workflow_ref = P00NSMASHER/github-value-hunt-ledger/.github/workflows/retally-oracle-readonly.yml@refs/heads/main`
   - `ref = refs/heads/main`
   - `repository_id = 1376771019`
   - `repository_owner_id = 22281248`
   
   **Do not weaken** `sub`, workflow ref, repository ID or audience. OCI currently documents a maximum of five additional claim validations; use the five above and restrict issuer/audience through dedicated trust attributes. The workflow independently verifies `event_name` is `schedule` or `workflow_dispatch`, the environment, repo, dates and audience. For any OCI tenancy/version that cannot enforce these constraints, **stop**; do not enable the workflow.
5. Have an OCI tenancy administrator create a **dedicated, compartment-scoped, bucket-specific IAM policy for the exact RPST workload principal**. Required permissions are only **`BUCKET_READ`** (`read buckets` / `GetBucket`) and **`OBJECT_INSPECT`** (`inspect objects` / `ListObjects`), both restricted by `target.bucket.name='retally-synthetic-sealed-recovery'`. The identity selector (resource principal type `githubactions` and exact trusted identity) must be confirmed against **this tenancy's** federation configuration; a generic unrestricted `any-user` policy is unsafe. **Never grant `read objects`, `manage objects`, put/delete/overwrite, tenancy-wide manage, or compute/network privileges.**
6. In GitHub's `retally-oci-readonly` Environment, add variable `RETALLY_OCI_IDENTITY_DOMAIN_URL` (just HTTPS origin), plus secrets `RETALLY_OCI_OAUTH_CLIENT_ID` and `RETALLY_OCI_OAUTH_CLIENT_SECRET`. In GitHub repo Settings → Secrets and variables → Actions → **Variables**, set `RETALLY_OCI_BRIDGE_ENABLED=true` **only after OCI identity trust, narrow IAM authorization and source review are complete**. Never create user API keys for this workflow.
7. GitHub → Actions → **RETALLY Oracle (read-only, no laptop)** → Run workflow on **main**. Confirm the actual **OCI live synthetic-only metadata observation** job—not merely offline tests—passes. Cross-check the original Oracle audit entries and independently prove that the workload is **denied** object download, upload/delete, service creation and compute/network updates. Confirm at least one real scheduled cycle. Observe GitHub Actions minutes and OCI usage; neither is guaranteed unlimited free.

## Acceptance / authorization gates

- [ ] Independent source approval and merged PR, protected main.
- [ ] OCI identity-domain client and cryptographically verified GitHub workload trust configured with exact claims.
- [ ] Narrow read-only IAM policy verified; object reads, writes and deletes explicitly denied.
- [ ] GitHub Environment locked to main; secrets entered without copying them into chat.
- [ ] Explicitly enabled repository variable and successful **live** authenticated job.
- [ ] Actual scheduled job and Oracle audit independently reconciled; no unexpected charges.
- [ ] Historical orphan remains untouched; no claim of successful encrypted restore or production acceptance.

To disable immediately from your iPhone: set repository variable `RETALLY_OCI_BRIDGE_ENABLED=false` and, if compromised, revoke the OCI confidential application/trust/policy. The GitHub schedule will continue showing **NOT CONFIGURED** without contacting Oracle.

**This is scheduled API observation, not an interactive persistent Oracle Cloud Shell.** Any future encrypted recovery run requires a separately reviewed workflow, distinct short-lived OCI identity, independently confirmed customer-free synthetic data, explicit authorization, and the current PR #520/#522 dependency gates.

Sources: [Oracle JWT-to-RPST federation](https://docs.oracle.com/en-us/iaas/Content/Identity/api-getstarted/token_exchange_grant_type_workload_id-federation.htm) · [OCI Object Storage IAM policy reference](https://docs.oracle.com/en-us/iaas/Content/Identity/Reference/objectstoragepolicyreference.htm) · [GitHub OIDC claims](https://docs.github.com/en/actions/reference/security/oidc).
