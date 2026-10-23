# RETALLY Unified Research Lab

**Mission:** continuously find authentic external data capable of stress-testing
FreightRecovery, PermitPlate, CaptureBrief and RecoveryOS, and run the strongest
already-approved real-document and engine regression tests without user prompts.

## One operating model

- **One automatic research controller:** .github/workflows/retally-unified-research-lab.yml.
- **One long-lived data branch:** research/retally-unified-data-lab, separate from protected main and production sites.
- **One canonical cross-engine catalog:** freight/research_lab/leads.json; exact URL deduplication and engine tags preserve the source's original first-seen date.
- **Four lanes, not four independent workers.** Every five minutes the scheduler rotates one engine's discovery queries (4, 9, 14, etc. minutes past the hour, to avoid the hour-boundary queue). This gives each engine a planned 20-minute interval. GitHub cron can be delayed or skipped; there is **no guaranteed five-minute execution SLA**.
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
- Every five minutes, Cloudflare chooses the least recently attempted one of
  the four engines, avoiding missed-event starvation.
- It fetches only public GitHub/Zenodo and official NYC Socrata *metadata*,
  bounds response sizes and source count (24 per run), canonicalizes URLs,
  and deduplicates them in its own D1 store. It does not fetch original invoice
  bytes, scrape restricted sites, send messages, or use commercial data APIs.
- D1 rights/truth-state fields are CHECK-locked to UNVERIFIED. Only public URL
  pointers and per-engine counts can leave that store. No independent accuracy
  or recovered cash assertions.
- Cron invocation is idempotent per five-minute UTC slot and lane; duplicate
  triggers cannot inflate source rows. HTTP endpoints are **read-only**:
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
