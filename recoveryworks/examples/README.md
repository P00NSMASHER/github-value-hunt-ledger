# RecoveryWorks executable examples

`raw_scan_all_six.json` is synthetic and contains no customer data. It exercises
all six initial RecoveryWorks branches through the real deterministic engines.

Run it from the repository root:

```bash
python -m recoveryworks.cli raw-scan \
  recoveryworks/examples/raw_scan_all_six.json \
  --output /tmp/recoveryworks-result.json \
  --ledger-output /tmp/recoveryworks-ledger.json
```

Inspect the durable ledger:

```bash
python -m recoveryworks.cli summary /tmp/recoveryworks-ledger.json
```

Render one case or a client-isolated portfolio:

```bash
python -m recoveryworks.cli packet /tmp/recoveryworks-ledger.json FINDING_ID
python -m recoveryworks.cli portfolio /tmp/recoveryworks-ledger.json example-client
```

The operator lifecycle is local-state-only:

```bash
python -m recoveryworks.cli approve /tmp/recoveryworks-ledger.json FINDING_ID \
  --reviewer reviewer-1 --note "Verified source and arithmetic"

python -m recoveryworks.cli authorize /tmp/recoveryworks-ledger.json FINDING_ID \
  --authorization-id customer-auth-1

# This records an action performed elsewhere; it does not submit anything.
python -m recoveryworks.cli mark-claimed /tmp/recoveryworks-ledger.json FINDING_ID

# Record externally verified recovered cash.
python -m recoveryworks.cli recover /tmp/recoveryworks-ledger.json FINDING_ID \
  --recovered-cents 1000 --fee-cents 200
```

For authenticated ledger snapshots, set `RECOVERYWORKS_LEDGER_HMAC_KEY` in the
process environment. To refuse unsigned ledgers entirely, also set
`RECOVERYWORKS_REQUIRE_SIGNED_LEDGER=1`. Never commit the HMAC key.
