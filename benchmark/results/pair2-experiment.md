# Pair 2 — EXPERIMENT results

Frozen benchmark result log. Append one task result block per scheduled run. Do not rewrite prior completed blocks.

## TASK 09 — Acquisition rule provenance
DATE: 2026-09-20
STATUS: COMPLETE

HYPOTHESIS:
An official first-party FAR production source exists in machine-readable form that preserves more procurement semantics than rendered regulation text alone—specifically clause/provision structure, solicitation fill-ins, and identifiable change/revision provenance. Falsification condition: no first-party source could be verified beyond rendered HTML, or machine-readable sources lacked either fill-in semantics or auditable revision/change provenance.

DISCOVERY MODES USED:
1. Direct domain/authority search across GSA/Acquisition.gov, eCFR and Federal Register first-party sources.
2. Code/file/markup inspection of the candidate source corpus, including exact DITA clause XML and acquisition-specific markup conventions.
3. Commit/history archaeology at an exact Git revision, including recent Federal Management/FAR production-fix commits and source-sync history.
4. Independent authority cross-check against Acquisition.gov, eCFR and Federal Register rather than relying on repository claims alone.

CANDIDATES CONSIDERED:
- GSA/GSA-Acquisition-FAR — official GSA source DITA XML used to create the FAR at Acquisition.gov; strongest match.
- eCFR API / Title 48 machine-readable regulatory text — authoritative structure/date source, but no verified FAR solicitation fill-in semantics or equivalent case-local production markers.
- Federal Register API/documents — authoritative amendment/rulemaking provenance, but not a consolidated current clause/provision corpus with structured fill-ins.
- Acquisition.gov rendered FAR pages — authoritative reading surface, but less useful as the machine-source substrate than the GSA DITA corpus.

BEST CANDIDATE:
GSA/GSA-Acquisition-FAR
Canonical URL: https://github.com/GSA/GSA-Acquisition-FAR

EXACT REVISION / VERSION:
da52ccbbe114e1f031a7f4c59195c508dbfa485f (master observed 2026-09-20); tree b17931d0739d432eb448a39f6cb99b300ae7ed49; parent 298318be7a6fd4dc1546b7a12b08a1072502b3f6.

VERIFIED EVIDENCE:
- Repository metadata identifies the project as GSA's "Source DITA XML for the Federal Acquisition Regulation."
- README at the exact revision states the DITA XML is used to create the FAR at Acquisition.gov and describes machine conversion into DITA with special handling for Multi-Line Text Fields and prescription references.
- README documents acquisition-specific Global Fill-in semantics: `xtrf="GFI"` marks clause/provision fields requiring solicitation/contract input.
- Real source file `dita/52.203-14.dita` was inspected at the exact revision. It is structured DITA (`concept`, `conbody`, `section`, ordered-list/list-item/paragraph elements) and contains multiple `<lines ... xtrf="GFI">` fill-in regions, including blank underscore lines. The clause title itself preserves its regulatory revision label: `52.203-14 Display of Hotline Poster(s). (NOV 2021)`.
- README documents production change markers `FM MARKER` and `FM AREA` keyed by case number for FAR/FAC/FAR Council text changes.
- Git history independently verifies active revision provenance. Recent commits include `7d81e616dee28495d3d3d066fd4bea7edf46fbee` (`Resolve 2026-01 FM and Technical errors`) and `fc9b64f57d28fb519be9a23102ab67452c35796e` (`sync with gsa-far-api`).
- Exact Git commit/tree/parent identity was verified, so downstream parsers/diff engines can pin a reproducible corpus state rather than relying on a mutable website.
- Standard DITA DOCTYPE/schema family is present in the inspected clause source. No repository-local acquisition-specific XSD was verified in this run; attempts to locate one did not substantiate that claim.
- Official Acquisition.gov/eCFR/Federal Register surfaces were used as authority cross-checks. Federal Register case-based rulemaking corroborates that FAR case identifiers are real regulatory provenance, but the strongest machine-production substrate verified here is the GSA DITA repository.

SPECIALIST PASSES:
- SOURCE/AUTHORITY VALIDATOR: verified first-party GSA ownership and the README's explicit Acquisition.gov production role; compared eCFR/Federal Register/Acquisition.gov alternatives.
- CODE/MARKUP INSPECTOR: inspected a real clause file at the pinned commit and verified structural DITA markup plus `xtrf="GFI"` fill-ins; explicitly failed to verify a custom repo-local XSD.
- HISTORY/PROVENANCE ANALYST: pinned commit/tree/parent and checked recent commit history for FM corrections and API synchronization.
- COMMERCIAL ANALYST: identified buyers as GovCon/acquisition software vendors, solicitation builders, contract-compliance systems and procurement teams. First paid wedge: a revision-aware FAR clause diff + fill-in extractor/exporter for one solicitation/award workflow; adjacent wedge: authoritative rule-update feed and clause matrix automation.

RED-TEAM / VERIFIER:
VERDICT: STRONG / ACCEPT.
Independent objections that survived review:
- README freshness is not sufficient evidence of current regulatory state; its stated FAC snapshot can lag later repository history. Production use must pin exact commits and reconcile against current official acquisition sources.
- The README acknowledges machine conversion required human intervention for irregular/missing tags, so a parser must tolerate source anomalies rather than assume perfect regularity.
- FM comments are useful provenance metadata, not by themselves a complete semantic amendment graph; a defensible revision tracker should combine corpus diffs, Git history and official FAC/Federal Register metadata.
- The inspected clause proves standard DITA structure and GFI fill-ins, but no custom acquisition-specific XSD was verified.
- Public repository license metadata was null in the observed repository metadata. Record provenance exactly; the user's standing separate repository-code authorization applies only to repository-owned material and not automatically to third-party tooling or independently owned assets.
Despite these objections, the first-party machine-readable corpus directly satisfies the benchmark's core requirement: structured FAR source, explicit solicitation fill-ins, and reproducible revision/change provenance.

SCORE:
A 4/5 — straightforward paid wedge for clause-diff/fill-in/solicitation automation.
B 4/5 — meaningful GovCon/procurement value, though the buyer universe is specialized.
C 5/5 — compresses substantial FAR parsing, curation and provenance engineering.
D 5/5 — rare first-party production corpus with procurement-specific fill-in and change conventions.
E 5/5 — repository role, real source markup, exact revision and history independently verified.
F 4/5 — official first-party source and reproducible revision, with public-license metadata/third-party boundary caveats.
TOTAL: 27/30.

COMMERCIAL INTERPRETATION:
The repository is a strong substrate for a procurement-diff engine rather than merely a reference corpus. A product can pin an exact FAR corpus revision, extract clause/provision fill-ins, generate clause matrices or solicitation templates, and diff later corpus revisions while attaching case/history provenance. The immediate money path is reduced manual acquisition/legal reconciliation and lower risk of stale or incorrectly populated clauses.

WHAT FAILED:
- eCFR alone did not verify the acquisition-specific fill-in semantics needed for solicitation automation.
- Federal Register alone provides amendment provenance but not the consolidated current clause/provision corpus.
- Repository-local acquisition-specific XSD/specialization files were not substantiated; do not promote that claim without a new source.
- README dates cannot be treated as the corpus's current regulatory version without commit/source reconciliation.

SEARCH-SKILL LESSON:
For official rule corpora, search the production-source repository rather than only the public reading website. Then triangulate three evidence layers: (1) source markup semantics, (2) exact commit/history provenance, and (3) a separate first-party publication/rulemaking authority. Acquisition-specific operational metadata may hide in markup attributes/comments rather than file names or README headlines.

NEXT QUERY IF REOPENED:
Trace `FM MARKER`/`FM AREA` case identifiers across multiple historical commits and join them to official Federal Register/FAC metadata to test whether a deterministic case→changed-clause provenance graph can be generated without manual interpretation.

SEARCH-SKILLS PROMOTION: NO — this is the first benchmark-task success for the lesson; protocol requires success on at least two distinct benchmark tasks or Hunt 15 approval before promotion.
