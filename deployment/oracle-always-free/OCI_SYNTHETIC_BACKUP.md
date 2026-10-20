# RETALLY Oracle Object Storage — synthetic encrypted recovery acceptance

**Status: code candidate / production release HOLD.** This is not a hosted customer backup service or an authorization to move real financial evidence.

## What is already known from the authenticated OCI Cloud Shell session

- Oracle home region: US East (Ashburn); Always Free `VM.Standard.E2.1.Micro` instance running, with 1 GB RAM and a 50 GB boot volume.
- VM has **zero inbound VCN security-list rules** and **no attached network security groups** after temporary private SSH was detached; the temporary SSH group was subsequently deleted.
- Separate Object Storage bucket `retally-synthetic-sealed-recovery` exists in Standard storage tier, `NoPublicAccess`, with versioning disabled. Object Storage was not enabled by a paid upgrade.
- A previous first cryptographic canary failed *after the upload was accepted* because the helper incorrectly expected all OCI CLI operations to return a `data` property. Subsequent read-only inventory showed **one** object under `synthetic-only/`, no real customer data. This unresolved synthetic object needs precise reconciliation.
- Cloud Shell also temporarily requires access to the public OCI API network; an ephemeral private subnet session was tested, then reset to Public. No Cloudflare public workbench route has been created.

## Purpose and boundaries

`oci_synthetic_backup.py` verifies only the *synthetic* six nonfreight + freight branch fixture by running the real engines, local sealed snapshot code, OCI object upload, remote readback, and new isolated recovery with old credentials invalidated. It rejects all customer data and uses a newly generated synthetic passphrase that is never output or saved. The test object is deleted after successful verification using an ETag-conditional delete; receipts are owner-only. **It does not establish ongoing backup protection, retention or passphrase escrow for real customers.**

The tool never creates an OCI VM, virtual network, bucket, subscription, API key, or customer operation. `--inspect` is read-only and can be used on stock Cloud Shell with no Python crypto dependencies. All synthetic object prefix inventories use `oci os object list --all`; OCI otherwise defaults to the first 100 entries. Some Cloud Shell CLI versions return zero stdout bytes for a successful empty-list response. A blank inventory is **not** accepted as evidence of emptiness: the tool performs a second, full-pagination query for `length(data)` and accepts only an explicit integer zero. Any disagreement, nonnumeric count, error, warning or unsupported shape stops the operation. A partial object inventory must never authorize cleanup, a claim that the prefix is empty, or another upload. OCI commands use `--no-retry`; uploads use `--no-overwrite` and `--verify-checksum`; failed/ambiguous uploads leave private receipts and stop rather than creating duplicate objects. **OCI `put --no-overwrite` can return exit status zero with `{"output":"The object already exists and was not overwritten"}`. That is NOT an upload acknowledgement. The candidate requires a top-level `etag` on PUT, then verifies the exact same ETag by independent HEAD before attempting GET. Empty, nested, or existing-object PUT responses fail closed.**

## Execution on the user's existing authenticated OCI Cloud Shell

Use a **reviewed immutable Git commit**, never a floating branch. The repository code at this SHA must include `recoveryworks` and the optional `cryptography==45.0.7` library before the full exercise. No keys or object names are to be pasted into GitHub, a chat, or logs.

From a clean checkout of the exact accepted staging revision:

```bash
# Read-only first: confirms private bucket settings and enumerates only synthetic objects.
python3 deployment/oracle-always-free/oci_synthetic_backup.py --inspect

# The previously abandoned canary may be cleaned only if exactly ONE object
# matches the prior synthetic-only/<24 hex>.rtbk name, the fixed magic bytes,
# and the bounded small ciphertext size. It uses a fresh ETag conditional delete.
# Only if original independent evidence supplies BOTH the exact prior key
# and original ciphertext SHA-256. Today's remote checksum cannot substitute.
python3 deployment/oracle-always-free/oci_synthetic_backup.py --cleanup-legacy-canary \
  --expected-legacy-object-name 'synthetic-only/PRIOR_VERIFIED_KEY.rtbk' \
  --expected-legacy-ciphertext-sha256 'PRIOR_VERIFIED_64_HEX_SHA256'

# Default exercise refuses any unresolved historical object.
# If the prior canary lacks independently frozen original SHA evidence,
# preserve it (do not delete!) while testing the DIFFERENT synthetic-recovery/
# prefix with strict private quarantine evidence.
# This option requires EXACTLY ONE bounded legacy magic candidate; the orphan
# remains unresolved and cannot be counted as a recovered backup.
python3 deployment/oracle-always-free/oci_synthetic_backup.py --exercise \
  --preserve-legacy-orphan

# When the historical prefix is genuinely EMPTY, omit --preserve-legacy-orphan.
# Run the real simulated seven-branch flow, encrypt, upload, retrieve,
# SHA-256 compare, replay/restore, invalidate all old tokens, reject tampering,
# and delete the exact current test object conditionally.
python3 deployment/oracle-always-free/oci_synthetic_backup.py --exercise
```

For any failed/partial command, **stop**. Inspect OCI audit, the bucket object inventory and the owner-only receipt before continuing; never delete arbitrary bucket objects, erase retry/attempt markers or repeat `--exercise` blindly. If the synthetic test fails *before* remote deletion, the object may already exist. Leave the partial receipt intact until a separately reviewed reconciliation.

A separate `--exercise --preserve-legacy-orphan` option now permits a
**new, isolated** recovery test while leaving the historical orphan completely
untouched. The quarantine procedure checks a single small historical object,
free Standard tier, the precise legacy key format, a bounded HEAD size,
ETag-conditioned downloaded bytes and the expected synthetic magic. It writes
an owner-only `legacy-orphan-quarantine.json` containing the **currently
observed** SHA-256, expressly marking original upload identity as unverified;
it does **not** use that hash to authorize deletion. The new workbench backup
test uses exclusively `synthetic-recovery/`, decrypts only the new fixture,
conditionally deletes only its own exact temporary object and then performs
a second full inventory, frozen-ETag HEAD and bounded remote-ciphertext SHA-256
readback to confirm the original canary remains byte-identical. No prior orphan is ever imported into a workspace
or counted as a valid backup. An unexpected extra object, changed head/ETag,
or existing quarantine receipt stops new uploads. The ordinary `--exercise`
mode still refuses to proceed when the historical prefix is nonempty.

The cleanup command now also requires a **previously frozen, independently
approved original key and ciphertext SHA-256**. If the previous upload did
not retain that evidence, **do not delete the orphan**. Its present filename,
magic header, ETag and newly calculated remote hash are not independent
proof of which original was uploaded. Before downloading, it verifies
remote HEAD content-length and freezes the original ETag; the download uses OCI `--if-match` to prevent a concurrent substitution with a larger or different object. The same bound-and-ETag check applies to the real-engine synthetic recovery exercise. It does not generalize to real records, evidence or arbitrary `.rtbk` archives. Never run bulk delete. Source content for the observed canary is already irrecoverable because the one-time synthetic key was not saved.

## Acceptance criteria and release status

- Real seven branch simulation passes with no external actions and `simulation=true`.
- Only a complete workbench snapshot without plaintext credential files is AES-256-GCM encrypted using scrypt.
- Remote bytes read back from the **actual OCI service** hash-identical to locally authenticated ciphertext.
- Independent filesystem restore of the remote retrieved snapshot passes, including source hashes, journal integrity and revocation of prior role tokens; changed ciphertext is rejected.
- Read-back verified temporary synthetic object is removed using a frozen ETag; remote prefix is empty afterwards.
- Owner-only receipt at `~/.retally-oracle/synthetic-backup-acceptance.json` reports only synthetic facts; separate key custody is explicitly **not** accepted.
- The bucket stays `NoPublicAccess`, Standard tier, versioning disabled; no unexpected events/replication services are activated; use stays below the 20 GB Always Free threshold.
- All CI and genuine independent source approval gates for PRs #493, #500, #502, #508, #516, and this dependent PR remain mandatory before live customer workflows.

**Current known gap:** No live OCI restore acceptance has yet been completed. The previous small synthetic canary remains unverified and must NOT be deleted merely because its current hash is known. No service is installed on the VM and customer release remains HOLD. Owner-only local receipts and unchanged OCI settings do not establish a disaster-recovery SLA.

Resources: [OCI Object Storage free limits](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm), [object put with no-overwrite and checksum](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/os/object/put.html), [ETag-conditional delete](https://docs.oracle.com/en-us/iaas/tools/oci-cli/latest/oci_cli_docs/cmdref/os/object/delete.html).
