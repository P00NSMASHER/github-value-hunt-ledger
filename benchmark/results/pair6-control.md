# Pair 6 — CONTROL results

Frozen benchmark result log. Append one task result block per scheduled run. Do not rewrite prior completed blocks.

TASK: 37
CONDITION: CONTROL
STARTING HYPOTHESIS: A strong target will combine several municipal permit-source adapters with a canonical permit/property model, preserve every observed permit state instead of destructive upsert-only storage, and contain tests that catch semantically wrong field mappings such as permit fee being mistaken for project valuation.
DISCOVERY METHODS: Broad web/domain search for municipal permit ingestion across Accela/Socrata/ArcGIS/Tyler-style systems; GitHub code search for connector/mapping/versioning signatures; deliberate low-attention/zero-star repository inspection plus comparison against commercial permit aggregators and weaker single-source projects.
CANDIDATE: adamleap02/PermitBuild
CANONICAL URL: https://github.com/adamleap02/PermitBuild
EXACT REVISION: ff795137e0c66e62a87e62956fa351926886255d
VERDICT: STRONG
A-F SCORE: A4 B4 C5 D5 E5 F4 = 27/30
EVIDENCE INSPECTED: backend/app/models.py; backend/app/ingest.py; backend/tests/test_ingest.py; backend/tests/test_connector_arcgis.py; backend/README.md; repository metadata and exact main-head commit. Source shows SourceSystem variants for Socrata, ArcGIS, CKAN, HTML/Accela scraping and FOIA intake; the README enumerates 62 wired municipal/state permit feeds. PermitVersion stores full snapshots plus changed_fields under a unique permit/version key. Ingest code diffs canonical fields, writes a new version on create/update, and explicitly avoids silent overwrite. Tests reproduce duplicate-permit version collisions and require gap-free version sequences. Connector regression tests explicitly protect semantics including project valuation vs permit fee, placeholder values, owner/provenance fields, absent status/issue-date fields, date parsing and geometry/address behavior across multiple jurisdictions.
CLAIMS VERIFIED: Multi-system permit ingestion is implemented beyond README through concrete Socrata/ArcGIS/CKAN/Accela connector modules and source registries. Permit change history is implemented as append-style PermitVersion snapshots with field-level old/new diffs and tested monotonic version numbering. Semantic field-mapping QA is explicit in regression tests, including multiple tests that ensure fee columns are not misinterpreted as construction valuation and tests for source-specific missing/placeholder fields. Property records are linked from normalized permit addresses/parcels and support enrichment.
CLAIMS NOT VERIFIED: I did not live-run all 62 external feeds, so current operability of every jurisdiction is not independently proven. "Immutable" is an application invariant/documented behavior rather than a database-enforced append-only table policy. I did not validate every jurisdiction mapping against the live municipal schema. The repository has no detected public GitHub license metadata; the user's standing separate commercial-permission assumption is therefore material to deployment/reuse.
STRONGEST OBJECTION: The source breadth is unusually high for a zero-star project, but municipal schemas drift continuously; maintaining 62 mappings/scrapers is an ongoing operational burden, and the historical-version immutability guarantee is enforced by code convention/tests rather than hard database permissions/triggers.
COMMERCIAL WEDGE: Managed permit-change intelligence: onboard a contractor/material supplier/developer to a metro set, ingest official municipal permits daily, deliver only new/meaningfully changed permits with field-level diffs and provenance, and charge recurring fees for sales leads, project monitoring or property-development intelligence.
SEARCH EFFORT: 3 materially distinct discovery searches; 5 deep inspections.
FALSE-PROMOTION RISK: LOW-MEDIUM — the core connector/versioning/semantic-QA behaviors are source-and-test verified, but full live-feed coverage and long-term mapping maintenance were not independently exercised.
LESSON: N/A
COMPLETED_AT: 2026-09-20T01:33:04-04:00
