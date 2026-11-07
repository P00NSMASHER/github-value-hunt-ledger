# End-to-end private acceptance

Run the following command from the RETALLY checkout after preparing the pinned dependencies. The destination must be a new private directory outside any Git checkout or Git-marked parent directory.

```sh
bash ai_business_os/verify_retally_stack.sh /private/new-stack
```

The command starts a fresh Postmill, writes three drafts, revises one and verifies their IDs after an empty Redis restart. The freight and CaptureBrief case desk then imports **this run's** synthetic readback. The wrapper checks those IDs through SQLite in the fresh desk and its restored backup and runs the pinned Prime RPC lease fixture. If a component fails, execution stops with its logs in the selected directory. A completed run writes `stack-acceptance.json` with relative paths and SHA-256 hashes for the underlying receipts. The desk's owner login and restore instructions are in RETALLY_OS_PILOT.md. Set the owner desk database to the new run's `desk/desk.sqlite`.

## Prepared inputs

| Input | Path and preparation |
| --- | --- |
| Postmill and Prime | Set `RETALLY_UPSTREAM_ROOT` to an absolute directory with `postmill/` and `prime/` subdirectories. Prepare the pinned backend following POSTMILL_PILOT.md and the pinned worker following prime_pilot/README.md. From the RETALLY root run `npm ci --prefix ai_business_os/prime_pilot --ignore-scripts --no-audit`. |
| GopherCRM, CaptureBrief and Python | Set `RETALLY_PILOT_CACHE` to the cache populated by run_retally_pilot.sh. It contains gopher-server, create-admin, capturebrief/ and venv/bin/python with the pinned PDF reader. The default is the retally-pilot directory in the XDG user cache. Set `RETALLY_GO_BIN` if the Go tool used to inspect build revisions is outside PATH. |
| PostgreSQL and Redis | The default PostgreSQL 17 bin and share directories are /usr/lib/postgresql/17/bin and /usr/share/postgresql/17. Redis defaults to /usr/bin/redis-server. Override using `RETALLY_POSTGRES_BIN`, `RETALLY_POSTGRES_SHARE` and `RETALLY_REDIS_SERVER`. A user-local package extraction may need its native library directory in `LD_LIBRARY_PATH`. |
| CaptureBrief public source | Point `RETALLY_SOURCE_PDF` at the original, hash-checked public Treasury PDF for an offline run. When omitted, CaptureBrief retrieves the public source through its existing restricted reader. |
| Optional real CPU inference | Prepare the dependencies as described in prime_pilot/cpu/README.md, including `npm ci --prefix ai_business_os/prime_pilot/cpu --ignore-scripts --omit=optional --no-audit`. Set `RETALLY_PRIME_GGUF` to the absolute location of the pinned Qwen2.5-Coder-0.5B GGUF. The CPU sandbox checks its SHA-256. The wrapper invokes local inference and requires an independently verified patch before writing a successful stack receipt. |

All upstream test identities, external references, money and content are synthetic. The replay fixture uses an upstream faux model. A CPU run records its generated candidate separately with the independent verifier's result, and preserves rejected candidates. Keep the complete state directory private because it includes disposable credentials for the local services.
