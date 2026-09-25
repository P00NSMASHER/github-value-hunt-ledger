# Production Read Bridge Contract

## Purpose

`ai_business_os.production_bridge.ProductionReadBridge` is the canonical runtime bridge from the
Python AI Business OS to the authoritative private `ai_business_os_prod` Business Brain.

It lets agents and planning systems **observe** production state without implicitly gaining
authority to mutate it.

## Authority boundary

The bridge is deliberately read-only.

- It accepts an injected private query executor; it contains no credentials or connection strings.
- It permits one `SELECT` statement at a time and rejects mutating SQL before execution.
- It reads the live schema fingerprint and can fail closed when it differs from the versioned
  `manifest.json.live_schema_fingerprint_sha256`.
- Core command-center reads expose canonical businesses, latest command-center snapshot and pending
  human approvals.
- Planning reads expose active agents, active portfolio initiatives, unresolved portfolio data gaps
  and open agent goals.
- Pending approvals are identified by the production `request_key` + `intent_hash` contract.
- It does **not** approve requests, create goals, dispatch Hunters, open pull requests, send
  messages, move money, deploy code, or write to Supabase.

## Private runtime responsibility

A private deployment may inject a PostgreSQL/Supabase executor with least-privilege SELECT access.
Credentials and mutable operating data remain outside the public repository.

Any future write path must go through the existing AI Business OS governance control plane rather
than being added to this bridge.

## Live contract verification

The production-use verification step must compare the live
`ai_business_os_prod.schema_fingerprint_v1()` result to
`manifest.json.live_schema_fingerprint_sha256` before trusting production planning state.

No live customer, provider, approval, or operating data is committed to the public repository.
