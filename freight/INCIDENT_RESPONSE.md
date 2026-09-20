# Freight Recovery — Incident Response Runbook

Updated: 2026-09-20

This is the current **operating plan** for a controlled Freight Recovery pilot.
It is not evidence that a production SOC, pager rotation, forensic vendor,
breach counsel, insurer workflow, or certified incident program has been
deployed.

## Principles

1. Protect customer evidence before preserving convenience.
2. Contain first; do not destroy evidence while trying to clean up.
3. Unknown exposure remains **UNKNOWN** until investigated.
4. A service/provider success response is not sufficient evidence of containment,
   deletion, or recovery.
5. External notifications are never sent automatically by the model.
6. Customer/regulator/insurer notification requires explicit human authorization
   and a recorded contractual/legal/policy basis.
7. Do not place credentials, raw customer data or sensitive incident payloads in
   GitHub issues, source files or the technology-intelligence ledger.

## Severity

- **SEV1** — confirmed or strongly suspected material customer-data compromise,
  destructive integrity event, or uncontrolled privileged access.
- **SEV2** — material confidentiality/integrity/availability incident with
  contained scope or uncertain exposure.
- **SEV3** — limited operational/security defect with no current evidence of
  material customer impact.
- **SEV4** — low-impact event, policy deviation or near miss.

Severity may increase as evidence changes.

## Incident states

- **OPEN** — investigation/containment incomplete.
- **CONTAINED** — spread/active impact is stopped; root cause/recovery may remain.
- **RECOVERED** — service/data integrity has been restored and verified.
- **CLOSED** — exposure is no longer UNKNOWN, required evidence is preserved and a
  postmortem/reference exists.

`freight/incident_response.py` enforces the minimum closure and notification
evidence rules.

## Immediate operating sequence

### 1. Open and scope
Record:
- incident ID;
- buyer + business unit;
- time observed;
- reporter/source;
- affected systems/data classes;
- current exposure state: UNKNOWN / NO_EVIDENCE / SUSPECTED / CONFIRMED;
- severity;
- evidence hashes/locations.

### 2. Contain
Prefer reversible, evidence-preserving actions:
- revoke or rotate affected credentials through the actual secret-management
  system;
- disable affected integration/path;
- restrict customer-data access;
- isolate parser/worker/service where relevant;
- stop outbound consequential actions if their integrity is uncertain.

Do not silently delete logs/source evidence during containment.

### 3. Preserve evidence
Preserve:
- relevant audit-log/export objects;
- source/provider receipts;
- release/provenance hashes;
- object/file hashes;
- relevant configuration/version references;
- containment decisions.

The application hash chain is useful reference evidence but is not an external
trusted timestamp/WORM system.

### 4. Assess exposure and obligations
A designated human owner reviews:
- customer contract;
- DPA/security addendum;
- applicable privacy/security obligations;
- insurer requirements;
- counsel guidance where needed.

The model may organize evidence but must not independently decide a statutory
breach-notification obligation.

### 5. Recover
Verify restoration against:
- known-good configuration/release provenance;
- backup/restore evidence where relevant;
- data-integrity checks;
- cross-tenant/access-control checks where relevant;
- settlement/audit semantic invariants for money-bearing state.

### 6. Communicate
Any external communication requires:
- explicit authorization;
- recipient/scope;
- factual evidence basis;
- approved wording/process.

Do not speculate about exposure, root cause, recovered dollars, or customer
impact.

### 7. Close
Closure requires:
- containment complete;
- recovery verified;
- exposure state resolved from UNKNOWN;
- preserved evidence;
- postmortem reference;
- corrective actions / owners.

For SEV1/SEV2, evidence hashes are required before closure.

## Learning loop

After sensitive details are removed, reusable **failure modes and control
lessons** may update the internal engineering backlog or search policy.
Customer identity, secrets, incident payloads and privileged forensic details
must not enter the public/private technology-hunt learning ledger.

## Still external / deployment-specific

Before annual assurance, establish and test:
- named incident commander/on-call roles;
- production alerting;
- logging/SIEM retention;
- external WORM/immutable evidence where required;
- contact tree and buyer-specific notification clauses;
- breach counsel / insurer procedures if applicable;
- tabletop and restoration exercises against the deployed environment.
