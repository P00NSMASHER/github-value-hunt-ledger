# Historical MNPI Research Corpus

This package is for **historical, already-public research and compliance analysis only**.

It does not ingest live confidential information and is not a trading feed.

## Step 1 — source registry

The source registry is the provenance gate for every later artifact.

Every source must include:

- stable `source_id`;
- source type;
- admissibility class;
- publisher;
- title;
- HTTPS source URL;
- publication date;
- SHA-256 of the exact retained artifact;
- timezone-aware retrieval timestamp;
- explicit confirmation that the source was already public;
- optional case/docket identifiers.

### Admissibility

**PRIMARY_PUBLIC_RECORD**

For already-public SEC, DOJ, court, or official FOIA artifacts. These may produce
candidate case/trade/publication-boundary facts in later stages, but those facts
will still require extraction review and exact source locators.

**PUBLISHED_RESEARCH_RECONSTRUCTION**

For peer-reviewed/public academic replication material. These remain explicitly
academic reconstructions and are never silently promoted to primary enforcement
facts.

**DISCOVERY_ONLY**

For secondary indexes, articles, catalogs, or lead-generation sources. They may
identify a primary source to retrieve, but they cannot establish a trade fact.

## Integrity

Each `SourceRecord` has a deterministic proof hash.

The full registry has its own order-independent registry hash. Duplicate artifacts,
conflicting source IDs, malformed hashes, non-HTTPS locations, naive timestamps,
or not-yet-public sources fail closed.

## Scope boundary

The constant `HISTORICAL_RESEARCH_COMPLIANCE_ONLY` is included in every record
and registry proof. A registry payload with a different usage scope is rejected.

## Tests

Run:

```bash
python -m unittest historical_mnpi.test_source_registry -v
```

Step 2 will retain raw public artifacts separately from normalized facts. No raw
source documents are downloaded by Step 1.


## Step 2 — raw artifact separation

Raw public source bytes are retained separately from every future normalized fact.

`LocalContentAddressedArtifactStore` accepts bytes only when:

- the source already exists in the Step-1 registry;
- the supplied source record's proof hash exactly matches that registered record;
- the source is confirmed already public;
- the exact bytes hash to the registered source SHA-256;
- acquisition/storage timestamps are timezone-aware and ordered;
- metadata such as filenames and media types passes validation before any write.

Artifacts are addressed as `sha256:<digest>` and stored under a content-addressed
layout. Reads re-check byte length and SHA-256. Existing objects are idempotent and
never overwritten with different content.

The local store reports
`APPLICATION_ENFORCED_APPEND_ONLY`. It does **not** claim the underlying
filesystem is provider-level WORM. `PROVIDER_VERIFIED_IMMUTABLE` requires a
separate provider attestation hash.

A `RawArtifactManifest` binds the exact source-registry hash to exactly one
retained artifact per registered source. The manifest contains hashes and custody
metadata only; source bytes are deliberately absent.

Future normalized records should use `SourceArtifactRef` to point to an exact
artifact and source location such as a page, paragraph, table, CSV row, JSON
pointer, text range, or archive member. Each reference pins both the Step-1
`SourceRecord.proof_hash` and the Step-2 `RawArtifactRecord.proof_hash`, so a
later metadata reclassification or custody-record change cannot silently alter
the provenance of a normalized fact.

Step 2 still performs no web retrieval and creates no normalized trade facts.


## Step 3 — canonical case layer

The case layer unifies multiple retained public artifacts around one historical
matter without turning case outcome into transaction truth.

A `HistoricalCase` contains:

- stable case identity and title;
- event type and information origin;
- proceeding status;
- named parties with explicit roles;
- issuers with optional historical CIK/ticker;
- exact proof-pinned raw-artifact references;
- optional complaint/opened and resolution dates.

Discovery-only sources cannot establish case content. Academic sources must remain
labeled `ACADEMIC_RECONSTRUCTION` and cannot masquerade as SEC/DOJ/court
artifacts.

Case proceeding status is deliberately separate from the fact status introduced
in Step 5. A settled or adjudicated case does not automatically prove every
individual allegation or transaction detail.


## Step 4 — sparse transaction schema

Historical transaction rows are deliberately sparse and provenance-bound.

A transaction must point to:

- an existing canonical case and exact case proof hash;
- a trader/party already present in that case;
- an issuer already present in that case;
- an exact retained artifact reference already linked to that case.

Trade timing may be represented as one exact timestamp, one date, or one date
range. The schema does not collapse ranges into guessed dates.

Price, quantity, profit, side, instrument, ticker, currency, exit data, and
option terms remain nullable/UNKNOWN when the public record does not establish
them. Numeric values are preserved as plain decimal strings rather than binary
floating-point values.

A transaction cannot be registered when its case proof, party, issuer, source
proof, artifact proof, or case-artifact relationship does not match.


## Step 5 — mandatory fact status

Every normalized historical transaction now requires an explicit `FactStatus`:

- `ALLEGED`
- `ADMITTED`
- `SETTLED_WITHOUT_ADMISSION`
- `FOUND_LIABLE`
- `CONVICTED`
- `COURT_ESTABLISHED`
- `ACADEMIC_RECONSTRUCTION`

The status is separately provenance-bound through `status_ref`. This matters
when the transaction details come from one artifact (for example a complaint
table) while the legal/factual status is established by another artifact (for
example a final judgment).

The verifier prevents status inflation:

- complaints/indictments can support allegations, not a `FOUND_LIABLE` label;
- liability requires a judgment;
- conviction requires a judgment or plea/statement artifact;
- court-established facts require court judgment/exhibit evidence;
- academic reconstructions must remain `ACADEMIC_RECONSTRUCTION`;
- non-academic legal statuses require a primary public record.

Case-level proceeding status remains separate and cannot automatically upgrade
the status of any individual transaction.


## Step 6 — information events and public-release boundaries

The event layer separates the historical information event from trade rows.

Each `InformationEvent` binds:

- one canonical case and exact case proof;
- one or more issuers already present in that case;
- an event type and historical information summary;
- a required public-release boundary;
- an optional private-information start boundary;
- optional tip/transfer boundaries.

Temporal precision is explicit: exact timestamp, date-only, or date range. Coarse
dates/ranges are not silently promoted to exact times.

Public-release boundaries require a primary public record linked to the case with
the `PUBLIC_RELEASE` artifact role. New primary source types cover public filings,
issuer press releases, and public regulatory releases.

Where both sides have exact timestamps (or both are date-only), chronology is
validated so the private-information boundary cannot follow the public release.
Cross-precision cases remain coarse rather than being guessed.


## Step 7 — source-specific candidate extractors

Extractors are deliberately **candidate-only**. They cannot create canonical
transactions/events or approve their own output.

Implemented adapters include:

- SEC HTML text extraction;
- SEC PDF page-text candidate extraction;
- DOJ/court page-text candidate extraction;
- academic CSV and ZIP/CSV extraction;
- a dedicated `hacked_earnings_jfe` `TimeOfFirstTrade.csv` adapter using the
  real public headers `PERMNO,SYMBOL,GVKEY,TimeOfFirstTrade`.

Before extraction, every adapter re-verifies the registered source proof,
retained artifact proof, expected source family, and exact raw-byte SHA-256.
Academic ZIP extraction rejects traversal/encrypted/oversized members.

Each candidate preserves:

- exact source/artifact proof chain;
- source locator;
- extractor ID/version;
- raw excerpt hash;
- parsed field values and per-field parse state;
- warnings about important limitations.

PDF adapters consume separately supplied page text and explicitly mark it as
`PDF_TEXT_LAYER_NOT_RAW_VISUAL_VERIFICATION`; they do not OCR or claim visual
verification of the underlying PDF.

The hacked-earnings adapter explicitly marks its output as academic
reconstruction, retains the source's timezone ambiguity, and warns that
`TimeOfFirstTrade` is not complete trade economics.


## Step 8 — deterministic human review gate

Parser candidates remain non-authoritative until a reviewer approves the exact
normalized record hash.

A review item freezes:

- canonical case, trader and issuer identities;
- information-event identity;
- proposed trade timing and its precision;
- public-release boundary precision and proof hash;
- proposed legal/factual status;
- normalized quantity/price and the exact normalized-row proof hash;
- every candidate extractor/version, sub-document locator, public-source excerpt
  hash, parsed value and parse state;
- deterministic conflicts and blockers.

Candidate sub-locators (for example a PDF page/table row) are validated against
the same retained artifact as the canonical case link rather than requiring the
root locator itself to be identical.

Approval requires explicit human confirmation that:

1. source evidence was checked;
2. party/issuer identity was checked;
3. temporal precision was checked;
4. legal/factual status was checked;
5. conflicts are resolved.

Ambiguous or unparsed fields, conflicting parsed values, unverified PDF text
layers, unsupported academic promotion, and unresolved timezone/economics issues
block approval.

`HistoricalReviewQueue` is append-only at the decision level. Once a review
item has a completed decision, corrections require a new normalized proposal and
therefore a new review hash. Approved decisions bind the exact normalized row
hash and remain scoped to `HISTORICAL_RESEARCH_COMPLIANCE_ONLY`; they never
authorize live trading.



## Step 9 — durable entity resolution

Case-local party and issuer IDs are no longer treated as durable cross-case
identities.

The entity-resolution layer now provides:

- durable issuer identities;
- durable trader identities;
- provenance-bound names and aliases;
- historical CIK mappings;
- historical ticker mappings with optional validity intervals;
- explicit `RESOLVED`, `AMBIGUOUS`, and `UNRESOLVED` states;
- proof-pinned crosswalks from case-local `issuer_id` / trader `party_id` values
  to durable entity IDs.

Ticker reuse is date-sensitive. A ticker crosswalk requires an explicit
`as_of_date`; the resolver does not invent a date. Reused identifiers or shared
aliases remain ambiguous unless the supplied historical context uniquely resolves
them.

Durable identities and crosswalks are established only from admissible retained
public evidence. Discovery-only sources cannot establish a durable identity.

Crosswalks pin:

- the exact canonical case proof;
- the exact case-local ID;
- the exact durable entity proof;
- the exact resolution proof that produced the unique match.

Mappings are append-only for a given case-local identity. A mapping cannot be
silently redirected to another durable entity.

### Step-8 approval integration

Sparse transaction objects remain evidence-layer records and therefore continue
to use case-local IDs. The Step-8 acceptance boundary is stricter:

- a review item may attach a durable issuer/trader identity snapshot;
- historical-research approval requires both issuer and trader crosswalks;
- approval requires the current case/entity/crosswalk registries;
- each crosswalk is recomputed at decision time;
- a missing, changed, stale, unresolved, or newly ambiguous mapping fails closed;
- the approval decision binds the durable-identity snapshot hash in addition to
  the normalized transaction-row hash.

This means a case-local name or ID can still exist in pre-review evidence, but it
cannot enter the accepted historical research corpus unless both the trader and
issuer are uniquely resolved to durable identities at approval time.

The entity layer remains historical/public-record only. It does not authorize
live trading, ingest live confidential information, or turn ambiguous identity
evidence into a guessed match.



## Step 10 — source priority and conflict preservation

Contradictory public sources are now represented as separate, proof-pinned
claims instead of being overwritten during normalization.

The source-priority policy distinguishes:

1. court-established, convicted, found-liable, and admitted facts;
2. official settlement/non-admission status when the field being resolved is
   itself a legal-status field;
3. primary allegations in complaints, indictments, releases, orders, and
   supported exhibits;
4. primary records that do not establish the underlying fact, including
   settlement-without-admission evidence used for non-status fields;
5. published academic reconstructions;
6. discovery-only secondary sources.

This priority order is field-specific. A settlement without admission can
establish that the matter was settled without admission, but it cannot upgrade
an alleged quantity, price, timing, profit, or other trade fact into an
established fact.

### Contradiction preservation

Every registered claim remains in the conflict assessment, including claims below
the preferred authority tier.

The assessment records:

- each claim and exact source/artifact proof;
- its factual/legal status;
- its authority class and rank;
- whether it is eligible to establish a canonical value;
- the preferred value, when one exists;
- the claim hashes supporting that preferred value;
- every contradictory claim hash.

A higher-priority source therefore **does not erase** a complaint, academic
reconstruction, or secondary claim.

If the highest applicable authority tier itself contains different values, the
result is `UNRESOLVED_TOP_TIER_CONFLICT`. No preferred value is produced.

Discovery-only evidence is retained for audit/discovery context but produces
`NO_CANONICAL_SUPPORT` when it is the only evidence available.

### Append-only conflict registry

`SourceConflictRegistry` is append-only by claim ID. A registered claim cannot
be rewritten under the same ID with different content.

The registry supports deterministic per-case/per-field assessments and has its
own order-independent proof hash.

### Review-gate integration

Step 10 extends the Step-8 acceptance boundary.

For new historical-corpus approvals:

- the review item must contain a source-conflict registry snapshot, even if the
  registry currently contains no relevant contradictions;
- relevant registered claims are assessed for every proposed normalized field and
  for `fact_status`;
- an unresolved top-tier conflict adds
  `SOURCE_CONFLICT_UNRESOLVED:<field>`;
- evidence with no canonical support adds
  `SOURCE_NO_CANONICAL_SUPPORT:<field>`;
- a proposed value that differs from the policy-preferred value adds
  `SOURCE_PRIORITY_MISMATCH:<field>`;
- a lower-priority contradiction may resolve a parser-level `CONFLICT:<field>`
  blocker only when the source-priority assessment has a unique preferred value
  and that value exactly matches the proposed normalized value.

The contradictory claims still remain attached to the review item and rendered
in the review report.

Approval re-evaluates the current conflict registry. If a new relevant claim was
registered after review-item creation, or an assessment otherwise changes, the
old review item fails closed as stale and must be regenerated/reviewed.

Approved decisions bind a source-conflict snapshot hash alongside the normalized
row hash and durable-identity hash.

As in all earlier steps, this remains limited to historical, already-public
research/compliance use. It never authorizes live trading or ingestion of live
confidential information.



## Step 11 — economic transaction deduplication

Approved historical source rows can now be compared as possible descriptions of
the same underlying economic transaction without deleting or collapsing their
source provenance.

### Source-independent signatures

Only rows already approved for the historical research corpus can produce an
`EconomicTransactionSignature`.

The signature uses:

- durable trader identity;
- durable issuer identity;
- information-event identity;
- instrument and side;
- exact timestamp, date, or date-range precision;
- currency;
- quantity;
- execution price;
- option strike and expiry when present.

Source IDs, artifact references, local trade IDs, and review IDs do not determine
the source-independent economic key. They remain separately bound in the
signature proof so the original source rows stay auditable.

Decimal strings are canonicalized for comparison, and exact timestamps are
compared as UTC instants so equivalent timezone offsets do not create false
differences.

### Conservative match states

Pairwise comparison returns one of:

- `EXACT_MATCH`;
- `POSSIBLE_MATCH`;
- `DISTINCT`;
- `INSUFFICIENT_INFORMATION`.

An automatic exact match requires:

- the same durable trader;
- the same durable issuer;
- the same information event;
- the same exact trade instant;
- matching instrument;
- matching side;
- matching quantity;
- matching execution price;
- no known contradictory economic field.

Coarse date/date-range overlap, missing economics, or unknown values never become
automatic duplicates.

### Economic cluster registry

`EconomicClusterRegistry` groups approved signatures while preserving every
normalized row as an individual member.

A new row auto-joins a cluster only when it is `EXACT_MATCH` against **every
existing member**. This prevents unsafe transitive merging.

Rows that are possible or insufficient matches remain in separate clusters and
generate deterministic `DedupReviewCandidate` records.

Partial-exact situations, where a new signature exactly matches only some members
of a cluster, also remain separate and require review.

Every registration and cluster change is proof-hashed and recorded as an event.

### Human dedup resolution

A reviewer may resolve a pending candidate as:

- `CONFIRMED_SAME_TRANSACTION`; or
- `CONFIRMED_DISTINCT`.

Same-transaction decisions consolidate the two active clusters while retaining
all source-backed signatures and normalized row hashes.

Distinct decisions leave the clusters separate and record permanent pairwise
distinct constraints across the reviewed source and target clusters.

Those confirmed-distinct constraints cannot later be bypassed through an indirect
manual merge.

A dedup candidate cannot be decided twice. Review timestamps must be
timezone-aware and a rationale/reviewer ID are mandatory.

If the target cluster changed after the candidate was generated, the old review
candidate fails closed as stale.

Related pending candidates are superseded when a human resolution changes or
adjudicates the relationship between their clusters.

### Review visibility

`render_dedup_review_candidate_markdown` presents the candidate reason and every
pairwise assessment, including agreeing, differing, and missing fields, without
hiding uncertainty.

The deduplication layer is historical/public-record research infrastructure only.
It does not authorize live trading, use live confidential information, or delete
the original SEC/DOJ/court/academic evidence rows.



## Step 12 — graph-aware historical surveillance

The accepted historical corpus now has a deterministic relationship graph for
retrospective compliance/surveillance research.

The graph contains four node classes:

- durable traders;
- durable issuers;
- information events;
- deduplicated economic transactions.

Each economic transaction is connected to its durable trader, issuer, and event.
Multiple SEC/DOJ/court/academic rows that Step 11 confirmed as one economic
transaction remain preserved inside that cluster; the graph does not duplicate
them into separate economic nodes.

The graph exposes deterministic, provenance-preserving relationship features such
as:

- trader degree;
- distinct historical event count per trader;
- distinct trader count per issuer;
- connected components;
- source-cluster membership.

Malformed clusters spanning multiple durable traders, issuers, or events fail
closed rather than being coerced into one graph node.

This graph is historical/public-record only and has no live-feed or trading
authority.


## Step 13 — leakage-conscious surveillance features

Step 13 derives transparent surveillance features from:

- the Step-12 graph;
- the Step-11 economic cluster;
- the Step-6 public-release boundary.

The feature vector includes:

- source-row count;
- repeated historical event count for the durable trader;
- issuer network breadth;
- connected-component size;
- instrument and side;
- exact or coarse trade timing;
- public-release timing;
- exact lead seconds when both trade and release timestamps are exact;
- conservative lead-day bounds for coarse dates/ranges;
- consensus currency, quantity, and execution price;
- deterministic notional when quantity and price agree;
- multi-source corroboration.

Later outcomes are deliberately excluded. The feature body does **not** include
conviction, settlement, judgment, proceeding status, later documented profit, or
other post-event enforcement facts.

When source rows inside a human-confirmed economic cluster disagree on a field,
that field becomes unknown/nullable in the feature vector rather than being
silently averaged or guessed.


## Step 14 — point-in-time controls and walk-forward windows

Step 14 prevents graph and feature leakage from future historical records.

A point-in-time cutoff can be:

- an exact timestamp; or
- an end-of-day date.

For an intraday exact cutoff, same-day date-only and date-range rows are excluded
because their full-day information was not yet safely available at the cutoff.

A cluster is usable only when **all** of its preserved source signatures are
available by the cutoff.

A `PointInTimeFeatureSnapshot` binds:

- the target cluster;
- the cutoff;
- the exact eligible-cluster set;
- every excluded future cluster;
- the point-in-time graph hash;
- the derived Step-13 feature hash.

Walk-forward windows freeze a training cutoff and a later evaluation cutoff.
Training rows are those available by the training cutoff. Evaluation rows are
newly available after training and by the evaluation cutoff. The two sets cannot
overlap.

`PointInTimeControlPlan` supports ordered, deterministic control-date schedules,
including large historical control-date grids.


## Step 15 — retrospective benchmark harness

Step 15 adds a deterministic historical-only scoring and evaluation framework.

`RetrospectiveScoringPolicy` uses transparent signals such as:

- exact pre-publication timing;
- coarse pre-publication timing;
- repeated historical trader-event exposure;
- issuer network breadth;
- a configurable large-notional threshold.

Every score includes its complete signal breakdown. The policy and receipts
explicitly keep `live_use_allowed=False`.

Outcome labels are separate from features. Labels may be used for retrospective
evaluation, but no later legal/enforcement outcome enters the Step-13 feature
vector.

Threshold fitting is training-only:

1. score the frozen training examples;
2. evaluate deterministic candidate thresholds;
3. choose the best training balanced accuracy with a deterministic tie-break;
4. freeze the threshold in a proof-hashed receipt;
5. evaluate the untouched holdout set using that frozen threshold.

The holdout evaluation records:

- true positives;
- true negatives;
- false positives;
- false negatives;
- sensitivity;
- specificity;
- precision;
- balanced accuracy.

The walk-forward benchmark verifies that every training and evaluation example
belongs to the correct Step-14 partition and that no snapshot reads beyond its
allowed cutoff.

Steps 12–15 remain limited to retrospective, already-public compliance research.
They do not ingest live confidential information, produce live alerts, authorize
trading, or generate orders.
