# Seven-branch managed pilot operations

This runbook covers a **private, operator-assisted pilot** on a controlled workstation.
It does not describe a public customer portal. The current Cloudflare Pages site
publishes allowlisted public assets; it does not host this Python workbench. Never
upload private workspaces or snapshots to Pages, GitHub, or a public tunnel.

Customer readiness is distinct from commercial validation: a new product need not
already have recovered real money to accept its first pilot. Simulations verify the
implemented workflow; they cannot establish genuine identities, customer consent,
production workstation security, real recoveries or comparative performance.

## Supported initial engagement

| Branch | Supported first-pilot population | Required records | Exclude or separately reconcile |
|---|---|---|---|
| Freight | Findings from a frozen, evidence-supported freight truth manifest | Population, shipment/invoice identity, governing authority, calculation proof | Missing tariffs, unresolved shipment identity, overlapping charge components |
| AP | Exact-identity duplicate/overpayment reconciliation | Payments, obligations, dated vendor balances, linked refunds | Fuzzy invoice identity, conflicting statements, unmatched refunds |
| Warranty/Credit | Documented credit or warranty entitlements less linked settlements | Entitlements, effective dates, settlement kinds and reversals | Unproven eligibility, credit memos represented as bank cash |
| Procurement | Contract unit-price and approved billable-quantity differences | Invoice lines, effective authority, approved quantities, explicit unit conversions | Inferred pack sizes, unmodeled taxes/landed costs, unresolved cumulative receipts |
| Rebate | Supported tier programs with explicitly due balances | Complete period purchases/returns, tier terms, payment due dates and settlements | Missing timing, unsupported return policy or unmatched reversals |
| Parcel | Reviewed shipment rate assessments; optional runner contract rating | Charges, service/zone/weight/date, independently reviewed expected rates | Unmodeled carrier exceptions or ambiguous/missing contracts |
| Utility | Supported account/service-class tariff components | Bills with service dates and quantities, effective tariffs, utility identity | Duplicated/corrected bills pending review, unsupported tariff terms |

One workspace holds one client and one declared intake currency. Use separate
workspaces for different clients or intake currencies. Reports retain case currency
and never convert or combine currencies. Inspect imported freight manifest currency
and scope against the engagement before review. Row-count reconciliation is a
completeness control, not an automatic proof that all source-system records exist.

## Install and start

Use the reviewed repository revision with successful release and browser checks.
Python 3.11+ runs the workbench with standard-library dependencies. Do not install
browser testing packages on the production workstation unless needed for testing.
Use an account restricted to the pilot operator, encrypted storage, and an approved
private backup/transfer destination. The service has no TLS or enterprise SSO.

```sh
python -m recoveryworks.workbench_admin init --workspace /private/client-a --client CLIENT-A --currency USD --live
python -m recoveryworks.workbench_server --workspace /private/client-a --port 8765
```

Open `http://127.0.0.1:8765` on that workstation. Assign the customer, primary reviewer,
independent reviewer and operator credentials to the appropriate authorized roles.
Local role keys are not authenticated human identities. A single person possessing
all four keys does not create independent approval. Customer consent must be genuine;
use a separately agreed secure process for source transfer and customer authorization.
The workbench records the role decision and exact evidence but cannot attest who held
the key. Live mode never accepts the simulation claim/cash shortcuts.

## Complete intake and deliver the audit

1. Agree the branch, accounts/business units, currency, period, exclusions, supported
   calculations, data access, and report delivery method. Keep customer funds owned
   by the customer. Claim authorization remains a separate case-level step.
2. Customer/operator uploads source files; map required columns and inspect counts.
   Reviewer reads and verifies the exact files. Operator configures scope dates and
   utility identity. Rebate requires explicit payment due dates and audit date.
3. Customer enters **Authorize audit scope**, including independent export counts,
   source system, exclusions and how the population reconciles. Reviewer checks the
   customer scope and source coverage. Mismatched counts, changed bytes/settings,
   missing reviews and incomplete scope block scanning. All seven branches follow
   this same gate in both simulation and live mode.
4. Operator scans; reviewers inspect findings, exceptions, duplicate/overlap holds
   and calculation evidence. Corrected evidence needs renewed intake approval and
   reviewed case replacement. Preserve old ledger history.
5. Use the existing primary/independent case reviews and reviewed live case bundle,
   customer authorization, external-action record and cash evidence workflow.
   A workbench record is not permission to contact a counterparty. No external
   messages, claim submissions or money movements are performed by this service.
6. Select a report format under Operations and download the customer report. HTML is
   printable, CSV supports spreadsheet review, and JSON contains evidence references
   and journal head. Verify the SHA-256 supplied by the workbench before transferring
   through the agreed private channel. Review holds and intake blockers with the
   customer; potential amounts are not recovered money. Reject/supersede unsupported
   cases rather than presenting them as actionable claims.

## Daily operation and incidents

At start of work, after any evidence correction, and before delivery:

```sh
python -m recoveryworks.workbench_health --workspace /private/client-a
```

Exit 0 means the implemented local health checks pass; exit 2 means stop and inspect
failed checks. Output excludes customer records and keys. Checks include original
and normalized evidence, journal replay, private file permissions, unexpired roles,
active-branch intake, at least 100 MiB free space, and an actual restore of a backup
created within 24 hours. This is not production or security certification.

- **Before and after a work session:** use Verify backup and restore. Copy snapshots
  to the approved encrypted backup location. The health check validates local backup
  recovery, not off-device storage availability. Agree actual recovery objectives;
  no uptime or recovery-time guarantee is inferred from these checks.
- **Expired/lost key:** use the credential rotation/revocation CLI in WORKBENCH.md.
  Stop the server first for an active compromise; in-flight authorized requests may
  finish. Record incident scope privately; review access and affected source history.
- **Corrupt or missing evidence:** stop affected actions. Preserve evidence and the
  failing workspace; restore a known-good snapshot into a new directory and replay.
  Never repair a journal by deleting or rewriting entries.
- **Failed code upgrade:** stop the server; retain the pre-upgrade backup and source
  revision. Test the older release against a separate restored copy. Never run an
  older binary on a new ledger format without verifying replay compatibility.
- **Service capacity:** loopback only, at most 16 simultaneous handler connections,
  10-second idle socket timeout, bounded request bodies, no third-party UI assets.
  Saturated new sockets are closed. This is a small pilot service, not a load-tested
  internet service.

## Optional encrypted off-device archive preflight

Once a fresh complete local snapshot has been verified, use the optional `offsite_archive` tool in [OFFSITE_BACKUP.md](OFFSITE_BACKUP.md) to create an authenticated AES-256-GCM ciphertext copy and independently verify restore. The tool does **not** upload files, certify remote storage, escrow recovery keys, attest workstation disk encryption, or authorize use of an organization-managed device. All such release controls must be verified by the responsible owners. Plaintext `.json` snapshots must not be moved to shared cloud destinations.

## Restore

```sh
python -m recoveryworks.workbench_admin restore --snapshot /private/backups/SNAPSHOT.json --destination /private/client-a-restored
python -m recoveryworks.workbench_credentials --workspace /private/client-a-restored --role operator --reason 'Restore recovery'
```

Issue fresh keys for the other three roles using the same command. Restore disables
all saved keys to prevent resurrection of revoked access. Verify journal head,
source hashes, all active branches, and a new backup/restore check before resuming.

## Retention, support and release boundary

Before a real pilot, record the named operator, separate reviewer, support contact,
incident escalation path, agreed retention/deletion schedule, authorized backup
locations and any preservation requirements in the private engagement record.
Do not invent a universal retention period. The workbench does not automatically
expire evidence or delete records: close access by revoking keys, then carry out an
authorized whole-engagement disposal through controlled filesystem and backup
administration after preservation requirements are resolved. Deleting the active
workspace alone does not delete backups or reports already delivered elsewhere.

An initial local pilot release needs an accepted code revision, successful checks,
verified workstation/data-transfer controls, named operating responsibility and
actual customer scope/authorization at engagement time. Enterprise SSO, a remotely
hosted customer portal, named accounting/carrier integrations and market-leadership
claims remain separate scope; these have not been implemented or certified here.
