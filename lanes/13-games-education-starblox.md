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

### Longsight qti3
- Repository: https://github.com/LongsightGroup/qti3
- Commit / revision: `2fc318baeef285e0330abdc86da385d783b8f2f2`
- Date discovered: 2026-09-19
- What it contains: A framework-neutral TypeScript QTI 3 assessment engine with a zero-third-party-runtime core/CLI for parsing, validation, response processing, scoring, state serialization/restoration, package inspection, item-bank writing, candidate-preference resolution, QTI 1.2/2.x migration, and transcoding to QTI 1.2/2.1/2.2 plus Canvas Classic/New Quizzes and Moodle XML. It also includes a native web-component player, React/Preact adapters, reference fixtures, conformance tooling, browser tests, and accessibility checks across the public interaction families.
- Why it matters: This is the strongest standards/content-interoperability find for StarBlox so far. Instead of maintaining a proprietary quiz format, StarBlox could ingest existing QTI banks, render rich question types, preserve scoring semantics, and export authored content back into common LMS/import formats. That materially changes the school-sales story because content migration and standards compatibility stop being a custom engineering project.
- Commercial possibilities: Standards-based StarBlox assessment/content layer; QTI-bank importer for districts and publishers; Canvas/Moodle export path; assessment migration service; interactive item-authoring tool; content marketplace that is not locked to a proprietary question schema.
- Build-time savings: Estimated 12-24+ engineering weeks versus implementing and testing QTI parsing, scoring, interaction rendering, accessibility, migration, package handling, and LMS-targeted transcoding independently.
- Evidence inspected: `README.md` at the pinned revision (package architecture and interaction support matrix); `packages/core/src/parser.ts` (`parseQtiXml` implementation); `packages/conformance/src/run-fixture.ts` (fixture execution through the parser); browser Playwright tests including `tests/browser/player.spec.ts`, `player-choice.spec.ts`, `player-match.spec.ts`, and `player-axe.spec.ts`; `packages/transcoder/src/qti22.test.ts`; `packages/writer/src/assessment-test.test.ts` including a complete adaptive-route round trip; `LICENSE.md`; commit history through the pinned revision.
- License / rights: MIT License, copyright 2026 Longsight, Inc. The source is permissively reusable with the MIT notice. 1EdTech specifications, marks, certification materials, and customer-supplied assessment content are separate rights domains and should not be treated as covered by the repository license.
- Reuse classification: Directly reusable (MIT, preserve notice); separately verify rights for any imported third-party item banks or external standards/certification artifacts.
- Scores:
  - Technical value: 9.7/10
  - Commercial value: 9.5/10
  - Rarity: 9.3/10
  - Completeness: 9.5/10
  - Build-time saved: 9.8/10
  - Data advantage: 4.5/10
  - High-ticket potential: 9.4/10
- Next action: Build a ten-item synthetic StarBlox question pack, round-trip it through qti3, and verify native rendering plus QTI/Canvas/Moodle export before changing StarBlox's internal content model.

### Longsight OneRoster for TypeScript
- Repository: https://github.com/LongsightGroup/oneroster
- Commit / revision: `8c14777e44efaf7cc32135c3eceeaa2ab12f69a4`
- Date discovered: 2026-09-19
- What it contains: A TypeScript implementation of OneRoster CSV and REST interoperability: ZIP/package parsing and writing, typed rostering/gradebook/resources records, reference and duplicate-ID validation, OneRoster 1.2 REST clients, 1.1 compatibility, pagination/filtering, gradebook writes, OAuth helpers, and a framework-neutral provider router. The project includes a CSV rostering conformance gate covering 719 official reference cases, REST-spec parity tooling, portability checks, and tests around full-package validation and client behavior.
- Why it matters: This is the missing school-operations bridge for turning StarBlox from a consumer-style educational game into something a school can actually deploy. It can eliminate large amounts of bespoke work around classes, teachers, students, enrollments, terms, courses, results, and grade passback while keeping the StarBlox learning/game layer separate.
- Commercial possibilities: District-ready StarBlox roster sync; automatic class provisioning; teacher assignment/result workflows; SIS/LMS integration product; white-label school game platform; reusable OneRoster integration layer for other education SaaS products.
- Build-time savings: Estimated 8-16+ engineering weeks for a standards-oriented rostering/gradebook integration baseline, plus substantial reduction in interoperability testing and edge-case handling.
- Evidence inspected: `src/one-roster-csv-full-validation.ts` (actual full-ZIP parse/validation entry point); `test/one-roster-csv-full.test.ts`, `test/one-roster-csv-full-semantics.test.ts`, `test/one-roster-csv-conformance.test.ts`, and public-API smoke tests; `tools/check-csv-rostering-conformance.mjs`; `src/v1p2/rostering/client.ts` (registry-driven REST client); `test/v1p2-rostering-client.test.ts`; `README.md`; `LICENSE`; pinned commit history.
- License / rights: MIT License, copyright 2026 OneRoster TypeScript contributors. Preserve the MIT notice. OneRoster/1EdTech specifications and SHA-pinned official conformance artifacts downloaded by tooling have their own terms; do not assume those external artifacts are relicensed by this repository.
- Reuse classification: Directly reusable for repository code (MIT); external specification/conformance artifacts require separate rights verification before redistribution.
- Scores:
  - Technical value: 9.3/10
  - Commercial value: 9.7/10
  - Rarity: 9.0/10
  - Completeness: 9.4/10
  - Build-time saved: 9.6/10
  - Data advantage: 4.0/10
  - High-ticket potential: 9.7/10
- Next action: Create a synthetic-only adapter that maps OneRoster users/classes/enrollments/results into StarBlox's internal identities, classrooms, assignments, and mastery/result records, then test round-trip grade passback without using real student data.

### OpenGameData ogd-core
- Repository: https://github.com/opengamedata/ogd-core
- Commit / revision: `0cf0d5787fefc9b2a1a5ea9685956bbd791046f2`
- Date discovered: 2026-09-19
- What it contains: A Python game-telemetry feature-extraction framework built for educational games. It reads raw event data from supported stores/exports and produces session-, player-, and population-level features through game-specific extractors. The codebase contains many real educational-game modules plus progression, sequence, and population feature implementations; the inspected BLOOM `PlayerProgression` tracks nodes, transitions, completion state, active time across sessions, and progression links from raw events.
- Why it matters: StarBlox currently benefits more from better learning telemetry than from another cosmetic feature. This provides a mature pattern for turning raw gameplay events into interpretable progression and engagement features that can drive teacher dashboards, product analytics, learning-efficacy studies, and experiment measurement. It complements SkillCoco/IRT: those systems decide what a learner should see; OpenGameData helps measure what actually happened.
- Commercial possibilities: Teacher/class progress dashboards; retention/drop-off analysis; learning-game analytics service; efficacy/evaluation reports for schools; cohort and level-funnel analysis; reusable analytics layer for other educational games.
- Build-time savings: Estimated 6-10+ engineering weeks for a tested feature-extraction architecture and a library of educational-game analytics patterns, before any StarBlox-specific event mapping and dashboard work.
- Evidence inspected: `README.md` at the pinned revision; `src/ogd/games/BLOOM/features/PlayerProgression.py` (event-driven player progression graph, session-gap handling, time-on-node, node/link counts); multiple additional `PlayerProgression`/population feature classes and game loaders found in source; game-module tree spanning numerous educational titles; `tests/cases/games/LAKELAND/test_lakeland_models.py` parameterized feature tests; broader `tests/cases` structure; `LICENSE`; pinned commit history.
- License / rights: MIT License, copyright 2019 University of Wisconsin - Field Day Lab. The code is permissively reusable with the notice. Any external game datasets, exports, or game-specific content should be treated separately and reused only if their own licensing permits it.
- Reuse classification: Directly reusable for MIT code and architecture; game datasets/content require independent rights checks.
- Scores:
  - Technical value: 9.0/10
  - Commercial value: 8.8/10
  - Rarity: 8.9/10
  - Completeness: 8.7/10
  - Build-time saved: 9.0/10
  - Data advantage: 7.0/10
  - High-ticket potential: 8.5/10
- Next action: Define a minimal StarBlox event schema using synthetic play sessions and port one progression plus one population feature end-to-end before deciding whether to adopt the framework wholesale or just its feature architecture.

### Ltijs
- Repository: https://github.com/Cvmcosta/ltijs
- Commit / revision: `4854de290595f9fe161d9a173dd989add7ccac0c`
- Date discovered: 2026-09-19
- What it contains: An actively maintained TypeScript-first LTI 1.3 Tool Provider implementation with validated launches, Deep Linking, Assignment and Grade Services (AGS), Names and Role Provisioning (NRPS), Dynamic Registration, launch-context handling, platform/key management, database abstractions, and the associated security/crypto plumbing. The current v7 codebase has unit/database tests across JWT/JWK handling, encryption, request authorization, grading serialization, platform keys, database managers, and other service boundaries.
- Why it matters: qti3 solves assessment content interoperability and OneRoster solves rostering/gradebook data exchange; Ltijs fills the third major school-platform gap: actually launching StarBlox as an LTI tool inside an LMS and using LMS services. In combination, these three repositories could compress a district/LMS integration roadmap that would otherwise require a large amount of security-sensitive protocol work.
- Commercial possibilities: LMS-launchable StarBlox for Canvas/Moodle/other LTI 1.3 platforms; grade-return-enabled classroom game; district pilot package; embeddable adaptive-learning tool; reusable LTI integration service for other education products.
- Build-time savings: Estimated 6-12+ engineering weeks for LTI/OIDC/JWT launch security, AGS grade workflows, NRPS roster access, Deep Linking, Dynamic Registration, and associated integration testing.
- Evidence inspected: `README.md` at the pinned revision; `src/services/grading/grading.service.ts` (actual AGS `Grading` implementation); `src/services/names-and-roles/names-and-roles.service.ts` (actual NRPS client/service); `src/services/launch/launch-context.service.ts`; tests including JWT, JWK/key, signed-value, AES encryption, authorization-header, grading serializer, platform-key, and database-manager suites; `LICENSE`; pinned commit history.
- License / rights: Apache License 2.0. Preserve required notices and comply with Apache-2.0 terms. LTI/IMS/1EdTech specifications, marks, certification, and platform-specific configuration remain separate from the code license.
- Reuse classification: Directly reusable under Apache-2.0 with notice/compliance obligations.
- Scores:
  - Technical value: 9.4/10
  - Commercial value: 9.8/10
  - Rarity: 9.1/10
  - Completeness: 9.3/10
  - Build-time saved: 9.7/10
  - Data advantage: 3.5/10
  - High-ticket potential: 9.8/10
- Next action: Stand up a local synthetic LTI 1.3 launch test with AGS grade passback, then connect it conceptually to the qti3 question layer and OneRoster classroom model before any real-school integration work.


## Art Production Accelerators

StarBlox integration target: `P00NSMASHER/StarBlox@screenshot-match-preproduction`, with the active implementation contract under `docs/preproduction/art-factory/`. Model/checkpoint rights for the StarBlox project are user-attested as fully cleared; this does **not** change repository code licenses, dataset/reference-asset terms, external API/service terms, or custom-node licenses.

### Hugging Face Diffusers
- Repository: https://github.com/huggingface/diffusers
- Commit / revision: `7263f3317f6b392d62f41e9d75ed9d7e21fc5a5c`
- Capability: Production Python diffusion runtime exposing FLUX/SDXL pipelines, ControlNet surfaces, IP-Adapter loading, schedulers, seedable generation, and reusable pipeline components.
- Why it fits StarBlox: Provides the provider-neutral generation layer behind the existing exact-metadata `artPromptOptimizer` without forcing prompt logic into a hosted vendor.
- Estimated build-time saved: ~6–12+ engineering weeks versus building/maintaining modern diffusion pipeline, scheduler, conditioning and batching infrastructure from scratch.
- Integration surface: `artPromptOptimizer` -> deterministic generation attempt -> versioned exact-byte source -> optional derivative stage -> staged-art render -> independent exact-hash review -> Workstream 08 canonical integration.
- License / weight / data terms: Repository code Apache-2.0. StarBlox model/checkpoint rights are user-attested as cleared, but exact model ID/revision must still be recorded; reference/dataset/API terms remain separate.
- Reuse classification: **DIRECT CODE REUSE / PREFERRED GENERATION FOUNDATION**.
- Concrete pilot: Generate 2–4 variants for one currently assigned REWORK item using exact Store metadata, a deterministic seed per attempt and full provenance; do not scale until independent review.

### Tencent AI Lab IP-Adapter
- Repository: https://github.com/tencent-ailab/IP-Adapter
- Commit / revision: `62e4af9d0c1ac7d5f8dd386a0ccf2211346af1a2`
- Capability: Image-prompt/reference conditioning for identity/style/appearance consistency across diffusion generations.
- Why it fits StarBlox: High leverage for keeping a character, item family, material language or approved visual reference consistent while still allowing distinct poses/forms.
- Estimated build-time saved: ~3–6 weeks for reference-conditioning plumbing and experiments.
- Integration surface: Reference asset SHA + adapter scale become explicit conditioning provenance fields on each factory attempt; outputs remain versioned candidates subject to real StarBlox render/review.
- License / weight / data terms: Repository code Apache-2.0. Model/checkpoint rights are user-attested cleared for StarBlox; reference-image rights remain independent.
- Reuse classification: **DIRECT CODE REUSE / REFERENCE-CONSISTENCY LAYER**.
- Concrete pilot: Pair one accepted family reference with a single REWORK item, vary adapter scale across 2–4 deterministic attempts, and compare actual card/detail identity/readability.

### JohannesBuchner ImageHash
- Repository: https://github.com/JohannesBuchner/imagehash
- Commit / revision: `7a405c9a27571ee8c998b661ce751639c34b7355`
- Capability: pHash, dHash, color hash and related perceptual fingerprints for image similarity/deduplication.
- Why it fits StarBlox: Cheaply flags recolor clones, repeated silhouettes and suspiciously similar catalog variants before reviewer time is spent.
- Estimated build-time saved: ~1–2 weeks for robust perceptual-hash implementations, normalization and comparison logic.
- Integration surface: Existing `pilot_art_accelerators.py` normalizes Store canvases, records hashes and emits nearest neighbors after exact byte checks.
- License / weight / data terms: Permissive BSD-style repository license; no model weights required.
- Reuse classification: **DIRECT CODE REUSE / REPORT-ONLY QA**.
- Concrete pilot: Continue collecting pHash/dHash/color-hash distances against independently labeled ACCEPT/REWORK history; do not auto-reject or auto-approve from thresholds yet.

### PyMatting
- Repository: https://github.com/pymatting/pymatting
- Commit / revision: `6d5c4a6bed0e5672abac0bad078e594423ffe4fd`
- Capability: Classical alpha matting/refinement from trimaps without requiring a learned segmentation checkpoint.
- Why it fits StarBlox: Improves halo/fringe quality for catalog items, characters and accessories while retaining deterministic source-to-derivative lineage.
- Estimated build-time saved: ~2–4 weeks for reliable matting solvers and edge-quality experimentation.
- Integration surface: Source candidate -> mask/trimap -> versioned alpha-refined derivative -> checkerboard and actual Store render -> independent review. Never overwrite source bytes.
- License / weight / data terms: MIT code; no learned model weights required for the selected classical path.
- Reuse classification: **DIRECT CODE REUSE / ALPHA-EDGE REFINEMENT**.
- Concrete pilot: Run on transparent non-canonical candidates with partial-alpha boundaries; compare source vs derivative at card/detail size and preserve both hashes.

### scikit-image SSIM
- Repository: https://github.com/scikit-image/scikit-image
- Commit / revision: `2dff163516e1a7c528b48d5eda8cf40788f0ade3`
- Capability: Tested structural-similarity metrics and image-processing primitives.
- Why it fits StarBlox: Provides an independent second similarity signal alongside perceptual hashes for duplicate/fidelity diagnostics.
- Estimated build-time saved: ~1–2 weeks versus implementing and validating SSIM correctly.
- Integration surface: Optional offline/report-only sidecar after normalized render capture; never a promotion gate.
- License / weight / data terms: BSD-family code; no model weights.
- Reuse classification: **OPTIONAL DIRECT REUSE / REPORT-ONLY QA**.
- Concrete pilot: Correlate SSIM and perceptual-hash distances with existing independent originality decisions before any threshold is considered.

### rembg
- Repository: https://github.com/danielgatis/rembg
- Commit / revision: `202e42649a8492a7c49f808de36608a7d1cbbfe3`
- Capability: Local CLI/API/batch background removal, alpha matting and foreground decontamination.
- Why it fits StarBlox: Fast path for converting generated item/character sources into transparent catalog-ready derivatives.
- Estimated build-time saved: ~2–4 weeks for background-removal service/CLI integration and batch plumbing.
- Integration surface: Optional source-preserving derivative stage before PyMatting/render QA.
- License / weight / data terms: MIT code. Segmentation-model files are a separate rights domain; StarBlox model/checkpoint rights are user-attested cleared, but exact model revision still belongs in provenance.
- Reuse classification: **OPTIONAL DIRECT CODE REUSE / BACKGROUND REMOVAL**.
- Concrete pilot: Compare rembg+PyMatting against source/native alpha on the same four bounded candidates and keep only derivatives that improve actual card/detail edges.

### LayerDiffuse Diffusers CLI
- Repository: https://github.com/lllyasviel/LayerDiffuse_DiffusersCLI
- Commit / revision: `3061d9aed52a6c52a13fcf2b196c0fef4d727824`
- Capability: SDXL-oriented native transparent/latent-layer generation path with deterministic examples.
- Why it fits StarBlox: Can reduce the need for post-hoc cutout when accessories/items genuinely benefit from native alpha.
- Estimated build-time saved: ~2–5 weeks of native-alpha experimentation/integration.
- Integration surface: Alternate generator mode producing a versioned source with alpha; compare against segmentation+PyMatting under the same prompt/seed metadata.
- License / weight / data terms: Apache-2.0 code. Associated model/safetensor/base-model rights remain separate but are user-attested cleared for StarBlox; exact revisions still required.
- Reuse classification: **OPTIONAL DIRECT CODE REUSE / NATIVE-ALPHA EXPERIMENT**.
- Concrete pilot: Same four prompts/seeds through native-alpha and normal-generation+matting paths; decide from real Store renders, not isolated transparency previews.

### Real-ESRGAN
- Repository: https://github.com/xinntao/Real-ESRGAN
- Commit / revision: `a4abfb2979a7bbff3f69f58f58ae324608821e27`
- Capability: Tiled super-resolution/restoration with alpha-aware image handling.
- Why it fits StarBlox: Can rescue otherwise good source art with insufficient detail/payload scale without regenerating the concept.
- Estimated build-time saved: ~2–4 weeks for robust tiling, alpha-aware upscale and restoration plumbing.
- Integration surface: Optional derivative only after a source is preserved; derivative gets its own hash/render/review.
- License / weight / data terms: BSD-3-Clause code. Pretrained weights remain a separate rights item; StarBlox rights are user-attested cleared but exact revision must be logged.
- Reuse classification: **OPTIONAL DIRECT CODE REUSE / DERIVATIVE RESTORATION**.
- Concrete pilot: Apply only to one or two candidates whose independent review identifies resolution/edge detail as the actual defect; reject the step if it invents texture or harms small-card readability.

### InvokeAI
- Repository: https://github.com/invoke-ai/InvokeAI
- Commit / revision: `9e1540962bcca7f8fa668d7d8e02cf79d75fda3b`
- Capability: Tested batch queue, API and graph/workflow orchestration around diffusion generation.
- Why it fits StarBlox: Useful only after the bounded factory proves enough throughput to justify a persistent queue; avoids inventing another orchestration service.
- Estimated build-time saved: ~4–8+ weeks if/when multi-worker batch generation becomes a real bottleneck.
- Integration surface: Queue/orchestration layer around the same provider-neutral attempt/provenance contract; never replaces StarBlox review or canonical integration.
- License / weight / data terms: Apache-2.0 code; model and external-service terms separate.
- Reuse classification: **OPTIONAL SCALE-UP INFRASTRUCTURE**.
- Concrete pilot: Defer until repeated 2–4 item pilots show generation throughput, not review quality, is the limiting factor.

### ComfyUI
- Repository: https://github.com/Comfy-Org/ComfyUI
- Commit / revision: `e638023d54497dbe0579565e5de4bb7076899592`
- Capability: Mature node-graph workflow authoring/execution with prompt queue/websocket interfaces and a large ecosystem.
- Why it fits StarBlox: Strong for visual workflow experimentation and reproducible node graphs, but less clean as the default foundation because core code is GPL-3.0 and custom-node/model licenses vary.
- Estimated build-time saved: ~3–8 weeks for visual workflow authoring and queue plumbing if a node-graph path is specifically needed.
- Integration surface: Isolated authoring/worker option that must emit the same StarBlox attempt/provenance record and exact-byte candidates.
- License / weight / data terms: GPL-3.0 core code; every custom node/model/data dependency must be reviewed independently.
- Reuse classification: **ISOLATED OPTION / NOT DEFAULT FOUNDATION**.
- Concrete pilot: Use only if a workflow requires graph authoring that Diffusers/InvokeAI cannot provide cleanly; keep it outside StarBlox runtime and compare throughput/maintenance cost before adoption.

### Current StarBlox factory referral
- Branch handoff: `P00NSMASHER/StarBlox@screenshot-match-preproduction/docs/preproduction/art-factory/README.md`
- Machine-readable contract: `docs/preproduction/art-factory/ART_FACTORY_V2.json`
- Direct pilot: `docs/preproduction/art-factory/pilot_art_accelerators.py`
- Deterministic preflight: `.github/workflows/art-factory-preflight.yml`
- Promotion rule: bounded generation -> exact-byte staging/readback -> real card/detail or target-surface render -> independent exact-hash review -> Workstream 08 canonical integration.
