# RETALLY Unified Research Lab

**Mission:** concentrate discovery and evidence quality primarily on **FreightRecovery**
(real freight invoices, tariffs, adjudicated rate rules and source-backed overcharge
validation), while retaining bounded PermitPlate, CaptureBrief and RecoveryOS
research and the strongest already-approved read-only regression suites.
Source pointers alone never count as independently validated claims.

## One operating model

- **One automatic research controller:** .github/workflows/retally-unified-research-lab.yml.
- **One long-lived data branch:** research/retally-unified-data-lab, separate from protected main and production sites.
- **One canonical cross-engine catalog:** freight/research_lab/leads.json; exact URL deduplication and engine tags preserve the source's original first-seen date.
- **FreightRecovery-first four-lane discovery, not four independent workers.** The nominal five-minute GitHub scheduler favors FreightRecovery for **7 of every 10 planned slots** and reserves one slot each for PermitPlate, CaptureBrief and RecoveryOS. The independent Cloudflare Worker weights FreightRecovery's elapsed-time priority to yield about **70% of sustained successful discovery cycles** while explicitly backfilling overdue secondary lanes. Actual proportions vary with missed triggers, provider failures and catch-up. Neither service guarantees a five-minute execution SLA or meaningful new evidence on each scan.
- **One nightly read-only test campaign:** real original freight invoices, RecoveryOS general-AP disclosures, PermitPlate official-source adapter regressions, and CaptureBrief procurement-source regressions.
- **Legacy Lab 15 source discovery preserved:** the two original metadata harvesters are run **inside the central controller** when FreightRecovery's periodic legacy refresh is due; their two legacy ledgers remain historical/compatibility views on the *same* data branch. Their independent scheduled triggers are retired, not their test code.
- **Existing Labs 1–14 kept intact:** their research findings, adversarial cases and stacked draft PRs are not silently declared merged, green or production-authorized. The synthetic 14-domain test director in PR #297 is a separate unmerged draft with explicit non-merge limitations. Port each validated, read-only harness into the nightly controller only when it exists on approved main; never transplant unfinished stacked branches into production.

## FreightRecovery evaluation-feed integration (v1.1)

**Integrated with the existing research controller, not a 16th lab or separate scheduler.**

On each five-minute discovery/dispatch run, the controller validates and
deduplicates source links from **all three catalogs**:
`freight/research_lab/leads.json` (four-engine canonical catalog),
`freight/lab15/evidence_ledger.json` (original evidence finder), and
`freight/research/lab15_candidate_ledger.json` (original source candidate lab).

A deterministic bridge (`freight/research_eval_bridge.py`) builds
`freight/research_lab/evaluation_feed_v1.json` **on the isolated research data
branch only**. Sources remain versioned, exact-URL deduplicated, provenance
tracked, first-seen-preserving, and rights-/truth-held. Rebuilding the same inputs
produces unchanged bytes. Invalid or non-representable legacy URLs are counted
as skipped; a bounded execution cap is reported, never silently treated as a
complete population. No private invoice identifiers, source body text, titles,
original public document bytes or payment records are copied into the feed.

The frozen nine-case `freight/fixtures/real_world_eval_v1.json` remains an
independent, reviewed fixture: seven **official** decision/SEC/STB/EIA pointers
are deliberately seeded into the unified catalog and crosslinked by exact URL.
Two private-party invoice faces remain in the frozen evaluation regression
suite; their document-specific URLs are **not** harvested or republished.
Additional candidate sources enter the **unlabeled source queue**, not the
curated invoice/overcharge population.

Every selected feed pointer is replayed through
`freight.canonical_schema`, `freight.rating_engine`, and
`freight.priority2_evidence` using a deliberately fabricated $1, no-authority,
no-shipment-document record. A source pointer alone must produce
`REVIEW_REQUIRED` and zero verified cash. This is a real **engine evidence-gate
test** using real source locators, **not** a fresh numerical invoice
extraction/rerate test. The fixed v1 pack separately retains original
public-domain numerical anchors and actual invoice-face arithmetic.

The existing read-only nightly four-engine runner now reads the **current
source-data branch**, validates and regenerates the feed, and replays both the
dynamic candidate proof gates and the frozen v1 tests. The first merge to
protected main additionally **bootstraps the isolated feed branch offline**
from official seeds; a successful push does not prove five-minute scheduled
discovery has executed. Subsequent cron/live discovery is independent and may
be delayed/skipped by GitHub.

Run locally without credentials or live source acquisition:

    python -m unittest -q freight.test_unified_research_lab freight.test_research_eval_bridge
    python -m freight.research_eval_bridge --output /tmp/evaluation_feed_v1.json
    python -m freight.research_eval_bridge --output /tmp/evaluation_feed_v1.json --verify
    python -m freight.real_world_eval_v1

**Research candidate != verified benchmark truth.** Promotion to a new
curated numerical case requires authentic source custody, permission review,
independent governing customer contracts, shipment support and payment/credit
evidence. Real recovered cash, customer precision/recall and externally
approved claims remain **zero or not estimable**, regardless of feed growth.

## Real-data research targets

| Lane | Discovery and validation |
| --- | --- |
| FreightRecovery | Official GAO adjudications; public invoice exhibits; freight-rate documents; Data.gov, Zenodo and public GitHub dataset *catalogs*. Nightly original GlobalTranz and ArcBest document replay using existing ingestion, rating and reconciliation paths. |
| PermitPlate | NYC DOB NOW **job applications**, DOB NOW **approved permits**, and BIS-only **permit issuance** are separate official source families with distinct coverage and timing. Keep restaurant inspections and dining-out registrations out of the DOB permit-issuance evidence population; never treat an application as an issued permit. Replay the existing official NYC building-permit adapters without asserting independent issuance labels or commercial reuse rights. |
| CaptureBrief | SAM.gov opportunity and amendment sources, federal procurement archives and USAspending award data; existing historical/current-source controls. Current SAM API access requiring a key is not assumed. |
| RecoveryOS | Original published vendor-payment and invoice disclosures, especially Pennine Care NHS spending CSVs, plus public procurement/payment metadata; nightly replay through the existing RecoveryWorks reconciliation kernel. |

### Verified public catalog APIs (October 2026)

- The former Data.gov CKAN v3 endpoint is **retired**. The documented replacement is the GSA Data.gov v4 metadata API, which requires an API key in production. This worker uses it only if the optional `RETALLY_DATAGOV_API_KEY` GitHub Actions secret exists; it never uses `DEMO_KEY` for automation.
- Without that key, continue unattended via public GitHub/Zenodo metadata search. PermitPlate also checks the official NYC Socrata public dataset catalog. Only public dataset links/IDs are stored, not records, titles, invoice rows, contacts or login details.
- Per-provider errors are recorded as bounded local error codes (e.g., HTTP_STATUS_404) without exposing private API responses. Partial provider success is displayed as a warning, not falsified full coverage.
- Rebuild the legacy Lab 15 triage queue on every run before git staging. It is a derived view and is absent on a fresh branch until first generated; treating an absent optional file as a mandatory git path caused the first real run to fail.

### Source promotion rules

A public link is only a **candidate**. Discovery itself does not fetch/save
third-party document bytes or invoice line items; it stores fixed-format source
URLs and source tags, never arbitrary titles, accounts, emails or private cases.
Existing nightly original-document tests use ephemeral memory/runner-local files
and do not upload customer material or extracted rows. Each candidate remains
rights-**unverified**, truth-**unverified**, and commercial-reuse-**unapproved**;
even a SHA-256 match does not prove an invoice error.

For a meaningful blinded accuracy benchmark require *independent* original
invoice, historical buyer-specific rate authority, shipment/BOL facts,
payment/credit chain, and adjudicated positive **and clean negative** outcomes.
The existing public original-document laboratory does not yet possess that
complete linkage. No accuracy, recovered dollars or superiority may be asserted
from an incomplete source.

### Execution and integrity

Run offline/adversarially from repo root:

    python -m unittest -v freight.test_unified_research_lab
    python -m freight.unified_research_lab --engine freightrecovery

Fetch bounded public metadata manually, if needed:

    python -m freight.unified_research_lab --live --engine capturebrief

The **only** automatic writer stages freight/research_lab/leads.json, the
versioned freight/research_lab/evaluation_feed_v1.json, both Lab 15 metadata
ledgers and triage output. It cannot modify
protected main, website pages, engine code, sales/claim data, customer inbox,
Stripe, private PermitPlate source state or CaptureBrief private archives.
Writes use serialized GitHub Actions, no force push, no source document uploads,
no customer/prospect/carrier outreach, and no paid API or paid infrastructure.

Offline adversarial tests defend against ledger manipulation, forged rights and
cash assertions, injection URLs, duplicates, rerun drift, partial source
failures, and wrong engine rotation. Source API outages must surface as workflow
failures or explicit provider errors; zero new leads by itself is not success
proof, accuracy evidence, nor an excuse to manufacture data. Research discovery
may produce many **leads** while yielding zero independently labeled cases.

### Independent scheduler fallback (Cloudflare)

GitHub Actions `schedule` events may be delayed or never emitted even when push CI
passes. The same single RETALLY research operation therefore has an independent,
bounded Cloudflare Cron collector. It is **not** a sixteenth research lab and
never touches customer, production money, hosted RecoveryOS, or other Workers.

- Worker source: `freight/research_lab_worker.mjs`; executable tests:
  `freight/research_lab_worker.test.mjs`; dedicated D1 schema:
  `freight/research_lab_worker.schema.sql`.
- Every five minutes, Cloudflare uses a **weighted elapsed-time** selector:
  FreightRecovery receives priority 10 versus 1 each for the three secondary
  engines. In sustained simulated operation this gives approximately 70%
  FreightRecovery runs, while an overdue secondary lane eventually overrides
  FreightRecovery to avoid starvation after missed triggers. Provider-search
  plans and bounded candidate windows advance per five-minute slot rather
  than repeating the same twenty-minute window during consecutive freight
  cycles. No additional provider calls are made per cycle.
- It fetches only public GitHub/Zenodo and official NYC Socrata *metadata*,
  bounds response sizes and source count (24 per run), canonicalizes URLs,
  and deduplicates them in its own D1 store. It does not fetch original invoice
  bytes, scrape restricted sites, send messages, or use commercial data APIs.
- D1 rights/truth-state fields are CHECK-locked to UNVERIFIED. Only public URL
  pointers and per-engine counts can leave that store. No independent accuracy
  or recovered cash assertions.
- Cron invocation is idempotent per five-minute UTC slot and lane; duplicate
  triggers cannot inflate source rows. Stale-data detection is weighted-policy
  aware: 45 minutes without successful FreightRecovery discovery, or 120 minutes
  for a lower-frequency secondary lane, is flagged as stale. HTTP endpoints
  are **read-only**:
  `/health` reports aggregate status and `/feed?engine=...` reports bounded
  metadata URLs. No public action can trigger a write.
- Hosted within the existing Cloudflare account and without upgrading its
  plan. Worker subrequests and D1 writes are capped to fit included usage.
  The independent service stores pointers durably when GitHub cron is absent;
  GitHub's source branch remains the governed publication mirror when its
  own runner executes. Each GitHub discovery first reads the Cloudflare
  metadata-only `/feed` for its chosen engine, checks the exact scope/engine,
  validates each URL against the source-host allowlist, and merges it into the
  source-held ledger. No claim of real-time perfect mirroring: if GitHub
  scheduling is absent, Cloudflare remains the durable live discovery store
  until a main-branch or scheduled GitHub run resumes.

### Operational acceptance and recovery

- On first merge or subsequent updates to the controller, a main-branch push also performs **one real live discovery and one complete four-engine read-only replay**. A passing PR test alone does not prove the live lab is healthy.
- Require a successful GitHub Actions **discover** job, a four-engine source coverage summary and a successful safe push to research/retally-unified-data-lab. Check for actual candidate changes; zero new leads can be a valid no-op but a stale job is not healthy.
- Require the separate **nightly-real-data-replay** job to pass; a failed original-document URL, parser, official source change, or engine test is a genuine blocked acceptance gate, not a reason to suppress that test.
- The 5-minute cron may be delayed or skipped by GitHub. The offset cron is intentionally changed in this repair to renew its associated scheduling actor; main push is an independently verifiable bootstrap, not a replacement for recurring cron proof.
- Do not claim the lab is continuously healthy until at least one actual **schedule** event has succeeded; if that continues to be unavailable, another authorized independent scheduler is needed.
- Every successful discovery emits an Actions job summary with counts per engine, new pointers, and public provider errors. Original documents, sensitive source details, and customer information never enter those summaries.

### Migration

1. Merge the unified controller only after its PR checks pass; GitHub Actions
   cron runs only from the default branch.
2. Remove the *schedules* from the two old Lab 15 workflows while keeping their
   explicit dispatch and PR tests. Preserve all old history and ledgers.
3. Verify the first five-minute source branch publication and first nightly
   engine replay; correct real source access failures instead of lowering
   evidence controls.
4. The long-lived isolated branch becomes the one research data store. Pending
   14-lab synthetic and adversarial PRs remain review-only until their
   dependency chains and safety gates are resolved.

**Hard boundaries:** no self-authorization of licenses, customer documents,
bank proofs, rate authority, commercial claims, fee actions or external
communications. Automation can run independently without making up permissions,
ground truth or results.

## Quality observability and publication verification (v1)

The controller publishes `freight/research_lab/source_health_v1.json` to
the **research data branch only** alongside the source catalog. The report is
deterministically generated by `python -m freight.research_lab_health` and
verified against the exact catalog SHA-256, both before publication and during
nightly original-document regression. A push-triggered nightly replay **waits**
for the source-branch writer to succeed, avoiding the prior risk of testing a
stale branch or a missing new receipt. Standalone nightly cron still runs.

This compact aggregate report distinguishes:
- Total unique public URL references from engine assignments (cross-engine
  overlap is never counted as an independent additional document).
- Official-publisher **host** references from GitHub/Zenodo and other
  allowlisted host references. An official host is not verification of a
  document's content, licensing, provenance, numerical truth or suitability.
- Clearly suspicious PermitPlate wrong-topic URL tokens for **review only**.
  These flags never delete historical references or establish an independent
  label; full PermitPlate candidate governance is a separate decision.
- Observed first-seen date counts (not source content, extraction coverage or
  independently validated source freshness).

No original third-party bytes or candidate titles, person records, source
URLs, private documents, customer money or synthetic-replay output enter the
published quality receipt. Its commercial and independently verified evidence
counts remain zero. The independent Cloudflare D1 collector remains the
five-minute discovery source; this report makes the *GitHub branch state*
inspectable without claiming it represents every missed schedule.

Manual offline reproduction, **without network or paid services**:

    python -m unittest -q freight.test_research_lab_health
    python -m freight.research_lab_health --output /tmp/retally-source-health-v1.json
    python -m freight.research_lab_health --output /tmp/retally-source-health-v1.json --verify

## Independent scout resource efficiency (v2)

The independent Cloudflare collector keeps the **same** existing
`*/5 * * * *` Cron trigger, D1 database, approved read-only GET routes,
three public metadata providers and maximum 24 processed links per cycle.

- Public GitHub/Zenodo search terms and pages 1/2/3 rotate deterministically,
  including one newest-first GitHub search per five lane attempts. This covers
  12 bounded query/page/sort views without increasing the three core provider
  requests, introducing any new credentials or fetching source-document bytes.
  Partial search misses still produce explicit provider warnings.
- A GitHub HTTP 429 skips the second same-origin GitHub call for that cycle,
  reducing pressure during a rate limit. Provider diagnostics consist only
  of bounded non-identifying status codes; raw exception text is never
  persisted to D1.
- A stream reader enforces the 1.2 MB provider response cap **in bytes**
  even when `Content-Length` is absent; oversized responses are cancelled
  rather than loaded as complete strings.
- The up-to-24-rights-held public URL pointers and their engine associations
  are inserted through one D1 `batch` transaction containing two prepared,
  parameter-bound SQL statements instead of up to 48 separate round trips.
  If either statement fails, no partial source/association pair is committed;
  the Cron run records a failed storage state where D1 remains reachable.
- `GET /health` additionally returns metadata-only 24-hour per-engine run,
  error and discovery counts plus per-engine source associations. These are
  operational counters, **not** verified benchmark evidence.

All candidate URLs remain unverified and require independent original data,
rights, authority and outcome evidence before usage as a benchmark or
commercial claim. This change does not change existing billing plans or
permissions, nor introduce a deployment or API-secret requirement.

## Cursor-paginated Cloudflare-to-GitHub publication (v3)

Each GitHub discovery execution mirrors the four Cloudflare source lanes from
the existing read-only endpoint `/feed?engine=...`, now with an opaque
`before` cursor. Cloudflare continues to preserve newest-first source
ordering while permitting older entries to be read across pages. Only the
public URL and its original observed date are returned; the internal D1
row ID is used for paging and is **not** returned as a source field.
The previous unpaginated endpoint continues to work for clients.

The GitHub publication worker reads up to **6 pages of 100 URL pointers per
engine**, with fixed cursor validation and no new scheduled jobs. At most
40 newly admitted pointers per engine are committed per GitHub execution,
preserving the original source-branch write bound. Every candidate remains
unverified for commercial rights, original-document custody and independent
ground truth; old historical records are not discarded. If the page cap is
reached, or a cursor is malformed, a bounded per-engine error is recorded.
Wrong-engine responses and malformed dates fail closed without overwriting
the existing ledger. Provider / mirror issues remain visible; a successful
job is not a blanket guarantee of source suitability.

This change is only for **public metadata readback and research branch
publication**: the Cloudflare five-minute Cron, D1 schema and bindings,
all production environments, external customer communications, and
existing nightly original-document tests remain unchanged.

## Four-engine source review priorities (v4)

The existing unified discovery job also writes
`freight/research_lab/source_review_queue_v1.json` on its isolated
`research/retally-unified-data-lab` branch. This is a **bounded source-review
queue**, not a fifth engine, a new research controller, or a numerical
benchmark. It adds no network requests, paid API dependencies, new Cron
triggers, customer outreach, original-document downloads or engine writes.

Each of the four lanes receives up to **8 ranked public URL references**,
with stable source IDs, first-observed dates, a SHA-256 receipt pinned to the
canonical source ledger, and explicit evidence gaps. The ranking is a
conservative review order: previously identified official publisher URLs,
then other official publisher hosts, then third-party repository names with
a matching URL-only keyword, then unclassified archive pointers.
**An official publisher host is not proof of source content, data rights,
original source custody, buyer-specific rate authority, independent truth
or available recovery dollars.** URL-only topic signals never become
independent positive/negative test labels or commercial authorizations.

Historical unrelated PermitPlate restaurant-inspection URLs are counted
but excluded from the **review queue only**; the original immutable catalog
and its first-observed dates are preserved. The current PermitPlate DOB
application-versus-issued-permit caveat is not erased by this ranking.

Nightly replay verifies the queue against the exact data-branch ledger
after verifying the source-quality receipt, original freight source
regression, and the other engines' adapter controls. A drifted hash,
promoted permission, forged ground-truth flag or missing queue blocks
acceptance. The queue describes **what evidence is missing** for valid
engine accuracy tests; it does not pretend that references alone are
reusable test cases.

Offline, read-only reproduction:

    python -m unittest -q freight.test_research_source_review
    python -m freight.research_source_review --output /tmp/retally-source-review-queue.json
    python -m freight.research_source_review --output /tmp/retally-source-review-queue.json --verify

## Source-topic admission screening (v5)

The independent Cloudflare scout and the GitHub discovery runner now use
the **same conservative four-engine topic lists** to screen metadata from
GitHub and Zenodo before accepting any *new* URL pointers. GitHub
repository name/description and Zenodo record title are inspected in
memory only, limited to 512 characters per field; the source catalog,
D1 and action logs still contain **only canonical allowlisted URLs**,
first-seen dates, engine names and fixed non-sensitive result codes.
Raw titles, descriptions, authors, contacts, invoice contents and source
document bytes are never persisted.

For PermitPlate, the rules require DOB, building-permit or permit-issuance
terms and reject restaurant-inspection context even when the word
"permit" also appears. All lanes reject obviously unrelated catalog
records and metadata lacking a useful topic signal. This does not inspect
or silently erase previous unverified leads. Existing historical records,
the PermitPlate wrong-topic quarantine fixture and their original
first-seen dates remain unchanged.

The **official NYC Socrata DOB catalog source filter is preserved**.
The optional Data.gov v4 lookup remains subject to the original
public-access-level check and production API-key requirement. No new
APIs, additional provider calls, secrets, timers, workers or billing
are introduced. Metadata-based similarity is a conservative
*screening heuristic*, not a human-reviewed truth label, a guarantee
that a document exists, or commercial-use permission. It can have
false positives and false negatives. A zero-new-lead cycle is
acceptable when requests and source safety checks succeed, not proof
that further real data does not exist.

Both collectors include adversarial regression cases for each of the four
engines, with aligned positive/off-topic metadata fixtures, missing
publisher titles, unsafe IDs and sensitive description text that must
never be copied to the ledger.

## Publisher response and evidence provenance gate (v6)

The existing unified controller now performs a **real read-only public-origin
probe** of up to nine pinned official source URLs across all four engines.
Its output, `freight/research_lab/publisher_provenance_v1.json`, is written
only to the isolated `research/retally-unified-data-lab` branch alongside
the previously versioned source review and evaluation receipts.

A source is probed only when it appears in the validated canonical ledger,
is associated with its original engine lane and is explicitly pinned by
the existing `PUBLIC_REVIEW_ANCHORS` policy. Requests are HTTPS,
public-DNS checked, redirect-blocked, bounded in time, and restricted to
the pinned publisher URLs. **No GitHub or Zenodo third-party candidates
are downloaded** by this provenance stage. For each fixed publisher URL,
a HEAD observation records a status code and fixed media-class category.
Only when HEAD succeeds, the content class is explicitly allowed and the
declared source size is at most 256 KiB does an optional GET read at most
256 KiB + one sentinel byte. A SHA-256 fingerprint is recorded **only**
for the complete bounded original HTTP response. Oversized, redirected,
unavailable or unsupported sources are reported with separate fixed
reason codes, not truncated or falsely fingerprinted.

All actual publisher content is ephemeral; never upload source bodies,
invoice faces, contact information or arbitrary headers. The persistent
receipt contains immutable source IDs, fixed publisher hosts, first-seen
dates, observation outcome/status, an optional SHA-256, and bounded
diagnostics. Its own digest and each observation are validated
adversarially, including fail-closed rights, outcomes and cash assertions.
For the same UTC date and unchanged pinned source set, the live process
reuses its receipt without extra publisher requests; a changing unrelated
catalog does not force a refetch. Receipts older than two days fail
verification rather than claiming ongoing freshness.

**Scope distinction:** HTTP 200 means the pinned public URL responded
with metadata during this probe; a complete-response SHA-256 is a
fingerprint of the bytes received, **not** an official digital signature,
original-invoice chain of custody, legal reuse permission, customer-specific
governing contract, independent positive/negative adjudication, or
confirmed cash recovery. The engine evidence/benchmark readiness, rights
and independent labels remain false/zero until actually supported.
No source is automatically admitted as commercial benchmark truth.

The existing nightly read-only four-engine replay now checks the exact
publisher provenance receipt against the research data branch before
evaluating original invoice/engine fixtures. There are no new Cron jobs,
Workers, D1 mutations, paid services, outbound sales activity, or engine
production changes. Offline adversarial tests simulate publisher errors,
tampered proof flags, forged hashes, redirects and large responses; they
perform no real public-network calls.

Run without network access for safety testing:

    python -m unittest -v freight.test_research_publisher_provenance

Run only on the approved isolated research branch with existing public
publisher access:

    python -m freight.research_publisher_provenance --live
    python -m freight.research_publisher_provenance --verify

### Next required evidence before accuracy benchmarking

- Confirm source terms and intended commercial reuse for **each specific
  dataset**, not from host identity or HTTP accessibility.
- Obtain/verify complete underlying original artifacts and governing source
  authority appropriate to the engine and its original time window.
- Link results to independently determined positive **and** negative
  outcomes; train/test leakage and as-of-date chronology must be excluded.
- Keep unknown labels **UNKNOWN** and commercial authorization **FALSE**
  until each separate requirement is evidenced, not inferred by a model.

## Official issued-permit original-row replay (v7)

An additional **read-only real source replay inside the existing controller**
uses the official NYC Open Data DOB NOW: Build – Approved Permits dataset
`rbx6-tga4` (publisher:
`https://data.cityofnewyork.us/d/rbx6-tga4`). It exercises the published
JSON record schema using *only* job filing, tracking number, work permit,
sequence, issue date and permit-status fields. No owner name, address,
contractor identity, contact, original row or other sensitive source field
is retained in the research branch.

The daily sample is capped at 20 dated original published records. Three
sampled tracking numbers are separately re-read from the **same original
publisher source**, with URL/SoQL allowlisting, strict source identity,
read-only HTTPS/redirect protection and a 160-KiB response cap. The derived
source receipt records sampled count, exact second-read matches,
conflicts/missing records, non-issued placeholder counts, and SHA-256 of
only the selected canonical sample fields. The source records and
identifiers themselves remain ephemeral. Duplicate tracking numbers are
not assumed to be unique permit IDs: multiple work permits and sequences
may belong to one tracking number. Furthermore, NYC can publish repeated
rows with the **same full composite permit identity**. These are preserved
in raw sampled-row counts but are never counted as distinct verified
permits; their multiplicity is separately reported as a source-quality
warning. Exact duplicate identities are excluded from individual
readbacks and cause DEGRADED rather than a false-green or an entire
lost discovery cycle. A saturated publisher readback page is explicitly
AMBIGUOUS, while a second-query timeout preserves the original-row
sample and records the error. A work-permit placeholder saying
"Permit is not yet issued" does not become a positive issued-permit case
simply because a source row has a date.

This checks **publisher consistency**, not a separate independent
government adjudication: issuance source records, historical filing
status, operational demand, buyers' purchasing intent and awarded
contracts are materially different facts. The source receipt therefore
preserves all commercial source-rights and independent outcome gates.
The user's asserted broad commercial reuse rights are recorded as
`OWNER_ATTESTED_NOT_SOURCE_VERIFIED` without forging signed or
source-specific permission evidence; source-specific rights remain
unverified by this controller. The official NYC Open Data FAQ states
that the open data is generally available for unrestricted use; individual
dataset terms and non-public material are not retroactively cleared by
that general statement:
`https://www.nyc.gov/opendata/get-started/FAQs`.

On source outages the replay records **DEGRADED**, not fake positives or
no-records-found claims. Source schema changes, duplicate full source
identity collisions, forged commercial rights or tampered receipts
block the research workflow. A successful limited publisher readback
remains separate from independently held-out opportunity accuracy.

The output is staged **only** on
`research/retally-unified-data-lab` as
`freight/research_lab/official_nyc_issued_permit_replay_v1.json`.
Every post-publish nightly replay verifies it against that exact source
branch before exercising the four independent engines. No extra Cron,
Worker, paid service, customer contact, billing or engine production
mutation is introduced.

Offline tests:

    python -m unittest -q freight.test_official_nyc_issued_permit_lab

Public read-only source probe (inside existing GitHub discovery only):

    python -m freight.official_nyc_issued_permit_lab
    python -m freight.official_nyc_issued_permit_lab --verify

## CaptureBrief official USAspending award-row readback (v8)

CaptureBrief now has an original federal contracting record readback inside the
**existing unified controller**. It queries the public USAspending
`/api/v2/search/spending_by_award/` publisher service using a strictly
fixed original award type population (A/B/C/D), the completed federal
FY2026 award period (2025-10-01 through 2026-09-30), bounded 12-row sample,
and at most two separately scoped exact award-ID re-queries. Search POSTs
are **read-only** to the official publisher, do not require credentials,
and never contact contractors, agencies or private parties.

The runner parses only original public publisher award ID/internal ID,
published award amount, generated internal ID and base obligation date.
It checks identity/amount/date consistency across re-reads, detects
duplicate economic source IDs, rejects invalid money/date formats and
distinguishes changed/missing/saturated publisher results from an exact
match. A published dollar award **is not** an attainable future CaptureBrief
customer contract, a currently open opportunity, bank-cleared payment,
successful bid or independent original SAM.gov solicitation amendment.
No recipient name, private source row or original award identifier is
logged or included in the persisted report.

The bounded cross-engine source branch now also publishes
`freight/research_lab/official_capturebrief_award_readback_v1.json`,
with the source-anchor hash, original award record counts, any repeated
publisher rows, an aggregate source-only award amount (USD cents),
up to two same-publisher readback outcomes and the canonical sample
SHA-256. This is neither a signature on original bytes nor a model
accuracy score. User-attested broad reuse rights remain distinguishable
from independently verified source-specific terms, and independent
solicitation outcome matches remain zero. The isolated data branch
receives no individual award identifiers or recipient names.

After the first live run the branch must report its **actual** sample
size, readback outcomes and provider error codes. A blocked or changed
publisher source is reported as DEGRADED, not silently turned into no
awards or a passing truth label. The nightly four-engine evaluation
tests its receipt integrity before claiming a healthy read-only replay.

The integration reuses the current controller, protected main,
metadata-only branch, required status checks and existing schedule.
No added Worker, new paid account, direct customer message, unapproved
API credentials or production CaptureBrief alteration is required.

The source contract is published by USAspending:
`https://api.usaspending.gov/docs/endpoints` and
`https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md`.

Run strictly offline regression tests:

    python -m unittest -v freight.test_official_capturebrief_award_lab

Reproduce only from the authorized isolated research branch:

    python -m freight.official_capturebrief_award_lab
    python -m freight.official_capturebrief_award_lab --verify

### Fixed-code provenance for failed original award-ID readbacks

The original issuer sample can succeed while a separately scoped award-ID
re-query fails. The nightly receipt now stores strictly bounded **error code
counts** for those second requests (e.g. HTTP_400, HTTP_429 or
PUBLISHER_UNAVAILABLE) without logging any award ID, URL query content,
publisher response body or recipient identity. A failed second read never
becomes a matching original award or an independent award-outcome label.
Counters are independently validated for consistency with the exact number
of unavailable second reads, even when the receipt's own SHA-256 is recomputed
by an adversarial source.

This diagnostic does not perform additional public API calls, does not
change the source population, and does not weaken fail-closed rules. The
code categorization distinguishes malformed requests, upstream throttling
and provider unavailability to enable a subsequent source-specific fix.

### Independent publisher endpoint fallback for throttled exact award-ID queries

The official USAspending award search returned actual contract rows in
the first live test but responded with HTTP 503 for both quote-wrapped
award-ID re-searches. Rather than falsely treating that as two failed
contract awards, the controller now optionally checks the **documented
separate original-publisher** award-detail GET endpoint:

    https://api.usaspending.gov/api/v2/awards/{INTERNAL_AWARD_ID}/

The URL is built only from a numeric `internal_id` already observed
in the fixed-source award sample. Each read uses fixed-host HTTPS,
no redirects, public-DNS precheck, a 12-second timeout and a strict
440-KiB maximum. No other source or account is contacted.

The fallbacks are attempted only after an initial second-read
HTTP 429, 5xx, or network-unavailable result and only for the existing
two bounded award cases. The source detail endpoint has a **different
schema** from the search endpoint: a successful detail response may
establish *same-issuer identifier and total-obligation consistency*
(`id`, `piid`, `generated_unique_award_id`, `total_obligation`),
but does **not** establish the base obligation date, original SAM.gov
solicitation, bidder eligibility, independent award accuracy, or legal
rights. Consequently the receipt stores separate detail consistency,
mismatch and error counts; the missing exact award-ID search evidence
continues to be disclosed as DEGRADED.

The full original award detail response is ephemeral and can contain
recipient information; only the above bounded publisher fact fields are
inspected, and no award IDs, names, payloads, recipient identities or
URL query values enter the research data branch or GitHub logs. Receipt
fields and counts remain tamper-evident and commercially rights-held.

Official endpoint documentation:
`https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/awards/award_id.md`

## CaptureBrief FY2027 original SAM archive and anti-lookahead receipt (v9)

The existing research controller now has a **research-only** original public
FY2027 Contract Opportunities archive source reader. The exact CSV object
URL was previously observed as a public first-party-listed SAM Data
Services file by CaptureBrief's October 19, 2026 automated source review:
`https://s3.amazonaws.com/falextracts/Contract%20Opportunities/Archived%20Data/FY2027_archived_opportunities.csv`.
The earlier unreviewed observation reported 1,607,260 original bytes,
1,104 data rows, and SHA-256
`7b4e00e3156248db9dcca767431bb6c5d4168aeeb2abc707ab12c0f9e61d71ce`.
These historical values are frozen as a *reference*, **not** a promise that
the publisher still serves identical source bytes today.

Within the **existing** research-only controller, one original fixed-host
HTTPS GET is allowed per UTC day, subject to a public DNS check, a no-redirect
policy, a 15-second timeout, a strict 2.5-MB maximum and complete
Content-Length/Content-Encoding integrity checks. The complete source CSV
is parsed in memory only. The reader verifies all first-party-required
SAM Data Services columns (`NoticeId`, `Sol#`, `PostedDate`, `Type`,
`Active`, `AAC Code`, `Office`, `Link`), source row shape, duplicate
NoticeIds and cross-office/agency solicitation collisions. The source
may evolve: new original-byte SHA-256 is recorded and **compared** to
the historic Oct19 original fingerprint rather than falsely labeled
unchanged.

The digest-linked branch receipt
`freight/research_lab/capturebrief_sam_fy2027_asof_v1.json`
stores **only counts, fixed source URL, source digest, observation time,
prior unreviewed provenance reference, and bounded error states**. It
does not store any contract opportunity description, notice IDs,
solicitation numbers, contacts, source CSV, or original rows. It never
changes the protected CaptureBrief FY2027 production archive catalog,
which remains explicitly **unapproved** for full-catalog release.

A pure **SAM-to-USAspending temporal-join guard** is also tested:
an exact matching `Sol#` and award solicitation identifier is
insufficient without a separately anchored issuing agency and office.
The original SAM issuer-reported `PostedDate` must precede the award
signing date; crucially, the *actual archive source observation* must
also precede that award date. A historical notice copied or obtained
after signing can never backfill a false as-of capability. Source
chronology therefore yields a **candidate only** when every guard
passes; it never independently establishes that CaptureBrief could
have known the opportunity, won a contract, or generated revenue.

This upgrade does **not yet join** the first-party original SAM file
to any individually verified USAspending award record. The current
USAspending readback receipt deliberately stores no original award
identifiers, and the research lab will not reconstruct identifiers
from summary digests. Independent linked award labels remain **0**
until a separate proven first-party agency/office/time association
is available. No buyer/outbound communication, extra source API,
new paid service, new scheduler, or production engine mutation
has been authorized.

Offline controls:

    python -m unittest -q freight.test_capturebrief_sam_fy2027_asof

Inspect exact-branch source receipt without public network:

    python -m freight.capturebrief_sam_fy2027_asof --verify

### Original FY2027 source-field quarantine (Oct 24, 2026)

The first live research-stage implementation encountered
`SOURCE_CSV_SCHEMA_INVALID` and did not publish source rows.
A separate read-only CI diagnostic of the **exact public original
1,607,260-byte CSV** established that the document has 47 headers,
all eight required first-party fields and 1,104 source rows, but **one
`Sol#` value contains a Unicode control character**.

Rather than quietly normalizing an unknown source identity or discarding
the entire authentic public file, the decoder now counts that row,
quarantines only the offending solicitation identifier from candidate
issuer/family matching, and preserves all original source bytes in the
ephemeral file digest. The receipt discloses the fixed error category
`SOURCE_SOLICITATION_CONTROL_QUARANTINED`, the quarantined source-row
count, and `PUBLIC_ARCHIVE_WITH_QUARANTINED_SOLICITATION_FIELD`
status. Only strictly validated, unambiguous solicitation keys are
eligible for future research-only matching; the quarantined row
cannot become an award-join match or independent outcome label.
Source records, raw identifiers, issuer names, and source bytes still
never enter the GitHub branch.

The short-lived **PR-only public CSV diagnostic was removed** after its
aggregate finding; the permanent workflow keeps just the fixed, validated
quarantine counters and original-byte digest. This restores research
observability without treating an intentionally held/unapproved archive
as a production source or inventing retrospective award outcomes.

## GAO B-215958 authority reversal and tariff isolation (v9)

A new **immutable, rights-held historical decision chronology receipt**
`freight/research_lab/gao_authority_chronology_v1.json` is generated on the
existing research data branch from two research-authored GAO case manifests
and three fixed *official* GAO URLs. The key chronology is:

- December 5, 1984: [GAO B-215958 initial decision](https://www.gao.gov/products/b-215958).
  The decision accepted the numbered-seal exclusive-use interpretation for
  53 of the 55 GBLs (other two original dispositions not proved).
- February 18, 1986: [GAO B-215958 reconsideration](https://www.gao.gov/products/b-215958-2).
  **This decision explicitly OVERRULED the carrier-favorable 1984 ruling
  and SUSTAINED the GSA audit/deduction.** Under the historic NASI 190-A
  tariff, numbered seals and their bill-of-lading notation alone did not
  entitle the carrier to exclusive-use charges without the prescribed
  written request.
- January 3, 1969: [GAO B-165091](https://www.gao.gov/products/b-165091)
  separately sustained a $179.80 deduction under a **different** historic
  517-V tariff written-order clause. Its other $393.24 claim was conditional
  on further validation and is **not** a paid/refunded amount.

The research test corpus previously included only the 1984 source and could
therefore misleadingly appear to support that ruling as the *final* case
disposition. It now preserves the original 1984 material **as a historical
observation that was overruled** and explicitly tests the 1986 superseding
outcome. An as-of query on January 1, 1985 returns only the original 1984
decision, while an as-of query after February 18, 1986 returns the controlling
historical reconsideration. This avoids *both* post-1986 stale legal labels
and retroactive pre-1986 look-ahead.

Tests also reject a forged 53-case invoice-accuracy numerator, transferring
a deduction under tariff 517-V to 190-A, treating the 1984 GBL count as
specific invoices or claiming any present-day rate authority, validated bank
refunds, recovery revenue, private customer error detection or reusable
rights. All original document bytes and real invoices remain outside this
catalog. Authored manifest hashes are **not** GAO original document digests.

The receipt is regenerated inside the **same unified controller**, staged
only on `research/retally-unified-data-lab`, validated in the nightly
four-engine source replay, and does not introduce a new Cron trigger, paid
service, customer communication, production-engine mutation or permissive
source-rights promotion.

    python -m unittest -q freight.test_gao_adjudication_chronology
    python -m freight.gao_adjudication_chronology
    python -m freight.gao_adjudication_chronology --verify

## FreightRecovery historic GAO numerical adjudication evidence (v10)

**This is not a new lab, scheduler, source repository or production engine.**
The same unified controller now validates five additional original
historical GAO motor-freight decisions through
freight/gao_motor_freight_numeric.py and its source-bound fixture
freight/fixtures/gao_motor_freight_numeric_v1.json. It generates only a bounded
freight/research_lab/gao_motor_freight_numeric_v1.json receipt on the
**existing isolated research data branch**. The nightly read-only four-engine
replay verifies exactly the persisted receipt, including GAO decision dates,
tariff scopes, published numerical facts and all safety limitations.

Original primary GAO decision URLs and numerics:

| GAO decision | Case-level published financial figures | Evidence limit |
| --- | --- | --- |
| [B-191257, 1978](https://www.gao.gov/products/b-191257) | Yellow Freight: $828.00 paid, $796.00 audited applicable charge, $32.00 GSA offset | Only one case whose two reported charges allow exact subtraction; not a modern tariff |
| [B-152744, 1964](https://www.gao.gov/products/b-152744-0) | Strickland: $611.80 paid, $122.20 deducted | GAO reserved possible later reconsideration depending on litigation; original independent tariff-rate build missing |
| [B-148465, 1962](https://www.gao.gov/products/b-148465) | Western Truck Lines: $546.88 paid, $61.22 deducted | Conditional future Supreme Court outcome caveat; no later disposition certified |
| [B-143048, 1960](https://www.gao.gov/products/b-143048) | Cooper-Jarrett: $130.30 *aggregate* for two shipments; $10.69 vs $7.65 per cwt in the quoted route dispute | No independently verified per-shipment allocations or individually scored bill labels |
| [B-146511, 1965](https://www.gao.gov/products/b-146511-2) | A. B. James: $152.05 paid, $20.74 deducted; the claim also appears as $20.70 and $20.76 | Conflicting numerical claim variants intentionally retained; never silently normalized |

All amounts are *published historical decision-level observations*, not fresh
shipper invoices, independent held-out engine classifications or RETALLY
revenue. Of five cases, **one** has both publisher-stated paid and audited
charges for exact subtraction. The others cannot be labelled with full
source-reconstructed audited amounts. Tests forbid mixing tariffs, inventing
per-shipment allocations, collapsing conflicting amounts, certifying
1962/1964 decisions beyond reserved review, or converting a historical
government offset into customer recoveries.

Written fixtures and receipts store **no original invoice/GBL bytes, source
HTML contents, customer records or credentials**. Authored JSON digests are
*not original GAO page-byte fingerprints*. Official GAO
[terms](https://www.gao.gov/copyright) request attribution, prohibit implied
endorsement and caution about embedded third-party materials. Separate
commercial engine input approval remains unverified. No current legal or
commercial-rate benchmark is claimed.

    python -m unittest -q freight.test_gao_motor_freight_numeric
    python -m freight.gao_motor_freight_numeric
    python -m freight.gao_motor_freight_numeric --verify

## FreightRecovery adjudication controls in nightly replay

The unified lab's existing nightly original-data replay now directly runs
`freight.test_gao_b221594_negative_control` and
`freight.test_gao_b189100_classification`, in addition to source-branch
receipt checks and the original freight-document evaluation. These source-bound
historical tests cover (a) an invalid $220.75 GSA deduction based on a
rejected DOD rate tender and (b) a sustained $2,634.38 GSA deduction after a
cargo-description/classification dispute. Each original-source fixture is
rights-held and no source invoice bytes, independently adjudicated customer
error metrics, modern tariff outcomes, customer credits or RETALLY revenue
are inferred. The cases continue to be checked during ordinary PR/push
verification *and* the existing once-daily real-data replay.

This change adds **no scheduler, provider requests, branch, production engine
actions, contacts or paid services**. CI contract tests explicitly reject
removing either regression from nightly execution without triggering a failure.


## Original GlobalTranz invoice adjustments — canonical v2 lab replay

The original-document lab verifies fixed SHA-256 source bytes from the
public GlobalTranz PDF and extracts **100 distinct actual invoice faces**
with original signed line components. The last confirmed source replay had
**93 invoices with a negative adjustment token** (canonical v2), while the
seven non-discounted original faces correctly remain canonical v1. The older positive-only
ChargeLine-v1 check correctly blocked those negative tokens and represented
just seven faces with charge lines alone. That does *not* mean that the
existing canonical **v2** InvoiceAdjustment mechanism cannot represent them.

The unified nightly lab now exercises the *existing* immutable v2
InvoiceAdjustment data model: nonnegative ChargeLine entries plus positive
magnitudes of original negative invoice components, each source-bound to the
original frozen PDF SHA-256. It checks all source net totals exactly, executes
the canonical v2 record-hash verifier, and rerates twice with an **empty**
AuthorityBook. A structurally valid source record without an independently
verified effective customer rate must always produce REVIEW_REQUIRED with
no expected charge and no claimed variance. No product code or admission
policy is modified.

**Critical separation:** The replay constructs **synthetic lab-only
shipment weight (1 g), postcodes, carrier and LTL mode** where the source
invoice does not independently establish these facts. The v2
kind=DISCOUNT is a provisional encoding of a negative *source component*,
not independently authenticated discount semantics, a credit memo, a bank
settlement or a refund. Only the signed source invoice net is conserved.

The nightly acceptance gate tests an exact 100-face source reconciliation,
including 93 adjustment-bearing records, 100 REVIEW_REQUIRED outcomes,
zero reconstructed-source discrepancies and zero unsafe automated variance
claims. All 110 total original GlobalTranz/ArcBest faces remain
**UNKNOWN for real overcharge classification** until shipment-specific
rate authority, original BOL/weight/contract evidence and independently
adjudicated outcome or payment linkage exist.

This is a deliberately bounded read-only amendment to
freight/real_document_lab.py and its original-PDF regression tests; it
adds no new Workers, GitHub schedule, data branch, customer communication,
cost, production ingestion, live engine change or financial assertion.


## Original freight document evidence-chain readiness (v11)

The latest original-document research verifies **110 real freight-invoice faces**
on two publisher-linked, frozen-hash public PDFs:

- 100 GlobalTranz face amounts, including 100 source-net amounts exactly
  reconstructed as 93 **v2 adjustment-bearing** records and seven original
  **v1 positive-only** charge records. All 100 test-only rating attempts return
  REVIEW_REQUIRED with no expected freight rate, computed variance or cash.
- Ten ArcBest original invoice-face amounts, five of which can enter the
  source-derived **lab-only** rating-proxy structure and all of which remain
  subject to review. The other five fail source-completeness checks.
- 100 GlobalTranz face identifiers also match original invoice amounts in a
  separate **open** statement. This is *not* a verified bank-cleared payment;
  the original document itself identifies it as an open-balance statement.

The new ephemeral, privacy-safe
freight/freight_evidence_chain_readiness.py collector summarizes these
existing nightly results without copying individual invoice IDs, addresses,
source PDF bytes or statements to Git. A fixed review-receipt SHA protects
against reclassification even if the receipt's own digest is recomputed.
Its CI test also pins **both original PDF SHA-256s**, the two reproducible
invoice-face catalog SHA-256s and the current canonical v1/v2 source-record
catalog SHA-256. Any altered source bytes, removed original faces, altered
signed arithmetic, fake bank payments, fabricated independent outcomes,
promoted rights or erroneous automatic rates fail before admission.

**Evidence checklist basis:** The current U.S. GSA
[Transportation Invoice Audit guidance](https://www.gsa.gov/policy-regulations/policy/transportation-management-policy/transportation-invoice-audit)
and [Freight, Household Goods and Small Parcel Audit Handbook](https://www.gsa.gov/policy-regulations/policy/transportation-management-policy/transportation-handbook-freight-household-goods-and-small-parcel)
describe federal checks against bill of lading, carrier rate/contract/tender,
actual shipment details, performed service, invoice totals, related supporting
documentation and when appropriate payment records. They are a **useful
federal reference checklist, not a legal determination that 41 CFR 102-118
governs a private RETALLY shipper/customer contract**.

Current evidence-chain completeness for these 110 original invoice faces:

| Evidence stage observed in isolated lab | Face count |
| --- | ---: |
| Original public source PDFs SHA-256 verified and face amounts extracted | 110 |
| Original signed invoice line amounts conserved through canonical records | 100 |
| Distinct independently custodied linked BOL for that invoice | 0 verified |
| Shipment-specific effective buyer/carrier contract or tender | 0 verified |
| Independent actual shipment weight/class and performed service | 0 verified |
| Bank-cleared payment, credit or reimbursement proof | 0 verified |
| Independently adjudicated customer invoice error outcome | 0 verified |
| Cash recovered by RETALLY | $0 verified |

These zeroes mean **not available in the current controlled lab input**.
They do not prove the original shipper or carrier lacks the documents. The
source-derived canonical proxies use synthetic shipment fields and lab-only
discount classification: neither is legal or commercial rate truth.

The new receipt is created and verified **only in an ephemeral nightly
workspace** from the actual original-document benchmark, without additional
schedule triggers, cloud workloads, original-source downloads beyond the
existing two PDFs, third-party contacts, spending, hosted-product mutations,
commercial approvals, or any persistent private source identifier.

    python -m unittest -q freight.test_freight_evidence_chain_readiness
    python -m freight.freight_evidence_chain_readiness --source /tmp/retally-real-lab.json --output /tmp/retally-freight-evidence-chain-readiness-v1.json
