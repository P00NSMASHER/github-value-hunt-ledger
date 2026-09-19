# Games / Education / StarBlox

## Hunter instructions
Before searching, read this file plus ../MASTER.md, ../REJECTED.md, and ../COMBINATIONS.md.

Search public GitHub repositories for unusually valuable functioning software, data pipelines, algorithms, workflows, datasets, integrations, or product infrastructure relevant to this lane. Include obscure, abandoned, low-star, and no-license repositories in discovery. Respect license/copyright for reuse.

Do not collect, reproduce, preserve, or exploit exposed credentials, personal data, authentication material, or accidentally published confidential information. Skip/quarantine those items and continue searching for legitimate technical or commercial value.

## Finding template
### Repository name
- Repository:
- Commit / revision:
- Date discovered:
- What it contains:
- Why it matters:
- Commercial possibilities:
- Build-time savings:
- Evidence inspected:
- License / rights:
- Reuse classification:
- Scores:
  - Technical value:
  - Commercial value:
  - Rarity:
  - Completeness:
  - Build-time saved:
  - Data advantage:
  - High-ticket potential:
- Next action:

## Findings

### SkillCoco
- Repository: https://github.com/skillcoco/skillcoco
- Commit / revision: `805c6c784db5ad60a02d450dc1711f1b3e1381c6`
- Date discovered: 2026-09-19
- What it contains: A functioning adaptive-learning engine and app with canonical 4-parameter Bayesian Knowledge Tracing (BKT), SM-2 spaced repetition, prerequisite/mastery gating, deterministic daily microlearning selection, topic-pack import/export, achievement/certificate infrastructure, AI content generation, and storage abstractions that keep the core algorithms independent of SQLite/IndexedDB.
- Why it matters: This is unusually close to the missing learning-science core for a serious educational game. StarBlox can keep its kid-facing game/store/avatar layer while replacing simplistic fixed quizzes with per-learner mastery, review scheduling, prerequisite unlocks, and “best next challenge” selection. The algorithm code is small enough to embed or port and is supported by tests and whitepapers rather than README-only claims.
- Commercial possibilities: Adaptive K-8 practice engine; school-branded learning game; mastery-based quiz/quest layer for StarBlox; teacher dashboard with evidence-backed mastery; reusable adaptive-learning SDK for other education products.
- Build-time savings: Estimated 4-8+ engineering weeks versus designing, validating, documenting, and testing BKT + spaced repetition + challenge-selection behavior from scratch; potentially much more if the pack/course infrastructure is reused.
- Evidence inspected: `skillcoco-core/src/bkt.rs` (BKT math, mastery threshold, 9 unit tests); `skillcoco-core/src/sm2.rs` (SM-2 scheduler and extensive boundary/sequence tests); `skillcoco-core/src/microlearning.rs` (deterministic challenge selector combining BKT zone, spaced-repetition due state, recency penalty, decay signal, deterministic tie-breaking, stub-store tests); `LICENSING.md`; repository commit history. Source paths and docs resolve at the pinned commit.
- License / rights: Repository `LICENSING.md` states all source code, topic-pack formats, bundled packs, algorithm whitepapers, daily microlearning, badges, certificates, and core adaptive engine are MIT. It also identifies some DeepTutor-derived path/content-generation portions as Apache-2.0-attributed in `THIRD_PARTY_NOTICES.md`. Preserve MIT notices and any file-level Apache attributions when reusing those portions.
- Reuse classification: Directly reusable (MIT), with normal notice/attribution obligations and file-level Apache notices where applicable.
- Scores:
  - Technical value: 9.4/10
  - Commercial value: 9.0/10
  - Rarity: 8.7/10
  - Completeness: 9.1/10
  - Build-time saved: 9.3/10
  - Data advantage: 4.0/10
  - High-ticket potential: 8.2/10
- Next action: Extract the BKT + SM-2 + microlearning APIs behind a thin StarBlox adapter and run a small deterministic simulation against current quiz/question content to compare fixed-question progression versus mastery-based selection.

### Adaptive Question Selector
- Repository: https://github.com/woodstocksoftware/adaptive-question-selector
- Commit / revision: `616234ff31bf87455f2912af84d876f3fb9d4ab4`
- Date discovered: 2026-09-19
- What it contains: A compact production-oriented 2-parameter logistic Item Response Theory (IRT) engine with ability estimation, regularized maximum-likelihood fitting, Fisher-information question selection, standard-error/confidence estimates, adaptive stopping behavior, a FastAPI session API, input bounds/capacity/TTL controls, and a substantial pytest suite.
- Why it matters: SkillCoco handles longitudinal mastery and review; this repository fills a different high-value gap: efficient placement tests and adaptive assessments that converge on learner ability with fewer questions. It can make StarBlox onboarding and level placement feel game-like while materially reducing unnecessary questions.
- Commercial possibilities: Adaptive placement test for StarBlox; grade/skill-level diagnostic; school intervention screener; pre/post assessment service; standalone adaptive-assessment API for education SaaS.
- Build-time savings: Estimated 2-4 engineering weeks for a tested IRT selector/API baseline, plus avoidance of common numerical and edge-case errors in home-grown adaptive testing.
- Evidence inspected: `src/irt.py` (2PL probability model, Fisher information, MLE with regularization, all-correct/all-incorrect edge handling, confidence intervals, max-information and target-50 selection); `tests/test_irt.py` (probability, overflow, information, ability-estimation, confidence, adaptive-selection and update tests); `src/server.py` (FastAPI sessions, request validation, session TTL/capacity, health endpoint); `LICENSE`; recent commits.
- License / rights: MIT License, copyright 2026 Jim Williams.
- Reuse classification: Directly reusable (MIT, preserve notice).
- Scores:
  - Technical value: 8.8/10
  - Commercial value: 8.5/10
  - Rarity: 8.3/10
  - Completeness: 8.7/10
  - Build-time saved: 8.5/10
  - Data advantage: 3.0/10
  - High-ticket potential: 7.8/10
- Next action: Combine with SkillCoco conceptually: use IRT for initial placement/periodic diagnostics and BKT+SM-2 for ongoing mastery and review. Validate on a synthetic 2nd-grade question bank before connecting to any student data.

### M3 CharacterStudio
- Repository: https://github.com/M3-org/CharacterStudio
- Commit / revision: `293182bf4a6087f4a4a7fd00e4fbdfb590029da7`
- Date discovered: 2026-09-19
- What it contains: A mature browser-based 3D avatar construction stack around Three.js/VRM with modular character traits, manifest-driven assets, animations, emotions, blinking, look-at behavior, screenshots, GLB/VRM export, random/batch generation, hidden-face culling, and an optimization/export path that supports skinned-mesh merging and texture atlasing. Core logic is centralized in `CharacterManager`; the repo includes Vitest unit/integration tests.
- Why it matters: If StarBlox moves from flat character art toward a Roblox/Bitmoji-style 3D identity system, this removes a large amount of low-level avatar engineering. The valuable part is not the sample art; it is the reusable character assembly/animation/export/optimization machinery.
- Commercial possibilities: StarBlox 3D avatar creator and wardrobe; kid-safe school mascot/avatar builder; branded character creator for schools/camps; embeddable avatar customization module; batch-generated promotional characters.
- Build-time savings: Estimated 6-12+ engineering weeks for the avatar runtime, VRM/GLB assembly, screenshots/export, animation plumbing, and optimizer baseline; art/content creation remains separate.
- Evidence inspected: `src/library/characterManager.js` (model/trait/animation/emotion/blink/look-at/screenshot/manifest orchestration); `src/library/download-utils.js` and optimization documentation (optimized export, texture atlas options); repository tests including `tests/unit/characterManager.simple.test.js`, `tests/unit/utils.test.js`, i18n tests and integration security tests; `LICENSE`; pinned commit history.
- License / rights: Core repository code is MIT (copyright Atlas Foundation). Do not assume sample or separately fetched avatar/model asset packs carry the same rights; verify each asset pack independently before commercial reuse. Prefer using StarBlox-owned or separately licensed art with the MIT runtime.
- Reuse classification: Directly reusable for MIT code; external/sample asset rights must be verified separately.
- Scores:
  - Technical value: 9.1/10
  - Commercial value: 8.6/10
  - Rarity: 8.2/10
  - Completeness: 8.9/10
  - Build-time saved: 9.5/10
  - Data advantage: 2.0/10
  - High-ticket potential: 7.4/10
- Next action: Prototype a tiny StarBlox-specific manifest with only owned placeholder art and test whether CharacterStudio can support the existing store/equip flow at acceptable mobile performance before committing to a 3D migration.
