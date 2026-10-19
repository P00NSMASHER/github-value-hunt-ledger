# Encrypted off-device backup — controlled pilot workflow

This is an **optional encryption and isolated restore helper**, not an uploader or production certification. It encrypts an existing complete RecoveryWorks snapshot. It never sends customer records, initiates claims, moves money, or chooses a cloud provider. A snapshot can contain confidential financial evidence even when it excludes plaintext role keys; never transfer the unencrypted JSON file to cloud storage.

## Prepare

1. Have the actual workstation owner authorize client-data processing and confirm full-disk protection with an administrator-issued status receipt. Do not assume that a domain login, TPM, Secure Boot, or cloud sync establishes either.
2. Configure a client-owned, access-controlled storage destination with an agreed retention/deletion schedule, immutable or versioned retention policy where appropriate, and a second authorized custodian for recovery credentials. Do not use an employer's unrelated corporate OneDrive account or a public code repository.
3. Obtain a fresh workbench snapshot from the **operator** role, after all local health checks pass. The snapshot includes original and normalized sources and the journal. It excludes plaintext `credentials.json` but remains highly sensitive.
4. Install the optional cryptographic package on the approved private host from a reviewed package source: `python -m pip install cryptography==45.0.7` (the base workbench itself remains standard-library-only).

## Encrypt and verify locally

Run from the repository root using a **new output filename**. The commands prompt for a 20+-character recovery passphrase without placing it in arguments, environment variables, shell history, output or logs.

```shell
python -m recoveryworks.offsite_archive seal --snapshot /private/client/backups/HASH.json --archive /private/staging/retally-client-20261019.rtbk
python -m recoveryworks.offsite_archive verify --archive /private/staging/retally-client-20261019.rtbk
```

The format uses scrypt (N=65536, r=8, p=1) and AES-256-GCM with a fresh salt and nonce; header and compressed snapshot are authenticated. It enforces a 64 MiB plaintext snapshot limit. The verifier decrypts in memory and independently runs `Workspace.restore_snapshot`, checking source hashes, journal replay, and revocation of all saved role keys. Wrong passwords, changed bytes and invalid snapshot paths fail closed.

## Off-device acceptance (not automatic)

Transfer **only** the `.rtbk` ciphertext to the independently approved off-device location. Compare SHA-256 of the destination against the locally returned `sealed_sha256`. Verify cloud upload acknowledgment or physical disk custody separately: a local file in a sync folder does not prove off-device persistence.

From a different controlled machine, retrieve the ciphertext using the actual provider, verify again, then restore it into a **new** private directory:

```shell
python -m recoveryworks.offsite_archive restore --archive /approved/remote-copy.rtbk --destination /private/isolated-restored-client
```

The original credentials remain disabled after restore. Rotate all roles locally before access. Maintain separate documented recovery-key custody: losing the passphrase makes the encrypted backup unrecoverable. The application **does not** manage or escrow passphrases. Do not save the passphrase in the same folder, GitHub, public chats, or next to the encrypted archive.

Record a private acceptance receipt with: approved owner and host, encryption state, snapshot/journal digest, destination and access ownership, off-device checksum and readback, independent restore result, key custodian, RPO/RTO, retention/deletion plan and a second reviewer. **No green application health check alone satisfies this receipt.**

## Deliberate limitations

The encryption helper is not a hosted backup service, cloud synchronizer, identity provider, external bank attestor, legal authorization mechanism or proof of disk encryption. It does not establish an approved off-device destination or key escrow. Windows file ACL failures, unavailable administratively verified encryption, or an unapproved cloud account are release blockers; do not work around enterprise security controls.