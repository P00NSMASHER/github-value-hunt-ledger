# RETALLY Oracle Always Free: private seven-branch synthetic staging

**Status: RELEASE HOLD.** This directory prepares a private Linux staging host for the existing RecoveryWorks application. It does not create a server, publish the workbench, permit real customer data, make purchases, send claims, or certify an independent review. Keep the existing public RETALLY Pages website unchanged.

## Verified service boundaries

- Application code: the reviewed source revision of [PR #493](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/493), plus the optional encrypted snapshot work in [PR #500](https://github.com/P00NSMASHER/github-value-hunt-ledger/pull/500), plus this deployment PR **after independent acceptance**.
- Existing Cloudflare account/zone: `retallyrecovery.com`. A separate Access application **RETALLY seven-branch private workbench — release hold** already protects `workbench.retallyrecovery.com` with zero Allow policies; default deny. Access application ID `690352a7-12e3-4c86-8953-2f005e1de892`.
- Cloudflare Tunnel is **not** created, and there is **no DNS record** for the workbench hostname. Do not create either before accepting the reviewed release and defining named operators.
- Web server: `127.0.0.1:18765` only. `--external-origin https://workbench.retallyrecovery.com` narrowly permits the exact HTTPS browser Host/Origin while preserving the loopback socket, current bearer credentials, and existing source/review gates.
- Cloudflare Tunnel ingress must enforce JWT validation using **Protect with Access** and the exact `audTag` in `cloudflared-config.yml.example`. Do not publish a hostname that bypasses Access.
- All seven branches are exercised only in a `simulation=true` workspace. There is no automatic case submission, outbound messages, payment or claims.
- Cloudflare R2 is currently **not activated** in the connected account. R2 requires its own subscription checkout and usage beyond free allowances may incur costs. **Never enable billable services or upload plaintext customer snapshots without authorization.**

## 1. Oracle Always Free account and instance (operator action)

Use the official [Oracle Cloud Console](https://cloud.oracle.com/); sign in to the user's own OCI tenancy or [register for Free Tier](https://www.oracle.com/cloud/free/). No OCI tenancy/instance is connected to this ChatGPT session; account setup, verification and agreement to terms require the actual account owner.

In the account's **home region** only, create one VM using these exact dimensions, reviewing the final estimate and **Always Free Eligible** labels before clicking Create:

| Setting | Value |
|---|---|
| Name | `retally-private-staging` |
| Shape | `VM.Standard.A1.Flex` (Ampere Arm, Always Free Eligible) |
| OCPU / RAM | **2 OCPU / 12 GB RAM** total across A1 instances |
| Operating system | Ubuntu 24.04 **Arm64/aarch64** |
| Boot volume | **50 GB** (leave total boot+block volumes below Always Free 200 GB) |
| Home region | Your actual OCI home region (never an unverified second region) |
| Add-ons | None; no load balancer, managed DB, paid image, paid support or upgraded plan |
| Networking | Outbound Internet for updates/Tunnel; deny public ingress to ports 18765, 8765 and 80/443 |
| Administration | Use OCI Console/serial console, or temporarily restrict SSH 22 to the authorized operator's specific IP; **never 0.0.0.0/0** |

OCI Always Free resources are subject to capacity availability and reclaim rules. If the selected free shape is unavailable, **stop**; do not change to a paid shape. The free allowance is not a hard billing cap for arbitrary paid resources or external provider charges.

OCI Block Volume boot/storage is AES-256 encrypted at rest with Oracle-managed keys by default. Record the new instance's volume encryption settings, region, compartment, tenancy and reviewer attestation before any real customer record enters the VM. Use separate customer authorization and secure transfer controls.

Sources: [Always Free resources](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [OCI encryption](https://docs.oracle.com/en-us/iaas/Content/Block/Concepts/blockvolumeencryption.htm).

## 2. Stage the reviewed source (no public network route)

On the Ubuntu VM, access the shell through an approved method. Clone the public source with Git; do not paste keys into terminal history.

```sh
git clone https://github.com/P00NSMASHER/github-value-hunt-ledger.git retally-deploy-src
cd retally-deploy-src
git fetch origin --prune
git checkout --detach FULL_INDEPENDENTLY_ACCEPTED_RELEASE_SHA
bash deployment/oracle-always-free/install-staging.sh FULL_INDEPENDENTLY_ACCEPTED_RELEASE_SHA
```

The installer checks the **exact SHA**, clean repository, Arm64 architecture, creates a least-privileged `retally` service user, deploys immutable root-owned source into `/opt/retally/releases/<SHA>`, seeds the complete **synthetic** seven-branch acceptance journey under `/var/lib/retally/synthetic-preview`, and installs a hardened `retally-synthetic.service` unit. The installer **does not enable or start the service**.

SHA equality is a reproducibility check, **not** independent release approval. Never replace a real workspace with this synthetic workspace.

## 3. Activate private access only after acceptance

1. Obtain independent PR #493 review/merge; independently review the dependent encryption and deployment changes. Verify latest combined release gate, no conflicts and exact accepted production SHA.
2. In **Cloudflare Zero Trust > Access applications**, verify the separate workbench application above. Configure named human reviewers, strong SSO/MFA, and an explicit minimum necessary Allow policy; remove any unsafe bypass. Do not broaden the existing inquiry application.
3. Install signed `cloudflared` packages using Cloudflare's [Ubuntu apt instructions](https://developers.cloudflare.com/tunnel/features/locally-managed-tunnels/create-local-tunnel/); do not use an unreviewed curl-to-shell installer.
4. Create a locally managed tunnel with credential files stored root-only under `/etc/cloudflared`. Substitute its real UUID in `cloudflared-config.yml.example`. Verify `cloudflared tunnel ingress validate`. The pre-populated `audTag` is the verified workbench Access audience; it is not a secret.
5. Configure DNS routing to `workbench.retallyrecovery.com` **only after** Access policies and **Protect with Access** JWT enforcement pass negative tests. No direct inbound HTTP/HTTPS port should be open on Oracle's virtual network or host firewall.
6. Start and enable `retally-synthetic.service` after confirming approved operator responsibility. Run `bash deployment/oracle-always-free/check-staging.sh` and verify the Cloudflare Access login. Test denied unauthenticated and unauthorized access from outside.
7. Keep all actual customer files out of synthetic staging. **Live client workspaces are a separate explicit release procedure** after real customer consent, verified independent reviewers, encrypted off-device recovery and data retention terms exist.

A standalone Python program listening on `127.0.0.1` cannot be accessed through public Cloudflare Pages; a secure tunnel and origin check are required. Cloudflare Access identities and local role bearer keys are different controls. Never share all four local reviewer keys with one person and call it independent review.

## 4. Encrypted off-device recovery — still a hold

The optional `recoveryworks.offsite_archive` helper from the dependent PR can produce authenticated AES-256-GCM ciphertext (`.rtbk`) from a locally verified workspace backup. Read [OFFSITE_BACKUP.md](../../recoveryworks/OFFSITE_BACKUP.md). It excludes plaintext role keys, refuses unsupported files, and validates restoration. Do not move a plaintext `.json` snapshot to shared storage.

Only after the account owner explicitly activates and confirms the R2 free allowance, an authorized operator can configure a private R2 bucket and scoped S3 credentials, copy **ciphertext only**, compare remote SHA-256 after round-trip, and independently restore from the remotely retrieved copy to a new workspace. Keep the recovery passphrase with a different authorized custodian. Verify retention, actual storage quota/usage and approval for real financial records.

R2 **free allowance is not a promise of zero bills**. If the owner requires a strict no-billing guarantee, do not activate a pay-as-you-go R2 subscription. Evaluate an independently approved no-cost destination before real customer acceptance. Existing local backup/restore does not prove off-device resilience.

[Cloudflare R2 getting started and subscription](https://developers.cloudflare.com/r2/get-started/) and [pricing](https://developers.cloudflare.com/r2/pricing/).

## Explicit go/no-go matrix

| Gate | Current status |
|---|---|
| GitHub PR #493 independent review and merge | **HOLD** |
| Dependent encrypted archive / Windows ACL review | **HOLD** |
| OCI account and Always Free VM provisioning | **NOT DONE** |
| OCI boot-volume encryption attested for this instance | **NOT DONE** |
| Existing Cloudflare private Access app, default-deny | **DONE** |
| Cloudflare tunnel with origin JWT enforcement | **NOT DONE** |
| Named operator, distinct reviewers and customer authorization | **NOT DONE** |
| R2 encrypted off-device snapshot read-back + independent restore | **NOT DONE** |
| Any real client information in cloud | **NONE** |

This is a release-acceptance checklist, not permission to bypass missing gates or increase spend.
