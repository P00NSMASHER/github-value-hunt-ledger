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

## Remaining operating work

1. Review exact private business-to-catalog bindings while retaining source IDs.
2. Supply service-specific authenticated register readers through the private
   runtime and verify their completeness and freshness contracts.
3. Use existing independent outcome/finance verification before adding monetary
   metrics or reporting paying customers.
4. Complete the normal source and production release requirements before enabling
   the integration in a deployed runtime.

No customer writes, workflow transitions, referrals, deliveries, payments,
database migrations or recurring tasks are implemented by this observation layer.

## Verification

```bash
python -m unittest ai_business_os.test_retally_group_private ai_business_os.test_retally_customer_register ai_business_os.test_retally_group ai_business_os.test_ceo_command_center
```

Tests use synthetic identities and records. A read-only live SQL observation can
confirm schema/query compatibility; it cannot establish production deployment,
customer payment, delivery acceptance or release approval.
