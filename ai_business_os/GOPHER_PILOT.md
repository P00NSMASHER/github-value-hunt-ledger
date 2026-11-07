# Synthetic GopherCRM pilot

The server uses SQLite and binds only to 127.0.0.1. The worker uses a sales API key. Registration is checked as disabled at startup. The pilot supplies no mail or model credentials and disables scheduled automations. Linux libseccomp rejects outbound connect and datagram/message send calls in the server before it starts. The launcher checks for EPERM before executing the server.

## Build and boot

Requires Linux, Python 3.11+, libseccomp.so.2, Git, Go 1.25 or newer, and Node/npm for the optional Gopher web UI. Run the following from the RETALLY checkout. Choose a new private local directory for the fixture database and secrets.

```sh
RETALLY_REPO="$PWD"
PILOT_ROOT="$(mktemp -d)"
git clone https://github.com/florinel-chis/GopherCRM.git "$PILOT_ROOT/source"
git -C "$PILOT_ROOT/source" checkout --detach ae53d6dbb251e33484207756cc9699bd316834a7
(cd "$PILOT_ROOT/source" && go mod verify && go build -o "$PILOT_ROOT/gopher" ./cmd && go build -o "$PILOT_ROOT/create-admin" ./cmd/create-admin)
python "$RETALLY_REPO/ai_business_os/gopher_pilot.py" --binary "$PILOT_ROOT/gopher" --admin-binary "$PILOT_ROOT/create-admin" --state "$PILOT_ROOT/state"
```

In another terminal in the same network namespace, retain the same values of PILOT_ROOT and RETALLY_REPO. Use the upstream React login at http://127.0.0.1:19824 after starting the UI with the following commands. The generated login lives in the private state/login.json file. The worker needs only state/client.json. Its key expires after seven days.

```sh
cd "$PILOT_ROOT/source/gocrm-ui"
npm ci --ignore-scripts --no-audit --no-fund
VITE_API_BASE_URL=http://127.0.0.1:19823/api/v1 npm run build
npm run preview -- --host 127.0.0.1 --port 19824 --strictPort
```

Stop the launcher before backing up the whole state directory with its restrictive permissions. Restart against the same directory to resume. The test below starts and stops its own private server, restores its database and credentials into a different directory, and removes that disposable state on exit. Choose another port if the persistent pilot is running.

```sh
python "$RETALLY_REPO/ai_business_os/verify_gopher_pilot.py" --binary "$PILOT_ROOT/gopher" --admin-binary "$PILOT_ROOT/create-admin" --port 19825
```

## Delivery and recovery

The pin filters lead results by the caller's visibility. The sales user can assign tasks only to itself and its task search filter is ignored. The adapter verifies the role and account, matches lead external IDs exactly, and examines at most 500 assigned tasks before requiring manual review. The qualification task contains a deterministic hash of the inquiry reference. In this dedicated fixture database only, two partial unique indexes reserve synthetic external IDs and qualification task titles across owners and soft deletion. These additional constraints belong to the pilot bootstrap. Applying them to another database requires an explicit deployment and migration review.

Record durable write intent before each POST. A lost response can indicate a committed write. Re-read by external ID or task marker, compare owner, lead and persistent ID, and hold if the result is missing, ambiguous or unauthorized. A 429 at this pin is an explicit rejection before the handler. Read-only throttling has two bounded retries. The adapter never automatically replays a POST. Renaming or reassigning a linked task can require manual reconciliation.

## Compatibility record

On 2026-11-07, the tested default branch and pin both resolved to ae53d6dbb251e33484207756cc9699bd316834a7. The service built with Go 1.26.10 on linux/amd64 from an unmodified checkout. Its binary SHA-256 was 5c14d37ce483e1196733e21ba911cb1a06f260e3486f6131504c458a4c9a07c2. The upstream go.sum hash was 8500b5f8133d2887cea54f908f9840af9ccc1a17675c72a258a92685d7fe0839 and the UI package-lock.json hash was 5799b2ff50acda3f8d4c8a0cdaa125cf7f7f28d46237bb7f070e53f4e323bcd7. Preserve the upstream MIT copyright and permission notice when distributing GopherCRM or substantial portions.

The verification proxy discarded the real 201 responses for both POSTs. The sales API key recovered lead 1 and task 1. After clean shutdown and restore, both IDs were still visible and the restored database held one row in each table. Reassignment hid the lead from the sales user, the database rejected a duplicate external ID, and the adapter held the task with the redacted lead link.

The upstream UI built with Node 24.22.1 and npm 11.9.0. An npm production dependency audit reported 6 high-severity packages and 1 moderate (axios, follow-redirects, form-data, lodash, react-router, react-router-dom and zod). govulncheck v1.9.0 in binary mode reported zero affected symbols, eight packages with findings and five modules with findings. Review and retest a patched build before deployment.

An independent headless Chromium 153 session signed into the pinned React app, opened the fixture in Leads, and found its qualification task in Tasks. The page attempted zero non-loopback requests. To repeat in the upstream gocrm-ui directory, install the Playwright Chromium binary and run the verifier against a known fixture. The optional RETALLY_CHROMIUM_HELPER points to the absolute module path of a locally installed @sparticuz/chromium when the host requires a headless shell. The independently tested alternative used version 153.0.0.

```sh
npx --no-install playwright install chromium
node "$RETALLY_REPO/ai_business_os/verify_gopher_ui.cjs" "$PILOT_ROOT/state/login.json" "$FIXTURE_EMAIL" "$FIXTURE_EXTERNAL_ID"
```
