# Private Postmill draft pilot

The synthetic Instagram account has no platform token or profile. A real local Postmill v1.4.0 backend accepted three private freight drafts. PostgreSQL held three rows in DRAFT state after one copy revision. No publishing credential, paid service, live user session or connected Instagram account was present. The backend, database and Redis shut down at the end of acceptance.

## Checked revisions and dependencies

- Upstream source and default-branch HEAD matched `b59d7ca3656836a8a8c8144dc3cde6a93070d083` on 7 November 2026. The release version file read v1.4.0. The lockfile SHA-256 was `df9f545b8deeb1809985a1c2003652f133517067ee33dfd24ba4d7a674b66639`. [Pinned public API](https://github.com/postmill-ai/postmill-app/blob/b59d7ca3656836a8a8c8144dc3cde6a93070d083/docs/developer-docs/public-api.md)
- Build runtime was Node 24.22.1 with pinned pnpm 10.34.4. `corepack pnpm audit --prod --json` returned 4 high, 72 moderate, 14 low and 0 critical. The distinct high advisories were GHSA-mrhx-c7xc-m3w5 (zod), GHSA-xcx6-jx8p-x3h5 (@azure/msal-node) and GHSA-x8rm-f576-gq67 (graphql-scalars). This checkpoint is a private synthetic pilot. A deployed release requires advisory review against its own dependency tree.
- PostgreSQL 17.11 and Redis 8.0.2 came from Debian 13 amd64 packages. The package index hash was checked against a signed InRelease and every downloaded .deb against its SHA-256 in that index. The harness initialized a new database, applied the pinned migrations and started password-protected services bound to IPv4 loopback.
- Upstream retains its AGPLv3 license, authorship and notices. This delivery contains an independent HTTP client, fixture and reproduction code. It references the upstream checkout. Retain its license, applicable notices and corresponding-source distribution obligations when redistributing binaries. A modified Postmill network service must prominently offer its interacting users the corresponding source for the running version, free of charge. [Pinned license](https://github.com/postmill-ai/postmill-app/blob/b59d7ca3656836a8a8c8144dc3cde6a93070d083/LICENSE)

## Reproduce

Use an isolated Linux workspace with free loopback TCP ports 54971, 55439 and 56379, Node 24, PostgreSQL 17 server and client utilities, Redis, Python 3 and several gigabytes of disk. Run as a regular OS user. Install native canvas dependencies if its matching prebuilt binary is unavailable. The direct backend serves the pilot. PostgreSQL and Redis are local and the browser frontend is unnecessary.

The following commands assume the current working directory is the RETALLY repository and `$PWD/upstream/postmill` is the dedicated Postmill checkout. Prepare a fresh checkout and its frozen dependencies.

```sh
RETALLY_PILOT_ROOT="$PWD"
git clone https://github.com/postmill-ai/postmill-app.git upstream/postmill
git -C upstream/postmill checkout --detach b59d7ca3656836a8a8c8144dc3cde6a93070d083
cd upstream/postmill
corepack pnpm --version
CI=true PUPPETEER_SKIP_DOWNLOAD=1 corepack pnpm install --frozen-lockfile --ignore-scripts
(cd node_modules/canvas && node ../prebuild-install/bin.js -r napi)
CHECKPOINT_DISABLE=1 node node_modules/prisma/build/index.js generate \
  --schema libraries/nestjs-libraries/src/database/prisma/schema.prisma
node "$RETALLY_PILOT_ROOT/ai_business_os/postmill-build-pilot.cjs" "$PWD"
cd "$RETALLY_PILOT_ROOT"
```

The standard Nest build exhausted its Node heap on the first attempt. A larger-heap retry exited without producing an entry point. For the accepted run the pinned TypeScript compiler emitted 1,837 source modules individually with Nest decorator metadata, and the pinned runtime path resolver loaded the backend. This is a tested pilot build. It does not constitute a passing upstream production release build or full type check. The fallback writes untracked files only into the dedicated checkout's backend dist directory.

Use a **new** state directory each time. PostgreSQL binaries and shared files can also be supplied from a user-local verified package extraction. The actual Debian package run supplied its extracted `usr/lib/x86_64-linux-gnu` via `LD_LIBRARY_PATH` for Redis. The database role uses the current Unix user name.

```sh
python ai_business_os/postmill-local-proof.py \
  --upstream "$PWD/upstream/postmill" --state "$PWD/postmill-proof-new" \
  --pg-bin /usr/lib/postgresql/17/bin --pg-share /usr/share/postgresql/17 \
  --redis /usr/bin/redis-server
python -m unittest -v ai_business_os.test_retally_postmill
node --test --test-name-pattern='campaign navigation' freight/site/test_inquiry.mjs
```

The proof generates temporary local secrets, disables registration and Inngest jobs, and provides no email, model, analytics or publishing credentials. The pilot integration has an empty token and is disabled. Its organization must explicitly enable the provider type so the API can build even a disabled-channel draft. The account key is available to the broker process only. Its generic upstream scopes also cover other actions. Keep a dedicated private host or network namespace around Postmill and keep the upstream key out of the browser. This harness tests a process boundary and a credential-free local channel. Production restrictions across alternate endpoints, independent web sessions, publishing workers and provider egress still need deployment-level verification.

The private HTTP adapter accepts the three catalog entries and reviewed revisions, validates exact channel, destination and media bindings, and generates only DRAFT requests. It uses a nonrecurring editorial timestamp in Postmill's required date field. The approved logo is a local reference, and the drafts are text-only. No image upload, post schedule, provider readback or metric import was performed. The pilot never contacts a social network to publish.

## Evidence and owner desk

`postmill-draft-readback.json` preserves only the three IDs, snapshot hashes, campaign revision markers, readback times and acceptance totals. The pinned Postmill API generated each ID. The harness ran an independent PostgreSQL grouping by state after the last HTTP readback. The first draft-write response was deliberately lost after upstream commit. Readback found the draft. Changing the first draft's copy invalidated editorial signoff and its existing ID survived the draft update. A stopped Redis port failed a TCP probe. The backend restarted with an empty Redis store and a reopened SQLite dispatch ledger. It issued zero new writes during reconciliation. Four writes in the whole run cover three creates and the single revision.

`import_readback(db)` is an offline import for a fresh owner desk, before seeding the local calendar. It validates exact content, version, media reference, time, account, destination and remote ID against the bundled receipt and rejects a differing local draft. The imported rows attest to the dated disposable local instance. The owner can review and revise their local copies. A subsequent edit needs a fresh synchronized readback from the same instance to establish its updated remote state.

The catalog references the November field notes, the October editorial voice and the approved wordmark at `freight/site/assets/brand/retally-wordmark-approved.png`. The pilot's tagged URL carries source instagram, medium organic_social, campaign retally_os_freight_pilot and a distinct content identifier. Canonical landing-form campaign tests passed for internal navigation and for untagged traffic. The integrated synthetic ingress fixture uses the liftgate tag. Synthetic conversions and draft counts are not channel analytics. [Source calendar](https://github.com/P00NSMASHER/github-value-hunt-ledger/blob/33af3fc00fcf359ed7f3d95e85dfa6fc760c79da/freight/brand/social/NOVEMBER_FIELD_NOTES_2026.md)

The pinned `instagram-standalone@v1` adapter supports Instagram professional Business or Creator accounts. It requests an app ID and secret and scopes including instagram_business_basic and instagram_business_content_publish. The approved pilot has no Postmill authorization for @retallyrecovery and no independent account-type or platform readback. RETALLY's dated Metricool record identifies the handle, while the Windsor Instagram identity differs. Treat live account status, real reach, published-post count and provider-confirmed impact as unverified. [Pinned Instagram adapter](https://github.com/postmill-ai/postmill-app/blob/b59d7ca3656836a8a8c8144dc3cde6a93070d083/libraries/providers/instagram-standalone/src/v1/social.adapter.ts)

The harness stops child services on completion or ordinary errors. Keep the synthetic proof directory private. Roll back the console patch through the project's normal branch workflow. The harness never deploys or migrates an existing Postmill instance.
