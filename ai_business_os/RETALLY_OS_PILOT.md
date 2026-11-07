# RETALLY private operating desk

This is an opt-in, synthetic operating environment. It connects the actual RETALLY intake handlers, a private integration ledger, a pinned GopherCRM service and the existing freight recovery ledger. The private desk includes the CaptureBrief release hold, verified Postmill draft receipts and the Prime worker rehearsal result. The live customer register, production D1 and public forms have independent activation boundaries.

## Run the pilot on Linux

Use a RETALLY checkout with Node 22.16+ (node:sqlite), Python 3.11+, Go 1.25+, Git and libseccomp. Use an owner-only local directory for fixture state. The following commands use a new workspace. The first downloads pinned GopherCRM and CaptureBrief code, builds the Go binaries, prepares Python and runs acceptance. It reads a public Treasury PDF through CaptureBrief's restricted source reader. RETALLY_SOURCE_PDF can refer to an offline copy with the verified SHA-256. The second starts the operator desk, asks for an access code and prints its loopback address.

```sh
bash ai_business_os/run_retally_pilot.sh "$HOME/retally-private-pilot"
python3 -m ai_business_os.retally_console --workspace "$HOME/retally-private-pilot"
```

The fresh workspace is deliberate. Use an unused path to repeat acceptance. Use the second command on the original workspace to reopen the existing desk. Enter the access code on the local sign-in page. The runtime binds only to 127.0.0.1 in standalone mode. Stopping it rotates its ephemeral session secret on the next start. The enabled desk can also be mounted into the existing authenticated private command center with AIBOS_RETALLY_SYNTHETIC_DESK pointing at the desk database. Leave that variable unset for existing deployments.

For prebuilt dependencies, run the same suite directly:

```sh
python3 -m ai_business_os.retally_pilot --workspace /private/new-pilot \
  --gopher /private/bin/gopher --admin /private/bin/create-admin \
  --capturebrief /private/pinned-capturebrief --source-pdf /private/original-Treasury.pdf
python3 -m unittest discover -s ai_business_os -p 'test_*.py'
```

## What each system actually does

| Surface | Verified operation | Remaining boundary |
|---|---|---|
| Cloudflare intake | Both existing handlers ran against local D1/workerd with interception of Turnstile and mail. Simultaneous identical requests returned one reference. Actual status GET on the public freight site returned 200 and online during build. | The feed SQL is a separate opt-in pilot file. The bridge explicitly requires a synthetic source identity and synthetic email domain. Connecting production D1 or historical records requires a separately tested private reader and retention/activation decision. |
| GopherCRM | Pinned service, SQLite, real restricted sales identity, exact-ID API readback, task creation and React UI. Lost POST responses, wrong owner, offline catch-up and clean restore exercised. | Dedicated pilot uses a host-local transport and reserved unique namespaces. Deployment needs a persistent private host, scoped control of credentials and dependency remediation. See GOPHER_PILOT.md. |
| Freight | The RecoveryWorks ledger replays a signed receipt and reversal. The fee calculator consumes the canonical freight default. Case updates, evidence hashes and stage changes persist. | All authorizations, money and customer identities in this walkthrough are synthetic. External claim submission and positive cash collection are outside this pilot. |
| CaptureBrief | The group inquiry maps to a separate engagement for the same fictional account. A case-bound private preview identifies conflicting deadlines in an official source. Upstream quality checks block the customer deliverable. A separate golden fixture produces the eight-file bundle. | Free supervised one-assumption review. The source hold stays visible. Live enrollment, delivery and paid status require their own evidence. See CAPTUREBRIEF_PILOT.md. |
| Postmill | Actual pinned backend, PostgreSQL and Redis. Three disabled-channel drafts survived a restart. The desk imports the sanitized, version-bound receipt from that rehearsal; its database contains no channel credentials. Local edits revoke the previous approval. | This is saved draft readback; live provider publication and analytics require an authorized account, reviewed dependencies and supported host. Repeat the real upstream proof using POSTMILL_PILOT.md. |
| Prime Agent | Actual isolated Prime RPC executed a CPU coding job with Qwen2.5-Coder-0.5B. The independent verifier rejected the first proposal and accepted the second after a SQLite set-subtraction hint. A separate fixture-model rehearsal exercised termination, lease generation change and rejection of stale output. | The local-model exercise was bounded to one synthetic engineering defect. Production authority and customer access stay outside the worker. Reproduce using prime_pilot/cpu/README.md and prime_pilot/README.md. |

## Full stack acceptance

After preparing the pinned upstream dependencies, run `bash ai_business_os/verify_retally_stack.sh /private/new-stack-run`. Set RETALLY_PRIME_GGUF to the pinned Qwen weights to exercise both the actual CPU model and the independent restart fixture. VERIFY_RETALLY_STACK.md lists the complete environment settings. The combined command imports Postmill draft receipts from its own invocation, exercises the CRM and both RETALLY services, and writes a hash manifest for independent readback.

## D1 query cost

Local workerd measured 8 rows read and 9 written for a single successful inquiry without the optional feed. With the feed it measured 9 rows read and 12 written. An idempotent replay still used 1 read and 0 writes. Three catch-up rows cost 6 reads and 0 D1 writes. The transcript, indexed query plan and repeatable benchmark are in d1_pilot/README.md. These local units do not establish actual account billing.

## Backups, rollback and money

The run writes acceptance.json and a clean restore under the chosen workspace. It uses SQLite online backups, restores each database, rotates and revokes the restored CRM credential, verifies stable IDs and reopens the same recovery ledger head. Keep each workspace private, including backup copies. Stop the loopback process to end the pilot. To disable an optional mount, unset AIBOS_RETALLY_SYNTHETIC_DESK and restart the command center. A source feed SQL file by itself makes no change to live intake.

The freight fixture flags $1,000, verifies $400 recovered at the default 30% rate, and reverses $100. It reconciles $300 net recovered, $90 assessed and $0 in fee cash collected. The PR and test suite do not establish a real customer, a paid engagement, a public post or a receipt of money.
