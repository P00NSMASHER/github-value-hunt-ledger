# StarBlox referral — Art Production Accelerators

Referral for [`lanes/13-games-education-starblox.md`](./13-games-education-starblox.md). This file records rights-clean/public infrastructure that can materially compress the `P00NSMASHER/StarBlox` 2D art pipeline without changing gameplay or treating third-party model weights/data as covered by repository code licenses.

## Operating rule
Repository code rights and model/data/API rights are separate. The candidates below were inspected at exact revisions. A permissive code license does **not** grant rights to a downloaded checkpoint, training dataset, bundled third-party media, external API, trademark, or hosted service. Any model-weight-backed pilot is gated on separately verifying the exact checkpoint/model-card terms. No credentials, private data, accidental confidential material, or exploit material was retained.

## Art Production Accelerators

### 1. Hugging Face Diffusers — strongest generation-runtime foundation
- Repository: https://github.com/huggingface/diffusers
- Commit / revision: `7263f3317f6b392d62f41e9d75ed9d7e21fc5a5c`
- Capability: Production-grade diffusion pipelines with current FLUX/SDXL support, ControlNet, IP-Adapter integration, deterministic `torch.Generator` seeding and batched prompts. The inspected FLUX ControlNet pipeline handles generator state and prompt-list batch sizing; current pipeline tests include FLUX IP-Adapter behavior; current docs explicitly describe IP-Adapter on Flux and combining IP-Adapter with ControlNet for structural control.
- Why it fits StarBlox: It is a much better substrate than one-off provider-specific generation/recovery workflows. StarBlox can turn one `artPromptOptimizer` recommendation into a deterministic job spec containing prompt SHA, seed, model revision, conditioning/reference inputs, dimensions and variant ID, then stage exact output bytes through the existing candidate/readback/render/review gates.
- Estimated build-time saved: **6–12+ engineering weeks** versus building and maintaining model loading, schedulers, batching, conditioning adapters and deterministic inference plumbing from scratch.
- Existing-pipeline integration surface: `scripts/artPromptOptimizer.mjs` recommendation JSON -> provider-neutral generation job -> versioned PNG + provenance JSON -> existing staged-art QA -> independent reviewer -> Workstream 08 canonical mapping only after ACCEPT.
- License / weight / data terms: Repository code is **Apache-2.0** at the pinned revision. Every selected FLUX/SDXL/base/refiner/ControlNet/IP-Adapter checkpoint remains a separate rights decision; pin exact model repo + revision + model-card/license in provenance before generating production candidates.
- Reuse classification: **STRONG / directly reusable code; generation blocked until chosen weights are rights-verified.**
- Concrete pilot: Build a local/offline adapter that consumes one current Aura REWORK recommendation and emits four fixed-seed variants plus machine-readable provenance. Use only a separately verified model checkpoint; no canonical write.

### 2. Tencent IP-Adapter — reference/style/item consistency without per-item fine-tuning
- Repository: https://github.com/tencent-ailab/IP-Adapter
- Commit / revision: `62e4af9d0c1ac7d5f8dd386a0ccf2211346af1a2`
- Capability: Lightweight image-prompt adapter supporting image variation, image-to-image, inpainting, SDXL, multimodal prompting and ControlNet-conditioned structural generation. The repository also contains training code and documents Diffusers/ComfyUI/InvokeAI integrations.
- Why it fits StarBlox: An independently accepted StarBlox asset can act as a visual reference for a related item/character while text still controls exact item metadata. That directly attacks catalog drift, palette-only siblings and inconsistent collection material language.
- Estimated build-time saved: **3–6 engineering weeks** versus building a reference-image conditioning path or training custom per-family adapters from scratch.
- Existing-pipeline integration surface: Add optional `referenceAssetHash/referenceImage`, adapter scale and reference-preprocess metadata to a generation job; preserve exact input hash so reviewer outcomes remain reproducible.
- License / weight / data terms: Repository code is **Apache-2.0**. Linked `h94/IP-Adapter` weights, CLIP/image encoders, base diffusion models and any fine-tuning dataset have separate terms and must be verified independently.
- Reuse classification: **STRONG / code directly reusable; weights conditional.**
- Concrete pilot: One accepted StarBlox-owned reference asset + one prompt-optimizer repair brief; generate fixed-seed variants at several adapter scales and compare exact-hash independent review outcomes against text-only generation.

### 3. InvokeAI — mature queue/API/workflow orchestration for a persistent art worker
- Repository: https://github.com/invoke-ai/InvokeAI
- Commit / revision: `9e1540962bcca7f8fa668d7d8e02cf79d75fda3b`
- Capability: Apache-licensed image-generation application/runtime with tested workflow/queue infrastructure. The inspected API exposes `/{queue_id}/enqueue_batch`; repository tests exercise batch enqueue behavior; current code also models IP Adapter, ControlNet and workflows.
- Why it fits StarBlox: If the art factory grows beyond a single script, InvokeAI can provide a durable local generation service/queue instead of StarBlox inventing its own daemon, retry state, job queue and graph representation.
- Estimated build-time saved: **4–8+ engineering weeks** for orchestration/API/queue/workflow infrastructure.
- Existing-pipeline integration surface: Art Factory queue -> InvokeAI batch endpoint -> exact generated output bytes + job IDs -> StarBlox candidate intake/provenance -> current render/review pipeline.
- License / weight / data terms: Repository code is **Apache-2.0**. Installed model checkpoints, optional external providers and any downloaded assets have independent terms.
- Reuse classification: **STRONG-OPTIONAL.** Prefer direct Diffusers first; adopt InvokeAI when persistent queue/workflow needs justify the larger dependency.
- Concrete pilot: After a direct Diffusers recipe is validated, submit a synthetic four-variant batch to a local InvokeAI instance and verify deterministic job/output provenance without touching canonical art.

### 4. PyMatting — fully rights-clean deterministic alpha-edge refinement
- Repository: https://github.com/pymatting/pymatting
- Commit / revision: `6d5c4a6bed0e5672abac0bad078e594423ffe4fd`
- Capability: Multiple classical alpha-matting algorithms plus foreground estimation, CLI, tests and documented CPU/GPU options. Current README reports pytest coverage and exposes a simple trimap-driven `pymatting` CLI.
- Why it fits StarBlox: It can refine fuzzy hair/fabric/glow/translucent edges after a foreground mask is available, without depending on opaque generated alpha or a hosted service.
- Estimated build-time saved: **1–3 engineering weeks** for robust edge refinement and foreground estimation utilities.
- Existing-pipeline integration surface: Candidate PNG + generated trimap/mask -> PyMatting -> transparent derivative -> exact SHA/readback -> card/detail render evidence. Keep original source bytes and provenance.
- License / weight / data terms: **MIT** code. Core algorithms do not require a learned model checkpoint; input images/trimaps remain StarBlox-owned/generated inputs.
- Reuse classification: **PILOT NOW / directly reusable.**
- Concrete pilot: Derive a trimap by eroding/dilating an existing foreground mask on 8 non-canonical candidate copies, refine alpha, and compare halo/edge quality in actual Store cards before any production adoption.

### 5. rembg — batch background removal and alpha-matting wrapper
- Repository: https://github.com/danielgatis/rembg
- Commit / revision: `202e42649a8492a7c49f808de36608a7d1cbbfe3`
- Capability: CLI/Python/HTTP/Docker background removal with single-file and folder batch modes, watch mode, alpha matting, mask-only output, color decontamination and CPU/GPU/ROCm paths.
- Why it fits StarBlox: It can make generated art catalog-ready as transparent PNGs and is easy to place between generation and exact-byte staging.
- Estimated build-time saved: **1–2+ engineering weeks**.
- Existing-pipeline integration surface: Raw candidate -> local rembg batch -> optional PyMatting refinement -> candidate intake/readback -> staged-art QA.
- License / weight / data terms: Repository code is **MIT**. Segmentation model weights are separately downloaded assets and must be rights-verified. Avoid optional hosted/commercial APIs in the StarBlox pilot; no API keys are needed for the local path.
- Reuse classification: **STRONG / code reusable; local weight choice conditional.**
- Concrete pilot: After verifying one local segmentation model's terms, process 8 non-canonical candidate copies and compare masks/edge decontamination with the current manual path.

### 6. Real-ESRGAN — alpha-aware super-resolution/restoration
- Repository: https://github.com/xinntao/Real-ESRGAN
- Commit / revision: `a4abfb2979a7bbff3f69f58f58ae324608821e27`
- Capability: Tested image restoration/upscaling with tiled inference, arbitrary `--outscale`, alpha-channel support, grayscale/16-bit support and explicit RGBA tests.
- Why it fits StarBlox: Source generations can be restored/upscaled before controlled downsampling to Store-card size while preserving alpha, useful when a candidate has good design but weak edge/detail resolution.
- Estimated build-time saved: **1–2 engineering weeks**.
- Existing-pipeline integration surface: Versioned source candidate -> optional restoration derivative -> preserve source + derivative hashes -> staged-art QA. Never silently replace the original generator output.
- License / weight / data terms: Repository code is **BSD-3-Clause**. Pretrained checkpoint weights remain separate artifacts; verify the exact chosen checkpoint/release terms.
- Reuse classification: **STRONG / code reusable; weights conditional.**
- Concrete pilot: Upscale then downsample 8 non-canonical candidates; compare actual Store-card readability and edge integrity against originals. Keep report-only until independent reviewers show a real acceptance gain.

### 7. ImageHash — low-cost perceptual duplicate/near-duplicate screen
- Repository: https://github.com/JohannesBuchner/imagehash
- Commit / revision: `7a405c9a27571ee8c998b661ce751639c34b7355`
- Capability: Perceptual image hashing with pHash/dHash/color hash/crop-resistant hashing, a real test suite and example similar-image tooling.
- Why it fits StarBlox: Reviewer feedback repeatedly penalizes recolor-only or template-like siblings. A cheap exact-SHA + pHash/dHash/colorhash nearest-neighbor report can reject obvious duplication before expensive render/reviewer cycles.
- Estimated build-time saved: **1–2 engineering weeks**, plus recurring reviewer time.
- Existing-pipeline integration surface: Run after exact-byte candidate intake and before/alongside staged-art rendering; compare candidate against canonical accepted art plus same-batch candidates. Start **report-only** and calibrate Hamming thresholds from accepted/rework history before any blocker is enabled.
- License / weight / data terms: permissive **BSD-style 2-clause** license; no model weights required.
- Reuse classification: **PILOT NOW / directly reusable.**
- Concrete pilot: Normalize Store-card candidates to a fixed canvas, compute exact SHA + pHash/dHash/colorhash nearest neighbors, record top 5 distances, and correlate warnings with reviewer `originality/duplicateVisual` failures.

### 8. scikit-image SSIM — independent structural-similarity signal
- Repository: https://github.com/scikit-image/scikit-image
- Commit / revision: `2dff163516e1a7c528b48d5eda8cf40788f0ade3`
- Capability: Tested Structural Similarity (SSIM) implementation; current repository includes parametrized multichannel SSIM tests.
- Why it fits StarBlox: SSIM is a useful second signal beside perceptual hash for detecting extremely similar silhouettes/layouts or measuring whether a transformation destroyed a known reference composition.
- Estimated build-time saved: **1–2 engineering weeks** for mature image metrics.
- Existing-pipeline integration surface: Report-only preflight sidecar after normalized card render; combine SSIM with pHash rather than making SSIM alone authoritative.
- License / weight / data terms: Main project files are **BSD-3-Clause** with documented BSD-family file exceptions; no model weights required.
- Reuse classification: **PILOT NOW / directly reusable, but heavyweight if used only for one metric.** Clean-room Node implementation from the published SSIM method may ultimately be a smaller dependency.
- Concrete pilot: Compare known duplicates, minor resizes/crops, accepted siblings and rejected recolors to calibrate a useful warning band.

### 9. LayerDiffuse Diffusers CLI — native transparent generation, conditional on model rights
- Repository: https://github.com/lllyasviel/LayerDiffuse_DiffusersCLI
- Commit / revision: `3061d9aed52a6c52a13fcf2b196c0fef4d727824`
- Capability: Official pure-Diffusers CLI implementation of latent transparency. The inspected SDXL demo uses a fixed `torch.Generator` seed, transparent VAE encoder/decoder weights and writes transparent PNG output directly; repository also supports transparent SDXL I2I and RGB padding.
- Why it fits StarBlox: Native alpha generation could eliminate a full background-removal stage for auras, companions, clothing and item renders, especially where soft glow/translucency is part of the asset identity.
- Estimated build-time saved: **2–4 engineering weeks** if the model stack's rights and quality prove acceptable.
- Existing-pipeline integration surface: Prompt-optimizer job -> transparent SDXL generation -> exact-byte PNG + seed/model/weight revisions -> candidate staging -> card/detail review; compare against rembg+PyMatting rather than assuming native alpha is superior.
- License / weight / data terms: Repository code is **Apache-2.0**. The demo downloads separate LayerDiffuse safetensors and uses an external SDXL base (`SG161222/RealVisXL_V4.0`); those model-weight terms were **not established by this GitHub code inspection** and must be verified independently before production use.
- Reuse classification: **WATCH / high technical fit, blocked on exact model-weight rights verification.**
- Concrete pilot: Once exact weights are cleared, generate four synthetic/non-canonical transparent assets at fixed seeds and compare alpha quality with rembg + PyMatting on checkerboard and actual Store-card backgrounds.

### 10. ComfyUI — strong workflow/API architecture, not the preferred rights-clean base
- Repository: https://github.com/Comfy-Org/ComfyUI
- Commit / revision: `e638023d54497dbe0579565e5de4bb7076899592`
- Capability: Mature graph/workflow image-generation runtime with a local `/prompt` API, websocket examples and execution/inference tests that queue prompts and track prompt IDs.
- Why it fits StarBlox: Excellent reference for reproducible graph workflows, queued generation and visual recipe composition; useful if human-authored node workflows become central.
- Estimated build-time saved: **4–8+ engineering weeks** for a node/queue/workflow environment.
- Existing-pipeline integration surface: Prompt compiler -> versioned Comfy workflow JSON -> local prompt queue -> candidate bytes/provenance -> existing intake/QA.
- License / weight / data terms: Repository code is **GPL-3.0** at the pinned revision, so it is not the preferred permissive foundation for StarBlox's embedded tooling. Under the user's separate repository permission it may still be usable, but public-license obligations and every custom node/model license remain separate and should be tracked. Model checkpoints are independent rights domains.
- Reuse classification: **WATCH / architecture reference or separately governed standalone service; Diffusers/InvokeAI are cleaner first choices.**
- Concrete pilot: None until the direct Diffusers path is evaluated; if later needed, run ComfyUI as an isolated local tool and keep versioned workflow JSON plus exact node/model manifest.

## Recommended StarBlox stack
1. **Immediate, no-weight preflight:** ImageHash + optional SSIM, report-only, calibrated against current exact-hash ACCEPT/REWORK history.
2. **Immediate alpha-edge experiment:** PyMatting on non-canonical copies where a trimap/mask already exists.
3. **Generation foundation after explicit model-rights gate:** Diffusers + IP-Adapter/ControlNet with fixed seed/model revision/provenance.
4. **Transparent output A/B test after rights gate:** native LayerDiffuse versus local segmentation + PyMatting.
5. **Optional restoration:** Real-ESRGAN only when actual card review shows measurable improvement.
6. **Scale-up orchestration:** InvokeAI if a persistent queue/service becomes necessary; ComfyUI remains an optional workflow-authoring environment rather than the default core.

## Highest-value next action
The safest accelerator to implement first is **perceptual preflight**, because it requires no model weights or paid services and directly addresses a recurring StarBlox reviewer failure class. Add exact-SHA + pHash/dHash/colorhash nearest-neighbor reporting to staged candidate QA, keep thresholds non-blocking, and measure whether warnings predict independent reviewer duplicate/originality REWORK. In parallel, define one provider-neutral generation provenance contract so future Diffusers/IP-Adapter pilots can enter the existing exact-hash review pipeline without special-case transport logic.
