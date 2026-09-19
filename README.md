# GitHub Value Hunt Ledger

Private persistent memory for the GitHub Value Hunt.

## Operating model
- Lanes 01-14 are independent discovery streams.
- Every hunter reads its lane, MASTER.md, REJECTED.md, and COMBINATIONS.md before searching.
- New findings must be evidence-backed and deduplicated.
- Task 15 integrates findings across lanes and maintains MASTER.md, COMBINATIONS.md, and REJECTED.md.
- Public repositories may be analyzed regardless of popularity or license, but reuse must respect license/copyright.
- Do not collect, preserve, reproduce, or exploit exposed credentials, personal data, authentication material, or accidentally published confidential information. Quarantine and skip those items.

## Finding schema
Each retained finding should include:
- Repository + canonical URL
- Exact commit/revision inspected
- Date discovered
- Lane
- What it contains
- Why it matters
- Commercial possibilities
- Build-time savings
- Evidence inspected
- License / rights
- Reuse classification
- Scores: technical value, commercial value, rarity, completeness, build-time saved, data advantage, high-ticket potential
- Next action

## Reuse classification
- Directly reusable
- Reusable with license conditions
- Inspect / learn / clean-room implementation only
