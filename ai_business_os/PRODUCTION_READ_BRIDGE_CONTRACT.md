# Production Read Bridge Contract

## Purpose

`ai_business_os.production_bridge.ProductionReadBridge` is the first canonical runtime bridge
from the Python AI Business OS to the authoritative private `ai_business_os_prod` Business Brain.

It exists to let agents and the future CEO Command Center **observe** production state without
implicitly gaining authority to mutate it.

## Authority boundary

The bridge is deliberately read-only.

- It accepts an injected private query executor; it contains no credentials or connection strings.
- It permits one `SELECT` statement at a time and rejects mutating SQL before execution.
- It reads the live schema fingerprint and can fail closed when it differs from the versioned
  `manifest.json.live_schema_fingerprint_sha256`.
- It exposes only four initial production surfaces:
  1. schema fingerprint;
  2. canonical businesses;
  3. latest command-center snapshot;
  4. pending human approvals.
- Pending approvals are identified by the production `request_key` + `intent_hash` contract;
  the bridge does not invent or substitute a separate request identity.
- It does **not** approve requests, create work, dispatch Hunters, open pull requests, send
  messages, move money, deploy code, or write to Supabase.

## Private runtime responsibility

A private deployment may inject a PostgreSQL/Supabase executor with least-privilege SELECT access.
Credentials and mutable operating data remain outside the public repository.

Any future write path must go through the existing AI Business OS governance control plane rather
than being added to this bridge.

## Live contract verification

The production-use verification step must compare the live
`ai_business_os_prod.schema_fingerprint_v1()` result to
`manifest.json.live_schema_fingerprint_sha256` before trusting any production snapshot. It must
also validate the live approval-inbox column contract rather than assuming test-only field names.

No live customer, provider, approval, or operating data is committed to the public repository.

## Next production-use step

Feed the verified read-only portfolio state into the canonical agent/Hunter planning layer without
granting new write authority.
