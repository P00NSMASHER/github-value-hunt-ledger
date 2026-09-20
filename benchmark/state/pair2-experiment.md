# Pair 2 — EXPERIMENT persistent state

## Task completion
- 09 — COMPLETE (2026-09-20): official FAR machine-source/provenance benchmark completed with GSA/GSA-Acquisition-FAR at `da52ccbbe114e1f031a7f4c59195c508dbfa485f` as the accepted strong candidate.
- 10 — UNFINISHED
- 11 — UNFINISHED
- 12 — UNFINISHED
- 13 — UNFINISHED
- 14 — UNFINISHED
- 15 — UNFINISHED

## Validated reusable lessons
- On official regulatory/procurement corpora, the public reading website can be weaker for automation than the agency's production-source repository. In Task 09, the GSA DITA source exposed solicitation fill-ins (`xtrf="GFI"`) and documented FM change-marker conventions that were not the point of the rendered reading surface.
- README version text is not sufficient evidence of currentness. Task 09's README snapshot information lagged later repository history, so exact commit pinning plus history and independent first-party publication cross-checks are required.
- Negative verification is useful: Task 09 did not substantiate a repo-local acquisition-specific XSD, so schema claims must remain limited to the standard DITA DOCTYPE/schema family actually observed.

## Failed search patterns
- Treating eCFR alone as the complete answer for acquisition automation: authoritative machine-readable regulation, but Task 09 did not verify solicitation-specific fill-in semantics there.
- Treating Federal Register alone as the complete corpus: strong amendment provenance, but not the consolidated current clause/provision source needed for fill-in extraction.
- Inferring current regulatory version from README date strings without checking commit history and the official publication surface.

## Useful terminology / signatures
- `xtrf="GFI"` — GSA FAR Global Fill-in marker for clause/provision input fields.
- `FM MARKER` / `FM AREA` — documented FAR/FAC/FAR Council production change comments keyed by case number.
- DITA `concept` / `conbody` / `section` / `lines` structure in the FAR source corpus.

## Candidate search skills awaiting second-task confirmation
- **Production-source triangulation for official rule corpora**: find the agency's source-generation repository, inspect operational markup in real files, pin exact revision/history, then cross-check a separate official publication/rulemaking system. Task 09 succeeded; requires a second distinct benchmark success before SEARCH_SKILLS.md promotion.
