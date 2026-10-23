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
| PermitPlate | NYC restaurant inspections, DOHMH pre-permit events, DOB NOW building filings and SLA liquor-license applications; real-source adapter and V4-relevant engine regression. **Not parking-ticket analytics:** PermitPlate's current product concerns restaurant vendor opportunity signals. |
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
