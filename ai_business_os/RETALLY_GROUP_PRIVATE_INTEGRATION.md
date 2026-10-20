# RETALLY Group private observation

This extension connects the group structure to **observations of existing source
records**. It is read-only source code awaiting normal release acceptance. The
public HTML preview remains a planning artifact; private responses are never
written into the public catalog or generated HTML.

## What is implemented

`ProductionReadBridge.retally_group_source_snapshot()` reads existing tables in
`ai_business_os_prod`: businesses, customers, financial events and external
outcomes. It selects only business IDs/slugs and per-business record counts.
Customer identities, contact fields, financial amounts, source documents and
free-form metadata are not selected.

The method checks the expected schema fingerprint before reading those records,
then compares the fingerprint returned in the same statement as the data. The
counts and business identities come from a single PostgreSQL statement snapshot.
Other existing command-center reads remain separate observations.

`build_private_group_observation()` validates the exact result shape, rejects
duplicate identities and malformed counts, and produces one reconciliation row
per catalog entry. A unique exact-slug match requires review. Multiple candidate
records stay separate. Entries without a match are explicit. Unmapped source
records are counted without exposing their identities in this projection.

**Record counts are not verified business outcomes.** A customer table row is not
proof of a paying customer; a financial event is not proof of settled fees; an
external-outcome row is not new independent verification. Verified lead, customer,
cash and profit metrics remain unknown. The output contains no merged financial
totals and grants no action or identity-mutation authority.

Counts cover records visible to the injected executor, not all possible service
stores. The query time is recorded, and observations older than five minutes are
labeled stale by default. Fresh query time does not prove that every business has
supplied complete or recent operating records. Future observation times fail.

## Private runtime interface

Use the existing authenticated private executor with least-privilege read access
and the reviewed fingerprint from
`supabase/migrations/ai_business_os/manifest.json`. Credentials stay in the private
runtime. The module supplies no login, credentials, database grants or public API.

```python
from ai_business_os.ceo_command_center import CommandCenterOperator
from ai_business_os.production_bridge import ProductionReadBridge

# Both variables are supplied by the existing approved private runtime.
operator = CommandCenterOperator(
    ProductionReadBridge(private_read_executor),
    expected_schema_fingerprint=approved_schema_fingerprint,
)

private_observation = operator.group_observation()
# Or include it alongside the existing command center:
private_dashboard = operator.dashboard(include_private_group=True)
```

The default `dashboard()` performs no additional group source query. Opt-in
failure raises an error; unavailable state never becomes an empty success.
The response remains private even though it excludes customer names and amounts.
It contains private business identifiers and must not be committed or served
publicly. `retally_group.render` cannot accept this private response.

## Optional customer-register reader

`CommandCenterOperator` optionally accepts `customer_register_reader`, a callable
that returns a decoded snapshot matching the register schema. The private runtime
must authenticate and authorize the reader and implement any service-specific
mapping from its existing stores. There is no assumed customer-register database
table and no automatic conversion of legacy customer rows into engagements.

Without a reader, the report says `NOT_CONNECTED` and register counts are unknown.
A supplied valid empty register means zero **observed records**, while verified
customer and financial metrics remain unknown. Reader and validation failures
produce a fixed error without copying private exception details.

`retally_customer_register.py` implements:

- Strict required fields, scalar types and duplicate-JSON-key rejection.
- Unique account, engagement and referral references.
- Existing-account and existing-engagement checks, consistent referral accounts
  and target businesses, and service ownership checks.
- Known-offset timestamps, no future records, and engagement updates no earlier
  than account creation. Timestamps support RFC 3339 at microsecond precision.
- Exact recovery service IDs; other services accept null or bounded opaque
  `private:` references.
- Declared stage/payment/referral counts and missing-reference counts, excluding
  private references, contacts, owner text and raw records from the observation.

The current register schema has no snapshot timestamp or authenticated provenance
envelope. Its source authentication and snapshot freshness therefore remain
explicitly unassessed. A populated authorization, review, delivery or financial
reference is a declaration, not authenticated evidence. Declared `PAID` and
`AUTHORIZED_INTERNAL_HANDOFF` states grant no authority and establish no revenue.
Counts from this optional register are kept separate from database source counts;
they are not added together or used to approve a group identity binding.

## PermitPlate NYC source reader

`retally_permitplate.PermitPlateNYCReader` implements the first service-specific
connection. Its source contract is the existing
[NYC onboarding producer](https://github.com/P00NSMASHER/permitplate-nyc/blob/7be09a82249ab1ef6b6a9de7402690dbefd47f5e/pipeline/curated-stripe-onboarding.js)
and [private-state runner](https://github.com/P00NSMASHER/permitplate-nyc/blob/7be09a82249ab1ef6b6a9de7402690dbefd47f5e/pipeline/run-curated-stripe-onboarding.js).
It reads the NYC subscription ledger and its initialization anchor. The separate
Pennsylvania Permit Pack and x402 services are outside this adapter's scope.

The private runtime supplies two authenticated read callbacks and a stable
protected pseudonym key. The reader resolves one immutable commit, then reads both
fixed paths at that commit. Each file response must contain exactly `commit_sha`,
`blob_sha` and `content`; the content is the original decoded UTF-8 file text,
including its final newline. The adapter checks Git blob hashes, strict source
shapes, the ledger seal, the initialization anchor and timestamp ordering.
Missing files, malformed records and mixed revisions fail rather than becoming
empty success. Callback error details are not returned.

```python
from ai_business_os.retally_permitplate import PermitPlateNYCReader

# These callbacks use the approved private repository and existing credentials.
# resolve_private_revision() -> full immutable Git commit SHA
# read_private_file(commit_sha, path) ->
#     {"commit_sha": commit_sha, "blob_sha": "...", "content": "..."}
nyc_reader = PermitPlateNYCReader(
    resolve_private_revision,
    read_private_file,
    pseudonym_key=protected_stable_key,
    max_age_seconds=9 * 60 * 60,
)
operator = CommandCenterOperator(
    ProductionReadBridge(private_read_executor),
    expected_schema_fingerprint=approved_schema_fingerprint,
    permitplate_nyc_reader=nyc_reader,
)
service_observation = operator.group_observation()["service_registers"]["permitplate_nyc"]
```

The key must contain at least 32 bytes and remain stable in the private runtime;
it is not committed, logged or returned. Source-scoped HMAC references keep
provider identifiers out of the transient normalized register. A Stripe customer
ID can group subscriptions within this service only. A subscription without a
customer ID receives a distinct surrogate account, counted explicitly. Neither
email similarity nor shared group ownership merges customers. Key rotation or
later replacement of a surrogate requires an explicit private reconciliation.

The transient register is immediately reduced to allowlisted aggregate fields.
The response contains no contacts, emails, raw provider identifiers, pseudonym
references, target dates or free-form source text. Exact source states remain
visible as counts, including `HOLD_SUBSCRIPTION_CHANGED`. The generic stage is
`inquiry`: retained intake does not establish an accepted scope or fulfillment
authorization. Current payment status is `UNKNOWN`, currency is unknown, all
evidence references are absent, and no referrals are invented. The source's
historical paid-checkout context is insufficient to prove current invoices,
refund status, settled cash or delivery.

Source freshness uses the ledger's `checkedAt`, separately from the adapter read
time. The configurable nine-hour default is a local observation policy, not a
NYC customer service promise or proof of provider completeness. Old source data
is labeled `STALE`; the reader never updates it. `firstDiscoveredAt` supplies
account creation time, while `checkedAt` means latest source-state observation,
not a per-engagement modification time. A reader retains continuity checks during
its lifetime; the private runtime owns persisted continuity across restarts.

Commit consistency and matching hashes establish integrity of the supplied
snapshot. They do not independently authenticate its writer, the caller's
repository access, Stripe observations or commercial evidence. Those limitations
remain explicit in the source-observation envelope. The generic register's own
authentication and freshness fields remain unassessed; the service envelope
reports the narrower checks actually performed.

The command center stores this service observation separately from its generic
register and database counts, with no summed customer or financial totals. An
unconfigured reader reports `NOT_CONNECTED`. Successful source observation does
not approve a missing private business binding. The default dashboard does not
invoke this reader; the public dashboard remains disconnected.

## Remaining operating work

1. Review exact private business-to-catalog bindings while retaining source IDs;
   use the [typed source reconciliation](RETALLY_GROUP_SOURCE_RECONCILIATION.md)
   to distinguish project/repository evidence and resolve conflicting mappings.
2. Configure the PermitPlate NYC read callbacks and protected key in the approved
   private runtime. Resolve CaptureBrief's live outcome-ledger location and
   account identity map before adding its adapter. Reconcile the separate PA
   product scope before importing its orders into this group catalog.
3. Use existing independent outcome/finance verification before adding monetary
   metrics or reporting paying customers.
4. Complete the normal source and production release requirements before enabling
   the integration in a deployed runtime.

No customer writes, workflow transitions, referrals, deliveries, payments,
database migrations or recurring tasks are implemented by this observation layer.

## Verification

```bash
python -m unittest ai_business_os.test_retally_group_private ai_business_os.test_retally_customer_register ai_business_os.test_retally_permitplate ai_business_os.test_retally_group ai_business_os.test_ceo_command_center
```

Tests use synthetic identities and records. A read-only live SQL observation can
confirm schema/query compatibility; it cannot establish production deployment,
customer payment, delivery acceptance or release approval.
