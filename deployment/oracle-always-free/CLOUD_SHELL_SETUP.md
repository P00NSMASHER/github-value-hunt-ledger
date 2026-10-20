# Oracle Cloud Shell: Almost-zero-touch Always Free RETALLY VM

**Status: staging preparation; not production acceptance.** This script uses your authenticated **Oracle Cloud Shell** session to create only one Always Free-sized virtual machine and a locked-down outbound-only network. It does not install or publish RETALLY or modify Cloudflare.

## One-time interaction needed

1. Sign in yourself to [Oracle Cloud Console](https://cloud.oracle.com/) and click the **Cloud Shell** terminal icon. No credentials or 2FA codes belong in ChatGPT.
2. Download this reviewed script from a **full commit SHA** (not an unpinned branch name):

   ```sh
   curl -fsSL https://raw.githubusercontent.com/P00NSMASHER/github-value-hunt-ledger/FULL_REVIEWED_COMMIT_SHA/deployment/oracle-always-free/provision-cloud-shell.py -o "$HOME/retally-oci-free.py"
   python3 "$HOME/retally-oci-free.py"
   ```

   The first execution is **read-only** against OCI. It discovers the tenancy home region, current Arm A1 usage, allocated boot/block storage, VCN usage, and official Ubuntu Arm64 image. If any data is missing or the Always Free limit would be exceeded, it stops.
3. **Only after** confirming OCI shows an Always Free account/resource and no chargeable selections, run:

   ```sh
   python3 "$HOME/retally-oci-free.py" --apply
   ```

   The script requires the exact phrase `CREATE RETALLY ALWAYS FREE` to create resources. It refuses non-interactive execution, paid shape fallback, duplicate resources, overlapping private networks, other regions, unsupported image, and insufficient capacity.

## What gets created

- One `VM.Standard.A1.Flex` with **2 OCPUs / 12 GB RAM**, in the **OCI tenancy home region**.
- Official **Ubuntu 24.04 Arm64**, one 50-GB boot volume; no marketplace or paid images.
- One VCN, one public subnet with a public outbound address, one internet gateway, with **zero allowed incoming network ports**. Default SSH ingress is removed and read back **before** a VM or subnet is created. Inbound traffic to RETALLY ports 18765/8765/80/443 remains denied.
- A local SSH keypair in Cloud Shell at `~/.retally-oracle`; private key remains in Cloud Shell with owner-only permissions. Do not copy or paste the private key into chat.
- An operator-only local receipt `~/.retally-oracle/always-free-staging-receipt.json` recording OCI IDs. If cloud provisioning partially fails, the tool retains a separate partial receipt and refuses an unsafe retry.

## Important limitations

- This is a **free-resource configuration**, not a guaranteed zero-dollar billing cap for an account with other billable resources or a changed plan. Oracle capacity can be unavailable and inactive A1 instances may be reclaimed. Do not select an alternate paid shape.
- **No workbench runs, no Cloudflare Tunnel, no access bypass and no customer data are installed.** This is intentional until PR #493, PR #500, PR #502 and this script obtain their required independent approvals.
- Because all inbound rules are denied, direct SSH to the public address will not work. Later administration requires an approved secure Oracle Bastion/console method or a narrowly approved SSH rule. Do not open `0.0.0.0/0` on port 22.
- Oracle Cloud Shell is not controlled by ChatGPT in this conversation. It is the only place where the actual tenancy can be changed after you securely sign in.
- Do not send API keys, tenancy passwords, passwords, Cloud Shell configuration files or SSH private keys here.

Official documentation: [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [Cloud Shell](https://docs.oracle.com/en-us/iaas/Content/API/Concepts/cloudshellintro.htm), and [OCI CLI instance launch](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/compute/instance/launch.html).
