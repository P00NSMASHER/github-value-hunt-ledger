# RETALLY Unified Research Lab

**Mission:** continuously find authentic external data capable of stress-testing
FreightRecovery, PermitPlate, CaptureBrief and RecoveryOS, and run the strongest
already-approved real-document and engine regression tests without user prompts.

## One operating model

- **One automatic research controller:** .github/workflows/retally-unified-research-lab.yml.
- **One long-lived data branch:** research/retally-unified-data-lab, separate from protected main and production sites.
- **One canonical cross-engine catalog:** freight/research_lab/leads.json; exact URL deduplication and engine tags preserve the source's original first-seen date.
- **Four lanes, not four independent workers.** Every five minutes the scheduler rotates one engine's discovery queries. This gives each engine a planned 20-minute interval. GitHub cron can be delayed or skipped; there is **no guaranteed five-minute execution SLA**.
- **One nightly read-only test campaign:** real original freight invoices, RecoveryOS general-AP disclosures, PermitPlate official-source adapter regressions, and CaptureBrief procurement-source regressions.
- **Legacy Lab 15 source discovery preserved:** the two original metadata harvesters are run **inside the central controller** when FreightRecovery's periodic legacy refresh is due; their two legacy ledgers remain historical/compatibility views on the *same* data branch. Their independent scheduled triggers are retired, not their test code.
- **Existing Labs 1–14 kept intact:** their research findings, adversarial cases and stacked draft PRs are not silently declared merged, green or production-authorized. The synthetic 14-domain test director in PR #297 is a separate unmerged draft with explicit non-merge limitations. Port each validated, read-only harness into the nightly controller only when it exists on approved main; never transplant unfinished stacked branches into production.

## Real-data research targets

| Lane | Discovery and validation |
| --- | --- |
| FreightRecovery | Official GAO adjudications; public invoice exhibits; freight-rate documents; Data.gov, Zenodo and public GitHub dataset *catalogs*. Nightly original GlobalTranz and ArcBest document replay using existing ingestion, rating and reconciliation paths. |
| PermitPlate | NYC restaurant inspections, DOHMH pre-permit events, DOB NOW building filings and SLA liquor-license applications; real-source adapter and V4-relevant engine regression. **Not parking-ticket analytics:** PermitPlate's current product concerns restaurant vendor opportunity signals. |
| CaptureBrief | SAM.gov opportunity and amendment sources, federal procurement archives and USAspending award data; existing historical/current-source controls. Current SAM API access requiring a key is not assumed. |
| RecoveryOS | Original published vendor-payment and invoice disclosures, especially Pennine Care NHS spending CSVs, plus public procurement/payment metadata; nightly replay through the existing RecoveryWorks reconciliation kernel. |

### FreightRecovery dynamic evaluation feed (v1 integration)

- The collector automatically includes the **seven non-invoice official reference URLs** from the already-frozen nine-case FreightRecovery evaluation pack. Direct third-party invoice-specific URLs and original files are **not** added to discovery.
- After the unified controller and both existing Lab 15 collectors run, `freight.research_eval_bridge` independently validates their three ledgers and builds one deduplicated `freight/research_lab/evaluation_candidates.json` file, saved only on `research/retally-unified-data-lab`.
- The queue retains only source locator metadata, publisher host, source-ledger provenance, earliest observation date, and exact matches to pre-existing fixed reference cases. Legacy source titles, original byte fingerprints, customer document text, and unapproved commercial-use assertions are not exported.
- Every candidate remains **RIGHTS_AND_INDEPENDENT_EVIDENCE_PENDING**, including official legal precedents and sources matching existing published rate references. Unknown sources do not automatically become numerical truth or modify the frozen nine-case fixture.
- The nightly read-only job checks the data branch's queue *against all three upstream ledgers*, replays the nine-case real-world pack and the earlier five-source official numeric reference suite through the existing native engine paths, and publishes aggregate hold-only counts. First-publish timing races use an explicitly logged temporary queue; they do not falsely claim that persistent publication happened.
- No extra research service, repository, workflow schedule, contacts, customer-data path, payment permissions, or separate lab branch is created.

Commands (run from repository root with the data branch ledgers accessible):

```sh
python -m unittest -v freight.test_research_eval_bridge
python -m freight.research_eval_bridge build
python -m freight.research_eval_bridge verify
```

**Candidate sources are not adjudicated invoices.** New numeric benchmark cases require approved original source custody, independent buyer-specific contracts, BOL/weight, bank/payment evidence, and independently sealed review outcomes. The existing original-document lab remains a separate research lane and is not silently assigned positive or negative freight-error labels.

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

The **only** automatic writer stages freight/research_lab/leads.json and the
two existing Lab 15 metadata ledgers and triage output. It cannot modify
protected main, website pages, engine code, sales/claim data, customer inbox,
Stripe, private PermitPlate source state or CaptureBrief private archives.
Writes use serialized GitHub Actions, no force push, no source document uploads,
no customer/prospect/carrier outreach, and no paid API or paid infrastructure.

Ten offline unit tests defend against ledger manipulation, forged rights and
cash assertions, injection URLs, duplicates, rerun drift, partial source
failures, and wrong engine rotation. Source API outages must surface as workflow
failures or explicit provider errors; zero new leads by itself is not success
proof, accuracy evidence, nor an excuse to manufacture data. Research discovery
may produce many **leads** while yielding zero independently labeled cases.

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
