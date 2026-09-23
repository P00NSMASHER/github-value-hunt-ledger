# StarBlox Development-Acceleration Audit — 2026-09-23

## Scope

Thorough scan of the Hunter repository plus source-level verification against the live StarBlox repository and its active `screenshot-match-preproduction` branch.

Primary question: **which already-discovered or already-built code removes the most remaining StarBlox engineering work?**

This handoff does not modify third-party repositories and does not treat README claims as implementation proof.

---

## 1. Current StarBlox state changes the answer

Repository: `P00NSMASHER/StarBlox`

Active acceleration branch:
- `screenshot-match-preproduction`
- observed head: `176478f1b1988fac52576049307fd2744cd53494`
- relation to `main`: **1121 commits ahead, 0 behind**
- merge base / main head at comparison: `d7502ff4c6f18329e21b304109e44213a4c155f0`

The old main-branch release ledger reported:
- 87/192 final-portable
- 105 remaining

The current preproduction manifest reports:
- manifest version: **33**
- target: **192**
- mapped entries: **173**
- final-portable: **166**
- remaining: **26**
- duplicate asset paths: **0**

Therefore the preproduction workstream has already eliminated most of the original art backlog and must not be rebuilt from `main`.

### Exact 26 remaining by manifest state

**Unmapped / visible fallback IDs (19):**
- Desks: `desks-7` through `desks-12` (6)
- Wall: `wall-8` through `wall-12` (5)
- Decor: `decor-5` through `decor-12` (8)

**Mapped but interim-not-verified (7):**
- `companions-2`
- `companions-5`
- `companions-6`
- `companions-7`
- `companions-8`
- `companions-9`
- `companions-12`

---

## 2. Highest-value code already built inside StarBlox

### Existing Art Factory — KEEP, DO NOT REBUILD

Branch contains a working production sidecar:
- `scripts/artPromptOptimizer.mjs`
- `scripts/artFactoryJob.mjs`
- `scripts/artReviewNormalizer.mjs`
- `scripts/artRegenerationQueue.mjs`
- `scripts/catalogFallbackBacklog.mjs`
- `scripts/catalogVisualPreflight.py`
- `scripts/catalogVisualCalibration.py`
- `scripts/artWorkflowAudit.mjs`
- `docs/preproduction/art-factory/verify_staged_output.py`
- `.github/workflows/art-factory-preflight.yml`

Capabilities already implemented:
- exact-hash ACCEPT / REWORK learning
- structured visual-failure taxonomy
- deterministic prompt hashes
- deterministic job-plan seeds
- exact runtime/model revision slots
- 2–4-variant bounded generation plans
- stale-safe regeneration queues
- exact-byte readback verification
- Git blob SHA + SHA-256 evidence
- visual/perceptual preflight
- calibrated report-only warnings
- disjoint producer/reviewer routing
- preservation of accepted hashes
- no automatic visual approval

**Conclusion:** do not create another art queue, review system, prompt store, or catalog QA framework.

---

## 3. Browser / visual QA is also already solved

Existing code:
- `scripts/catalog-staged-art-qa.mjs`
- `scripts/preproductionVisualQa.mjs`
- `scripts/referenceScreenshotCapture.mjs`
- `.github/workflows/catalog-staged-art-qa.yml`
- `.github/workflows/preproduction-visual-qa.yml`
- `.github/workflows/reference-screenshot-capture.yml`

Implemented behavior:
- Playwright Chromium
- real Store card/detail rendering
- image signature verification
- exact Git-blob binding
- stale-alternate rejection
- unsafe/external SVG rejection
- contact sheets + detail captures
- desktop/tablet/mobile viewports
- responsive geometry contracts
- 44px touch checks
- runtime/page-error checks
- keyboard-focus checks
- Axe color-contrast checks
- deterministic screenshots
- Pixelmatch diagnostic diffs
- SHA-256 binding
- explicit separation between pixel diff and human visual approval

**Conclusion:** do not add Cypress, Storybook/Chromatic, or a second screenshot harness to solve current release work.

---

## 4. Exact-byte recovery/import infrastructure already exists

Important reusable code:
- `scripts/importCatalogAdobeBatch.py`
- multiple family-specific `scripts/import*Recovery*.py`
- `docs/preproduction/reference-intake/import_reference_screenshots.py`
- `docs/preproduction/catalog-sprint/import_chat_intake01.py`

The generic Adobe importer already:
- reads a machine request through `STAR_BLOX_RECOVERY_REQUEST`
- validates current 192-item Store metadata
- allowlists HTTPS source hosts
- downloads exact source/rendition bytes
- decodes JPEG/PNG/WebP
- rejects blank images
- checks dimensions
- computes SHA-256
- computes canonical Git blob SHA
- writes immutably
- refuses conflicting existing bytes
- reads bytes back exactly
- preserves original generation containers
- rejects duplicate candidate content
- emits a structured review handoff

**Conclusion:** no new “binary upload system” is needed. The missing issue is availability of the exact source bytes / provenance-compliant generator surface.

---

## 5. Current remaining-art work by true action type

### A. Recover / stage existing bytes — do NOT regenerate first

#### Desk 7
Two Adobe Firefly candidates already generated remotely.
Current state:
- remote generated
- producer visual check passed
- stable Firefly generation URNs preserved
- repository exact-byte staging pending

Rule in current evidence:
> preserve both candidates and recover exact bytes before any regeneration or review.

#### Desk 8
Two real local source candidates were generated and measured:
- source SHA-256 values recorded
- expected Git blob SHAs recorded
- derivative hashes recorded
- exact repository binary staging failed in prior attempt

No new creative generation is necessary if those exact bytes can be recovered from the producing environment/artifact.

#### Desk 9 / Desk 10
Remote Firefly candidates and native/local source candidates were generated with visual checks.
Do not blindly regenerate while exact candidates remain recoverable.

#### Wall 8
A fresh `wall-8-w05-v2.png` was independently REWORK for mounting/read depth.
Current `ACTIVE_BATCH` assigns:
- selected Variant B exact-byte recovery only
- no regeneration if exact selected bytes can be recovered

### B. Existing candidate bytes need review / integration, not generation

#### Companion 2 / 5 / 6 / 7
Rich source/card/detail candidates already exist under:
`public/assets/catalog-candidates/chat-20260921-intake01/`

Current state:
- exact repository bytes present
- independent Reviewer 05 decision pending
- no regeneration required before review

Companion 8 and 12 also have rich candidate bytes but remain held by current review/theme gating.

### C. Truly needs a provenance-compliant generator

#### Wall 9–12
Current state:
- only legacy flat SVGs
- reviewer 14 = REWORK
- no new candidate directory
- prompts/seeds/metadata plans prepared
- blocked specifically on a runtime that exposes:
  - model/checkpoint ID
  - exact revision
  - runtime/tool revision
  - executed seed or allowed authoritative “seed unavailable” record
  - exact output bytes

Current tested Firefly/Viewmax/built-in-container paths were closed because their metadata/runtime contract was insufficient.

#### Decor 5 / 6 / 7 / 8
Current old or W09 candidates are REWORK / provenance-blocked.
Replacement plans exist.
They should be generated only with the revision-reporting runtime.

Decor 9–12 are intentionally gated behind the smaller pilot.

#### Desk 11–12
Frozen until Desk 7–10 pilot is dispositioned.
Do not open yet.

---

## 6. Biggest missing piece: deterministic Diffusers generation adapter

Hunter already identified:

### `huggingface/diffusers@7263f3317f6b392d62f41e9d75ed9d7e21fc5a5c`
Use for:
- pinned model loading
- deterministic generator seeds
- FLUX / SDXL paths
- ControlNet
- batching
- scheduler/inference plumbing

Hunter build-time estimate:
**6–12+ engineering weeks** versus writing/maintaining this substrate from scratch.

### `tencent-ailab/IP-Adapter@62e4af9d0c1ac7d5f8dd386a0ccf2211346af1a2`
Use for:
- StarBlox-owned accepted reference-image conditioning
- family identity consistency
- reducing recolor/template drift

Hunter estimate:
**3–6 engineering weeks** saved.

### Required StarBlox adapter should be narrow

```
STARBLOX_ART_FACTORY_JOB
        ↓
validate planSha / attempt metadata
        ↓
resolve exact model snapshot / revision
        ↓
load Diffusers pipeline
        ↓
optional IP-Adapter / ControlNet
        ↓
torch.Generator(seed)
        ↓
generate exact source candidate
        ↓
write source bytes + provenance receipt
        ↓
verify_staged_output.py
        ↓
existing Playwright card/detail render
        ↓
independent exact-hash review
```

Do **not** build a new queue/reviewer/integration system around it.

---

## 7. Learning-engine shortcut

Current StarBlox `gameModel.pickQuest()` is a good deterministic heuristic but not a learner model.

Current scoring roughly:
- unseen: +80
- wrong answers: +18
- correct answers: -3
- recency/due-days bonus
- transfer +10
- review +4

Current mastery award is essentially a count threshold of independent mastery-eligible correct answers.

### Best complete learning donor: SkillCoco

`skillcoco/skillcoco@805c6c784db5ad60a02d450dc1711f1b3e1381c6`

Verified:
- canonical 4-parameter BKT
- SM-2
- deterministic microlearning selector
- BKT struggle zone
- due-card handling
- decay/recency
- store abstractions
- substantial tests

Hunter estimate:
**4–8+ weeks saved**.

Do not import its entire Tauri desktop application.

### Best architecture-fit mastery donor: MasteryTrace

`RudrenduPaul/MasteryTrace@7f2070d9869802472246e7bcf4cbf868c2a0aa02`

Verified:
- native TypeScript BKT
- native TypeScript 2PL IRT
- independent Python port
- 162 tests
- no server
- no database required
- importable Node/TypeScript API
- synthetic IRT parameter-recovery tests

Recommended combination:
- MasteryTrace TypeScript for BKT / diagnostic IRT
- port only SkillCoco SM-2 + microlearning selector behavior
- preserve current StarBlox browser/local state

This avoids creating a backend just to add mastery science.

---

## 8. Large future accelerators — do not insert into current release

### Longsight qti3
`LongsightGroup/qti3@2fc318baeef285e0330abdc86da385d783b8f2f2`

Hunter estimate:
**12–24+ weeks** saved.

Use later for:
- QTI parsing/writing
- scoring
- state
- rich interactions
- accessibility
- Canvas / Moodle export
- district/content migration

Do not rewrite current Quest around QTI before visual release.

### OneRoster
`LongsightGroup/oneroster@8c14777e44efaf7cc32135c3eceeaa2ab12f69a4`

Estimate:
**8–16+ weeks** saved.

Use when school deployment requires classes/users/enrollments/results.

### Ltijs
`Cvmcosta/ltijs@4854de290595f9fe161d9a173dd989add7ccac0c`

Estimate:
**6–12+ weeks** saved.

Use for LTI 1.3 launch/AGS/NRPS/Deep Linking.

### OpenGameData
`opengamedata/ogd-core@0cf0d5787fefc9b2a1a5ea9685956bbd791046f2`

Estimate:
**6–10+ weeks** saved.

Use for educational-game progression / engagement / efficacy analytics after event instrumentation is a real requirement.

### CharacterStudio
`M3-org/CharacterStudio@293182bf4a6087f4a4a7fd00e4fbdfb590029da7`

Estimate:
**6–12+ weeks** of 3D avatar engineering avoided.

**Defer.** StarBlox already has a large 2D art investment and only 26 catalog slots remain; switching to 3D now is negative leverage.

---

## 9. Hunter internal code worth reusing as patterns

### `freight/release_provenance.py`
Useful pattern:
- require full 40-char revisions
- normalize repository/component inventory
- hash all control files
- build deterministic provenance hash
- verify snapshot against current checkout

### `freight/release_attestation.py`
Useful pattern:
- deterministic release envelope
- hashes provenance + SBOM
- explicit claim boundary
- never implies signature/certification that does not exist

### `production/blind_partition.py`
Useful later for:
- train/confirm split receipts
- preventing question-selector/mastery optimizers from learning directly on protected confirmation cases

Do not port these wholesale into StarBlox today; borrow the invariants where needed.

---

## 10. Fastest implementation sequence

1. **Do not restart from main.**
   Continue on `screenshot-match-preproduction`.

2. **Recover/stage existing exact bytes before generating anything new.**
   Prioritize:
   - Desk 7–10 preserved candidates
   - Wall 8 selected recovery candidate
   - Companion rich candidates already in the repo

3. **Use the existing generic importer / recovery workflows.**
   Do not create a new binary transport layer.

4. **Implement one narrow Diffusers adapter behind `STARBLOX_ART_FACTORY_JOB`.**
   No new queue, reviewer or catalog writer.

5. **Pilot the adapter only on one bounded release batch.**
   Best fresh-generation pilot:
   - Wall 9–12 or Decor 5–8 after current pilot gates
   - preserve all accepted exact hashes

6. **Finish all 192 art mappings before broad new gameplay work.**

7. **After visual release, add mastery science with minimal architecture change.**
   - MasteryTrace TS: BKT / optional IRT
   - SkillCoco donor: SM-2 + microlearning selection

8. **Keep qti3 / OneRoster / Ltijs / OpenGameData as post-MVP accelerators.**

9. **Defer 3D CharacterStudio migration.**

---

## Bottom line

The highest-value Hunter discovery is not a new external framework. It is that StarBlox already contains most of the hard production machinery on its preproduction branch.

The true missing work is now narrow:
- recover existing candidate bytes where possible;
- provide one provenance-compliant deterministic image-generation runtime;
- finish the 26 remaining catalog slots;
- then replace heuristic learning selection with a tested mastery/spaced-repetition kernel.

Everything else should be treated as later expansion, not current-release scope.
