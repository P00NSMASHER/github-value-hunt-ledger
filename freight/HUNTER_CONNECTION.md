# Hunter to Freight connection

Hunter now has a small, deterministic bridge into Freight's operating review. It connects the existing capability registry, graph, search provenance, commercial outcomes and Freight gap register. It does not introduce a second learner or a runtime dependency on the research corpus.

The initial mapping covers all **19 registered capabilities**: **10 USE**, **7 DEFER**, and **2 OUT_OF_SCOPE**. USE means a reviewed application proposal, not installed code or a production claim. The best immediate use of the research is improving invoice evidence, historical rate authority, deterministic rerating, settlement truth, source completeness and review effort. Scientific decoders and industrial equipment emulation remain outside the current freight offer.

## Run the review

From the repository root:

```bash
python -m freight.hunter_bridge --format markdown
python -m freight.hunter_bridge --format json > /tmp/freight-hunter-review.json
python -m freight.hunter_bridge --check
```

Use `--source-ref` with the exact 40-character Git commit when the calling CI/job knows it. The report always includes SHA-256 hashes of the input files. It writes only to standard output; the optional shell redirection above writes a report chosen by the operator. `--check` exits 1 when review is needed and 2 on invalid inputs. Ordinary reporting exits 0 while preserving the review queue. This lets ongoing Hunter research feed review without blocking every unrelated research change.

The private Freight CI job publishes the Markdown review in its job summary when the connected inputs change. The JSON report retains fuller evidence: graph edges, search-run IDs, durable evidence paths and candidate revisions as actually recorded. Missing upstream revisions remain missing; the bridge never invents them.

## What changes when Hunter learns

1. Hunter records evidence in its existing catalogs and structured search records. Run the existing intelligence generation/validation workflow after catalog edits so `intelligence/capabilities.jsonl` remains current.
2. The bridge compares each capability's current metadata, connected edges and related search evidence with its reviewed fingerprint in `HUNTER_FREIGHT_MAP.json`.
3. New capabilities default to DEFER/UNMAPPED. Changed evidence becomes SOURCE_CHANGED. Removed capabilities and incomplete outcome provenance also enter the review queue. A changed `CAPABILITIES.md` file is detected even before generated registry refresh.
4. A reviewer inspects the source evidence, identifies the affected Freight gap and selects a small implementation with the mapping's measurable acceptance test. Existing gap states and named buyer/diligence gates remain authoritative.
5. After review, change the mapping decision and reviewed fingerprint in a normal code review. Record the inspected repository revision. A hash update is an acknowledgement of review, not proof that the implementation passed its acceptance test.
6. Measure delivery effort, false-positive dollars, paid conversion and supported settlement using existing Freight reporting. Use `freight/outcome_adapter.py` and the existing outcome review process to append legitimate, attributed evidence to `intelligence/outcomes.jsonl`.
7. The bridge reuses `freight/commercial_learning.py` to report whether enough independent buyer evidence exists for a pricing/scope review. It never reprices automatically.

Capability fingerprints cover the structured evidence identified above. They do **not** hash every referenced Hunter Markdown document, fetch external repositories, validate current external code, or continuously audit all upstream revisions. The input manifest adds a hash of the canonical capability catalog; other catalog changes should flow through the existing intelligence-generation workflow and recorded search observations. Full registry coverage is not a claim that every catalog repository has been deployed or individually reassessed by this bridge.

## Business priority and honest learning

The backlog inherits all current Freight gaps and their evidence-to-close requirements. The first authorized buyer population is P0 because more repository research cannot establish willingness to pay or customer recovery. Internal deployment controls, reproducible release evidence and rights diligence remain separate owner tasks. Dormant buyer-specific connectors remain dormant until their registered trigger occurs.

At the initial reviewed snapshot, the only recorded Freight outcome is a **synthetic PARTIAL rehearsal**. There are **zero eligible paid buyer cohorts** in the calibrator. The correct commercial recommendation is **KEEP_PRIOR**. This describes the available outcome records; it does not assert that no payments exist elsewhere in the business.

The bridge excludes Freight outcomes with missing search attribution, unknown capability references or blank evidence locations from commercial calibration. The existing calibrator then excludes synthetic/internal work and applies its minimum independent-buyer thresholds. Recorded external-evidence flags and locations still require human verification; the bridge does not inspect private payment documents or independently prove bank receipt.

## Operating boundary

Keep this report and the research corpus in the private operating repository. Put only approved product code and customer-safe copy into a deployment. Keep customer documents, credentials, contracts and raw financial records in the approved customer-data environment; use pseudonymous outcome summaries with controlled evidence references in Hunter.

This bridge performs no network requests, imports no researched third-party code, sends no messages, makes no provider transactions, changes no permissions, opens no research gap and deploys no product. Customer-data processing and external actions remain governed by the existing Freight launch and engagement controls.
