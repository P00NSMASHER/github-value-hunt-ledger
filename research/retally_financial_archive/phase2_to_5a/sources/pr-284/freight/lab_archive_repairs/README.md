# Original Unified Laboratory: portable repair source

This folder preserves a **tested offline repair** for the archived synthetic Unified Five-Step Laboratory. It is not runtime production RecoveryOS code and does not imply a bank/carrier-corroborated financial proof.

## Baseline and exact reproducibility

Original Library archive: \`RecoveryOS_Unified_Five_Step_Laboratory.zip\`
Original SHA-256:
\`2dcfd16296454689a391fb76ac57e4a9282091c25d85134334b3c7eeeeafc93b\`

Source inside archive:
\`RecoveryOS_Unified_Development_Lab/unified/staging.py\`

Files in this directory:

- \`STAGING_ENTRYPOINT.patch\` updates the original verifier and strict contract-consent guard.
- \`unified/semantic_verify.py\` independently derives financial fields, source binding digest, consent state, and expected journal postings from archived event history.
- \`tests/test_semantic_repair.py\` contains six new baseline/attack-regression tests.

**From a clean extraction** with \`RecoveryOS_Unified_Development_Lab\` as the current directory:

\`\`\`sh
cp /path/to/repo/freight/lab_archive_repairs/unified/semantic_verify.py unified/semantic_verify.py
cp /path/to/repo/freight/lab_archive_repairs/tests/test_semantic_repair.py tests/test_semantic_repair.py
patch -p1 -i /path/to/repo/freight/lab_archive_repairs/STAGING_ENTRYPOINT.patch
python -W error::ResourceWarning -m unittest -q tests.test_unified tests.test_semantic_repair
\`\`\`

The source and test GitHub blobs were compared byte-for-byte with locally tested files via Git blob SHA:

- \`unified/semantic_verify.py\` blob SHA-1: \`c39988a64ab01d40beab8c8057cec62812c75cd8\`
- \`tests/test_semantic_repair.py\` blob SHA-1: \`86f45316a1a3e520997f3e1968362ddb4d5d1d03\`

A fresh extraction of the original archived ZIP accepted the full repair patch without rejected hunks and the patched file contents matched the locally tested versions.

## Actual local verification

- Original archive: seven of seven audit weaknesses reproduced; baseline legacy suite 62/62 passing.
- Patched archive: six new tests plus 62 legacy tests, **68/68 passing**.
- Repeat audit: **five of seven original weaknesses still reproduced**. The two no longer reproduced were (1) combined tampered financial balance/public invoice and (2) phantom simulated cash journal.
- Additional strict boolean consent regression checks were added, although unbound signed historical fee terms remain **unfixed**.

This patch does **not** fix source ownership across tenants, duplicate economic claims, blind truth leakage, authorized historical fee terms, all settlement/reversal semantics, fully authenticated external evidence, partial credit posting, or realistic customer behavior. The original financial ledger model remains too limited to certify money. Its internal binding hash is not an independently controlled trust anchor.

Keep the cumulative 26 historical findings \`OPEN_UNVERIFIED\` until each distinct issue is repaired and independently closed with full evidence. No external donor code or customer data was used. Do not republish the old generated results/manifests as though produced by the patched code.
