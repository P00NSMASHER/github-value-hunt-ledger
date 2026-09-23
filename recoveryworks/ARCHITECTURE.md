# RecoveryWorks architecture

## RecoveryOS shared layers

1. **Ingestion** — branch-specific adapters normalize source data while original source hashes remain addressable.
2. **Authority** — effective-dated governing rules carry source hashes and explicit verification status.
3. **Calculation** — deterministic expected-vs-actual arithmetic; LLM output is never accepted as money math.
4. **Evidence** — every load-bearing source has a locator, content hash, type, and verification state.
5. **Recovery Ledger** — proof-deduped case lifecycle, review, authorization, claim, externally evidenced recovery, and fee fields.
6. **Human control** — validated dollars are not permission to act; claims require reviewer approval and customer authorization.
7. **Outcome learning** — realized recoveries, false positives, reviewer hours, and branch economics should feed the existing technology-intelligence outcome system only when supported by external evidence.

## Branch boundary

A branch owns domain-specific parsing and expected-amount logic. RecoveryOS owns
the invariants after normalization. This prevents a growing portfolio of recovery products from drifting into
incompatible concepts of evidence, money, approval, and recovery status.

## Security boundary

- Payer data is sensitive and must remain inside an appropriately controlled environment.
- Source files are referenced by hash/locator; never silently replace historical rule versions.
- Unknown or conflicting authority stays REVIEW.
- No accidental credential/private-data discovery is a valid authority source.
- No external claim/dispute/contact action occurs without explicit authorization.
- No amount becomes recovered cash from a caller-supplied number alone; verified,
  hash-bound settlement evidence with matching currency and chronology is required.
  Evidence names the exact finding, and one client cannot allocate a settlement
  ID or source line to two findings.
- Durable lifecycle events carry authenticated canonical UTC times. Replay
  preserves those times, and legacy bundles without authenticated event times
  fail closed rather than appearing newly rebuilt.

## Commercial surface

The universal client-facing output is the Recovery Ledger:

- potential recovery
- validated recovery
- authorized/claimed recovery
- recovered cash (verified settlement evidence only)
- branch
- counterparty
- transaction reference
- rule/version provenance
- evidence packet readiness
- fee eligibility and realized fee

This supports one-time historical audits and continuous monitoring without changing the evidence model.

## Hostile-examination layer

For findings at or above $1,000,000 of validated potential recovery, RecoveryOS adds a mandatory assurance layer above the ordinary branch engines: point-in-time authority snapshots, source authentication attestations, a code/input calculation manifest, two approving reviewers, an independent adverse-evidence challenge, deadline assessment, a frozen CaseProofBundle, explicit client actor authorization, and a hashed exact outbound-action envelope. The durable journal preserves these artifacts for replay. See `recoveryworks/HOSTILE_EXAMINATION_STANDARD.md`.

## Local durability boundary

The reference local store performs atomic replacement under a cross-process
private lock, so its optimistic head-hash check is an actual serialized
compare-and-swap operation. It applies and verifies owner-only permissions on
POSIX and a current-user plus SYSTEM private DACL on Windows. These controls do
not substitute for an encrypted production data service, independent immutable
logging, backup policy, or tenant-aware service authorization.
