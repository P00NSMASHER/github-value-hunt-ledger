# Oracle Always Free E2 Micro fallback for RETALLY

**Release decision: HOLD.** Use only synthetic data. The seven-branch Python workbench has not passed genuine independent PR approval or real-customer onboarding evidence. No new services, public routes, billable options, off-device backups or customers are authorized by this workflow.

## Why this fallback exists

In the connected `retally` OCI tenancy, home region `us-ashburn-1`, every A1 AD returned `OutOfHostCapacity`. The original guarded launch left an outbound-enabled but **zero-ingress** VCN/subnet in the root compartment and an owner-only receipt:

`~/.retally-oracle/partial-setup-receipt.json`

The actual OCI E2 Micro shape is offered in Ashburn **AD-1 only**; three official Ubuntu 24.04 shape-compatible images were listed. Oracle's Always Free allowance includes up to **two** `VM.Standard.E2.1.Micro` x86-64 instances, 1 GiB RAM each, using the home-region combined boot/block volume allowance. Unlike the A1 shape, Micro has only **one eighth of an OCPU baseline**; under-provisioning, latency and reclaim risks remain real.

See [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm). A free shape is not a guarantee of available capacity or a billing cap for other OCI resources.

## CI acceptance before attempting a VM

The `oracle-micro-memory-rehearsal` job runs the *actual seven-branch synthetic journey*, local backup/restore, health checks and loopback HTTP negative tests in a Docker container constrained to **768 MiB RAM**, with no swap, no network, a 1/8-CPU quota (the fixed Micro baseline), a read-only repository and an unprivileged UID. A passing job indicates the fixture workload fits; it does **not** simulate full production customer datasets or the Micro's 1/8 baseline OCPU. Do not represent this as independently adjudicated customer proof.

An initial rehearsal at 0.5 CPU reported **seven passing synthetic journeys, restore, local health and HTTP controls, 31.3 MiB peak child RSS and 8.2 seconds elapsed**. The current CI additionally constrains the workload to **0.125 CPU**; verify its separate results at the exact PR head. Later sustained host acceptance and security review are required.

## A. Reinspect the existing partial network (read-only)

Use **only** Oracle Cloud Shell while authenticated to the correct OCI tenancy. Never put OCI credentials, SSH private keys, customer files or volume secrets in ChatGPT or GitHub.

Download **both** files from the exact reviewed GitHub commit into the **same** Cloud Shell directory; verify the GitHub SHA and the published SHA-256 checksums before running:

```sh
mkdir -p "$HOME/retally-micro-stage"
cd "$HOME/retally-micro-stage"
# Use the exact independently reviewed full Git SHA, not a floating branch.
curl -fsSL "https://raw.githubusercontent.com/P00NSMASHER/github-value-hunt-ledger/REVIEWED_FULL_SHA/deployment/oracle-always-free/provision-cloud-shell.py" -o provision-cloud-shell.py
curl -fsSL "https://raw.githubusercontent.com/P00NSMASHER/github-value-hunt-ledger/REVIEWED_FULL_SHA/deployment/oracle-always-free/provision-micro-cloud-shell.py" -o provision-micro-cloud-shell.py
# Confirm checksums separately through a trusted release receipt.
python3 provision-micro-cloud-shell.py
```

The default action performs only GET/list operations. It:
- Reads the existing original partial receipt and checks the owner-only RSA SSH key.
- Verifies exact original VCN/subnet/security-list/gateway/route identities.
- Enforces zero inbound network rules and checks free storage.
- Searches *every accessible compartment* for existing Micro and RETALLY instances, rejecting duplicates and full Always Free allowances.
- Finds the **one** E2 Micro availability domain and a compatible official Ubuntu 24.04 image.

If any check fails, do **not** delete the partial receipt or run the old A1 `--apply` command.

## B. Create exactly one micro (requires explicit live authorization)

Only after successful read-only inspection and confirmation that the exact request is Always Free Eligible in this account:

```sh
python3 provision-micro-cloud-shell.py --create
```

The script prints the plan and requires the exact phrase `CREATE ONE RETALLY FREE MICRO`. It then rechecks all OCI resources, reuses **only** the existing original subnet, and issues one `oci compute instance launch` for:
- Shape `VM.Standard.E2.1.Micro` (**fixed 1 GiB RAM**), no flex configuration.
- Official Ubuntu 24.04 image for **AMD64/x86-64**, home-region eligible AD.
- Exactly **50 GB** boot volume.
- Original Cloud Shell **public** RSA SSH key only.
- A public IPv4 for **outbound networking**, but OCI Security List ingress remains **DENY ALL**, including ports 22, 80, 443, 8765 and 18765.

An OCI error, timeout, wrong shape, unexpected state, insufficient free inventory or disagreement with the receipt **stops without paid fallbacks**. No automatic retry is performed because instance state may be uncertain. On success, the tool writes a new owner-only final receipt and archives the original partial evidence.

**Important:** the zero-ingress network means direct SSH will not work. Use an approved Oracle Console/Bastion path for later synthetic installation, never a broad 0.0.0.0/0 SSH rule.

## C. Install a synthetic-only workbench (release hold remains)

After a VM is actually running, obtain independent review of PRs #493, #500, #502, #508 and this PR. Install the accepted exact repository commit through the existing reviewed installer with the Micro-specific flag:

```sh
RETALLY_MICRO_HOST=1 bash deployment/oracle-always-free/install-staging.sh FULL_REVIEWED_RELEASE_SHA
```

The installer must verify **x86-64 hardware and OCI v2 instance metadata shape `VM.Standard.E2.1.Micro`** before any package installation. It stages only a synthetic workspace, runs its seven-branch acceptance, installs systemd with a Micro-specific `MemoryHigh=640M`/`MemoryMax=768M` drop-in, and leaves the private workbench service **stopped and disabled**. A1 installation remains separate and works without the Micro flag.

The separate **read-only on-host checker also requires the Micro flag**, but only after an operator has explicitly approved and started a synthetic service:

```sh
RETALLY_MICRO_HOST=1 bash deployment/oracle-always-free/check-staging.sh
```

The checker independently queries the current OCI v2 instance identity and exact E2 Micro shape before testing the loopback-only listener, HTTP authorization failures and isolated workspace health. It does **not** change OCI networking, start or enable a service, create external access, handle customer data or certify production.

Later, verify host encryption, operator authorization, encrypted independently retrieved off-device backups, data-retention and customer scope; establish protected Cloudflare Access and origin-JWT validation *before* any hostname routing. The existing public RETALLY website is unaffected. **No genuine customer data is permitted under the current release hold.**


## D. Read-only attestation of an already-running E2 Micro

**Use this instead of provisioning again if the final instance receipt already
exists.** From the authenticated owner Cloud Shell, download the exact reviewed
commit's provision-cloud-shell.py and check-existing-micro.py side by side.
Check their published SHA-256 digests locally before executing anything.
Run only:

    python3 check-existing-micro.py

The script refuses partial/stale/nonprivate receipts, verifies the *actual*
OCI tenancy home region, running fixed Micro shape, official Ubuntu 24.04 image,
exact 50-GiB boot volume and attachment, original VCN/subnet/route identities,
and **zero default VCN security-list ingress** plus either **zero attached NSGs**
or one explicitly owner-receipted, independently verified **private-only**
management NSG. The optional owner-only
`~/.retally-oracle/temporary-private-ssh.json` must identify the exact VNIC,
NSG, and rule. The read-only audit queries every live NSG rule and only
accepts **one TCP/22 rule from 10.76.1.0/24**, with no public or additional
rules. Unknown fields, receipt drift, unlisted rules or any public ingress fail
closed. Private-only SSH is **not zero total ingress**, is not a customer-facing
route, and does not grant commercial deployment approval.

This is an **existing-instance read-only audit**: only OCI GET and LIST
operations, no resource creation, firewall change, SSH connection, tunneling,
billing action, customer data, or new credential. The result intentionally
omits provider OCIDs, IP addresses and secrets. The safe report always marks
guest firewall, private-service installation, off-device restore, account
zero charges, independent review, and commercial production readiness as
unverified/false. No CI mock run may be reported as a live OCI acceptance.
Review every source commit, exact file checksum and live OCI response again
before considering an operator-only synthetic installation.

The service installer and check-staging.sh continue to require explicit
RETALLY_MICRO_HOST=1 for x86-64 E2 Micro, and the verified OCI v2 metadata
shape before any staging installation or health acceptance. Neither script
starts/enables the service, creates a Cloudflare Allow policy/DNS/tunnel,
installs customer originals, or authorizes public access. The customer
production launch decision remains **HOLD**.
