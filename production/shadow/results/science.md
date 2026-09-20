# Scientific software / research-to-code shadow results

Append-only shadow log. These findings are NOT authoritative MASTER promotions.

## 2026-09-20 — Shadow Science Run 1

### Hypothesis
National-laboratory/research software that couples Bayesian-optimization recommendations to a durable experiment work queue and explicit **suggested-vs-actual execution provenance** is a more reusable and commercially meaningful kernel than another acquisition-function implementation. The operational handoff between what the model requested and what the laboratory actually ran should expose rare research-to-code value.

### Discovery modes
1. **Direct problem search:** self-driving/autonomous laboratory software, closed-loop experimental design, active learning + instrument/lab workflows.
2. **Code/invariant search:** queue lifecycle, `actual_inputs`, provenance IDs, acquisition strategy state, completion callbacks, concurrency guards, save/load round trips, CI/test signatures.
3. **National-lab/ecosystem adjacency:** NIST AFL software/paper lineage, national-lab organization repositories, low-attention scientific optimization projects, physical-lab comparators.

Triage also surfaced Frank-Gu-Lab/RAISE and several simulation-first SDL projects. Deep inspection was limited to NatLabRockies/ALchemist and the NIST AFL software split (`AFL-agent` + `AFL-automation`) as the principal comparator family.

### Best candidate
**NatLabRockies/ALchemist**  
Canonical URL: https://github.com/NatLabRockies/ALchemist  
Exact revision: `02c7a6eaa5a8e75bb65d0292b9b8d9a5e08301cf`  
Public license: BSD-3-Clause  
Repository attention at inspection: 8 stars / 5 forks  
Evidence snapshot id: `shadow-science-20260920-alchemist-02c7a6e`

### Frozen evidence manifest
- head revision `02c7a6e...`: merge explicitly adds per-experiment suggested-vs-actual provenance, durable session/audit records, and routes web completion through queue lifecycle;
- `alchemist_core/queue.py` blob `90226823427a7174ae1b33f132f6cde78bd3bd51`;
- `alchemist_core/session.py` blob `5e3f28ce62411d490f3cc22e76e4e1bea090b35c`;
- `tests/unit/core/test_provenance.py` blob `bfb40f86df330c3650366707d58249e839ded4f5`;
- `tests/unit/core/test_experiment_queue.py` blob `b2d4fc08e17eb797e59fd9f931381fa8ffe0b258`;
- `tests/unit/core/acquisition/test_botorch_acquisition_extended.py` blob `293c7c108edf1c04e69eca60a9ac5d576bee7bd8`;
- `.github/workflows/tests.yml` blob `aea32b5ec3e42d8d68c8d1bebabcf8c9efe272cf`;
- `README.md` blob `df113d1ba72e87895e49774c5c3cb394945f2181`;
- `LICENSE` blob `b1c602425e996119255e180f59b1e99832f6462d`.

### Load-bearing claims
**VERIFIED**
- The experiment queue is implemented as a thread-safe state machine (`pending/running/done/failed`) with per-item IDs, suggested inputs, optional actual inputs, outputs/noise/errors, timestamps and dataset references.
- Concurrent completion of the same queue item is explicitly guarded by a private claim set so the side-effecting completion callback is not run twice; a dedicated threaded regression test asserts exactly one callback execution.
- Queue completion writes the **actual** run conditions into the experiment dataset while retaining the originally suggested conditions and recording a provenance record containing strategy, suggested inputs, actual inputs, per-variable delta, output, noise and timestamp.
- Provenance survives session save/load, is deep-copied on read, and its hidden `ProvenanceId` is regression-tested not to leak into model features or BoTorch training/evaluation.
- The repository contains implemented/tested BoTorch acquisition paths including qEI, qUCB and qIPV, with batch selection, categorical-variable handling and configurable Monte Carlo samples tested against a catalyst fixture.
- CI runs the test suite on Ubuntu, Windows and macOS across Python 3.11, 3.12 and 3.13.
- Public provenance is BSD-3-Clause.

**CLAIMED / NOT ESTABLISHED BY THIS SNAPSHOT**
- README describes autonomous reactor-in-the-loop/automated-laboratory use and remote monitoring, but this run did not verify a physical instrument executor in ALchemist itself or a published physical closed-loop campaign driven by ALchemist.

**UNKNOWN / LIMITS**
- Production behavior across process crashes/network partitions and transactional persistence of queue state was not independently reproduced.
- The queue's `dataset_ref` is explicitly only an insertion-order snapshot, not a stable primary key; the stable provenance join is the `ProvenanceId` stored with the row.
- No independent benchmark was found proving ALchemist improves physical experiment throughput or sample efficiency relative to Ax/BoTorch-based custom orchestration.

### Why this matters
The individual Bayesian-optimization algorithms are not rare: BoTorch already supplies qEI/qUCB-style acquisition functions, and Ax provides a mature experiment/trial abstraction. ALchemist's differentiated kernel is the **execution-governance seam**: it preserves the difference between what optimization software suggested and what was actually run, carries that through a queue lifecycle, and protects the provenance metadata from contaminating model features. That is directly relevant to reproducibility, human/robot deviations, failed runs and scientific auditability.

This is especially interesting beside NIST's AFL family. NIST has a published physical validation of an autonomous formulation agent and an instrument-automation stack, while ALchemist contributes a newer, explicit suggestion→actual provenance contract that can sit above heterogeneous executors.

### Independent RED-TEAM / VERIFIER pass
Verifier input excluded the proposed score and used only the frozen evidence above plus public comparator evidence.

**Verdict: PASS_WITH_LIMITS.**

Reasons to pass:
- exact revision pinned;
- central provenance/queue capability exists in implementation, not README only;
- dedicated unit/integration tests cover the key data-flow and concurrency invariants;
- history shows the provenance feature was deliberately introduced as an operational lifecycle change;
- rights/deployment posture is unusually clear for research software.

Strongest objections:
1. **Commodity-algorithm risk:** qEI/qUCB/GP optimization are available directly in BoTorch/Ax. The commercial/scientific thesis fails if ALchemist is positioned merely as a Bayesian-optimization library.
2. **Physical-automation gap:** the repository exposes a queue/API designed for external equipment, but this evidence packet does not establish a native instrument layer or a real autonomous campaign.
3. **Persistence boundary:** thread-level duplicate-completion protection is tested, but process-crash exactly-once semantics and durable transactional queue storage were not established.
4. **Validation gap:** NIST AFL has stronger peer-reviewed physical experimental validation; ALchemist currently wins on integrated provenance/governance breadth rather than demonstrated closed-loop scientific outcomes.

Evidence that would upgrade the verdict: a reproducible physical campaign or hardware-in-loop integration test showing queue/provenance behavior across retries/restarts, plus a benchmark demonstrating that suggested-vs-actual capture prevents model/data corruption or improves campaign reproducibility.

### Proposed commercial score
A) speed to first revenue: **4/5** — integration/audit service can be sold before a full platform product.  
B) customer value / ceiling: **4/5** — meaningful for automated materials/process/formulation R&D, but buyer/ROI still needs field validation.  
C) build/domain compression: **5/5** — mixed-variable DoE + BO + API/UI + queue + audit/provenance is substantial engineering compression.  
D) rarity/advantage: **4/5** — algorithms are common; the suggested→actual execution provenance contract is less common and operationally important.  
E) evidence/completeness: **4/5** — strong source/tests/CI/history, no independent physical campaign reproduced here.  
F) rights/operability: **5/5** — BSD-3-Clause, packaged Python/REST architecture, cross-platform CI.  
**Total: 26/30 — STRONG_COMPONENT candidate, not a central promotion.**

### Commercial wedge
**Closed-Loop Experiment Governance Integration/Audit.** Buyer: automated materials, formulation, catalysis or process-development laboratory already using robots/reactors/instrument APIs. First paid wedge: connect the lab executor to ALchemist's queue, preserve each model suggestion and actual executed condition, export a reproducible campaign record, and flag suggestion→execution divergence before retraining. Money path is fewer invalid/wasted experiments, faster failure diagnosis and lower campaign-reconstruction/audit labor; exact ROI remains to be validated by the commercial lane.

### Comparator evidence
- `usnistgov/AFL-agent` @ `a1cc6e53438f6b0135c2e73d71fc260b9191029d`: modular active-learning pipeline framework; public NIST paper reports in-silico tuning followed by physical validation on a formulation-replacement problem.
- `usnistgov/AFL-automation` @ `eaf8905ac77f7f0ff285295f0b796d69b4375c73`: substantial DeviceServer/driver/queue/data infrastructure with real and virtual lab/beamline drivers; stronger physical-execution plane than ALchemist itself.
- `Frank-Gu-Lab/RAISE` @ `c3422c868ebf3fcfd8957cf560a3a6b71b023d91`: triaged as a promising physical formulation/vision/BO stack with campaign datasets, but not deeply verified enough in this run for a verdict.

### Local lesson
For autonomous-science repositories, generic `Bayesian optimization` searches over-select algorithm demos. Search the **decision→execution seam** instead: terms such as `actual_inputs`, `suggested`, `provenance`, `queue complete`, `audit`, `failed`, `retrain`, `save/load`, and concurrency/retry tests expose software that has crossed from optimization notebook to operational experiment control. This lesson has one successful shadow use and remains LOCAL.

### Cost proxies
- materially distinct discovery/search queries: ~13;
- deep inspections: 3 candidate/family inspections (ALchemist; AFL-agent; AFL-automation), with RAISE triage only;
- external GitHub/web reads/searches: ~50;
- reproducible untrusted-repository code executions: 0 (source/test inspection only).

## 2026-09-20 — Shadow Science Run 2

### Hypothesis
A stronger autonomous-science maturity signal than optimizer novelty is a **closed physical design→execute→measure→learn loop with recoverable campaign artifacts**. An independent implementation should contain both an actual lab-execution state machine and released evidence from a real multi-week campaign; if found, it should independently support LOCAL-1 while also exposing where decision→execution provenance still breaks.

### Discovery modes
1. **Direct domain search:** self-driving laboratory, autonomous experiment, protein/materials robotic closed-loop systems.
2. **Operational-seam code search:** proposal handoff, lab state, result polling, archive, retry/failure paths, sequence/result identity, save/load and campaign artifacts.
3. **Paper→code/ecosystem traversal:** recent autonomous-lab preprints and university releases back to exact repositories; comparison against generic lab orchestration and safety frameworks.
4. **Low-attention/current-release triage:** newly public and low-star research repositories were considered separately from established frameworks.

Serious candidates/comparators were limited to `RomeroLab/PRAXIS`, `AD-SDL/MADSci`, and `MaxNaeg/safe_lab_agents`.

### Best candidate
**RomeroLab/PRAXIS**  
Canonical URL: https://github.com/RomeroLab/PRAXIS  
Exact revision: `2441e471c3161542b50889f083da29d5b4deae73`  
Revision date: 2026-08-17  
Public license: Apache-2.0  
Evidence snapshot id: `shadow-science-20260920-praxis-2441e47`

### Frozen evidence manifest
- repository head `2441e471...`, initial public PRAXIS release;
- `README.md`: closed-loop protein-design/lab system, bundled benchmark datasets, released analysis/campaign assets, ProteinNPT/model dependencies;
- `environment/README.md`: physical robotic stack and five-state experiment progression;
- `environment/lab_controller.py`: implemented lab state machine, file watchers, sequence→pipetting workflow, EvaGreen filtering, plate-reader processing, sequence tracking, SFTP result return and timestamped archival;
- `agent/self_driving.py`: implemented model-acquisition loop, sequence dispatch to laboratory, phenotype monitoring, database update and subsequent acquisition round;
- `agent/phenotype_monitor.py`: phenotype-result monitoring/ingestion path;
- repository tree: hardware/auto-fridge firmware and fabrication files, assay/data-processing code, in-silico benchmark datasets/scripts, experiment database and round checkpoints through round 24;
- external paper: Brooks, Notin & Romero, *Learning protein function through autonomous experimental interaction*, bioRxiv 2026, DOI `10.64898/2026.08.14.744985`.

### Load-bearing claims
**VERIFIED / INDEPENDENTLY CORROBORATED**
- PRAXIS is not merely an optimizer: source contains a physical-lab controller with explicit `IDLE → SEQUENCE_RECEIVED → MONITORING_EVAGREEN → EXPERIMENTING → PROCESSING` lifecycle plus ERROR handling.
- The environment transforms requested sequences into automated pipetting/worklist inputs, watches experimental outputs, filters failed assemblies, processes plate-reader measurements, updates sequence tracking, archives run artifacts and returns phenotype data to the compute side.
- The agent side sends selected sequences to the lab, waits for phenotype output and feeds measured results back into the experiment database/model loop.
- The repository includes unusually rich operational artifacts: hardware/firmware files, assay-processing code, benchmark datasets, an experiment database, paper-analysis data and many sequential round checkpoints.
- The accompanying 2026 preprint independently describes the same closed loop and reports continuous operation for approximately one month, with multiple agents designing, physically constructing/characterizing and learning from protein variants.
- The code license is Apache-2.0. Paper/data/model-weight rights remain separate: the bioRxiv manuscript is CC-BY-NC 4.0, and external model weights/dependencies retain their own terms.

**LIMITS / FALSIFIED OVERCLAIMS**
- No conventional automated regression-test suite was found at the pinned revision; this is empirical research software, not a heavily tested production orchestrator.
- The lab controller uses useful local safeguards such as input-file hashing, sequence tracking and timestamped archives, but no durable transactional queue/outbox or restart-proof exactly-once experiment protocol was established.
- The agent transfer path does not establish a strong acknowledgement contract before phenotype polling; a failed dispatch can degrade into timeout/stall behavior rather than a cleanly persisted unresolved state.
- Unlike ALchemist, PRAXIS does **not** expose a first-class suggested-versus-actual execution record with per-variable deltas. Failed/filtered assemblies are handled operationally, but proposal→actual divergence is not preserved as an explicit governance object.
- Reproducing the physical loop requires specific robotic/vendor hardware and external model weights; repository publication does not imply rights to those independent assets or services.

### Independent RED-TEAM / VERIFIER pass
Verifier saw the frozen claims/evidence above without the proposed score.

**Verdict: PASS_WITH_LIMITS.**

Reasons to pass:
1. The model→physical-lab→measurement→model loop is visible in implementation, not only README text.
2. Physical execution is corroborated by released campaign/checkpoint/data artifacts and a matching 2026 bioRxiv report of roughly one month of autonomous operation.
3. Hardware, assay and data-return code materially reduce the chance that this is a simulation-only research demo.
4. The candidate independently supports the broader search thesis that execution-boundary artifacts are more discriminative than optimizer names.

Strongest objections:
1. **Reliability gap:** absence of a proper regression suite and durable crash/restart semantics makes PRAXIS a research-grade closed loop rather than a reusable production laboratory OS.
2. **Governance gap:** it proves real execution but does not explicitly record `suggested ≠ actual`, so it does not replace ALchemist's provenance kernel.
3. **Hardware specificity:** value is high for protein-engineering lab architecture but portability to other scientific domains is not automatic.
4. **Publication maturity:** the new PRAXIS result is presently a preprint; scientific claims should not be upgraded to peer-reviewed status.

The verifier therefore supports STRONG_COMPONENT status specifically for **physical closed-loop research-to-code and released campaign evidence**, not for production-safe orchestration or generic optimizer superiority.

### Proposed score
A) speed to first revenue: **3/5** — likely starts as specialized integration/reproducibility work, not a plug-in SaaS.  
B) customer value / ceiling: **5/5** — autonomous protein/biotech experimentation can compress months of scientist time and instrument idle time when it fits the lab.  
C) build/domain compression: **5/5** — model acquisition, gene/assay workflow, hardware control, result transport, archival and campaign artifacts encode years of cross-domain work.  
D) rarity/advantage: **5/5** — a public end-to-end physical protein-engineering closed loop with campaign artifacts is unusual.  
E) evidence/completeness: **4/5** — source + hardware + artifacts + matching preprint are strong; automated tests/restart guarantees are weak.  
F) rights/operability: **4/5** — Apache-2.0 code is clear, but hardware/vendor/model/data dependencies require separate diligence.  
**Total: 26/30 — STRONG_COMPONENT, not a central promotion.**

### Commercial / research implication
The reusable product is not “sell PRAXIS.” It is a **Protein SDL Reliability & Reproducibility Retrofit**: take a lab that already has robotic protein workflows and add explicit job identity, acknowledged dispatch, suggested→actual provenance, retry/restart state and campaign auditability around the existing design/test/learn loop. PRAXIS supplies a real physical reference architecture; ALchemist supplies the missing execution-governance contract; MADSci is a stronger generic orchestration comparator; Safe Lab Agents contributes a safety/isolation pattern.

### Comparator evidence
- `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0`: broad modular autonomous-discovery infrastructure with lab/resource/workcell/data/event managers and stronger generic orchestration separation; comparator for productionizing PRAXIS-like loops.
- `MaxNaeg/safe_lab_agents@e4a71147c219caf8867a135ab1fbd4c26e35d43b`: recent MIT framework/paper with sandboxed task compilation, controller isolation, simulated devices, validated workflows and preserved execution artifacts; stronger safety/reproducibility emphasis, weaker direct evidence of a multi-week physical campaign in this run.

### Search lesson outcome
LOCAL-1 succeeds a **second independent shadow run** in a different implementation family. Generic `self-driving lab` discovery found many framework/demo candidates, but following operational terms—lab state transitions, result return, archives, proposal dispatch, failure/retry boundaries—and then requiring physical campaign artifacts isolated PRAXIS. This makes the lesson eligible for **STAGED consideration inside the shadow program**, but no global `SEARCH_SKILLS.md` promotion is made here.

New negative lesson: physical scientific success does not imply software-governance maturity. A month-long autonomous campaign can coexist with weak transactional retry semantics and no explicit suggested-vs-actual record. Future searches should score **scientific closure** and **execution-governance closure** separately.

### Cost proxies
- materially distinct discovery modes: 4;
- search/code/paper queries and traversals: ~16;
- serious candidate/comparator inspections: 3;
- external GitHub/web reads: ~35;
- untrusted-repository code executions: 0 (source/data/history inspection only).

## 2026-09-20 — Shadow Science Run 3

### Hypothesis
The missing high-value quadrant in autonomous science is a **persistent experiment-intent ledger with retry-safe mutations that is actually used by physical closed-loop campaigns**. A strong candidate should preserve optimizer suggestions, actual submitted experiment conditions and provenance as distinct durable state; prevent logical duplicate mutations under retries/concurrency; and have credible physical-campaign evidence showing the same campaign state survives real operational interruption.

### Discovery modes
1. **Paper→code traversal:** followed the September 2026 *La Agente Óptima* preprint to its BO backend and released physical-campaign artifact repository.
2. **Executable-invariant search:** searched for `suggestion_id`, result linkage, provenance snapshots, partial unique indexes, idempotency reservations, cancellation cleanup, stale-owner handling, trace/audit events and replay tests instead of optimizer names.
3. **Physical-platform/ecosystem adjacency:** checked the RAISE physical orchestrator and RoboChem-Flex/RAISE campaign evidence to separate BO-state durability from hardware execution; low-attention MEDAL-LAB was triaged but not opened on `.env`/credential-shaped paths.
4. **History archaeology:** inspected commits that hardened cancellation, reservation TTL/heartbeat and campaign-version integrity.

Deep inspection was limited to `AccelerationConsortium/bo-mcp` as the reusable kernel, the `the-matter-lab/La-Agente-Optima-artifacts` campaign archive as corroborating evidence, and `Frank-Gu-Lab/RAISE` as a physical-execution comparator. No sensitive values were opened or retained.

### Best candidate
**AccelerationConsortium/bo-mcp**  
Canonical URL: https://github.com/AccelerationConsortium/bo-mcp  
Exact revision: `56d590b91ac120d0f22a3e41e770843d271808cd`  
Revision date: 2026-09-18  
Public license: MIT  
Repository attention at inspection: ~2 stars / 0 forks  
Evidence snapshot id: `shadow-science-20260920-bo-mcp-56d590b`

### Frozen evidence manifest
- `packages/bo-mcp-server/src/bo_mcp_server/idempotency.py` blob `6ae9bff5c80d8309a89aa402651308bd90f34409`;
- `packages/bo-mcp-server/src/bo_mcp_server/storage/models.py` blob `1156604c372a934eaa2044a95b8a362f64b29fde`;
- `packages/bo-mcp-server/src/bo_mcp_server/operations/submit_results_pipeline.py` blob `afd247eeb64f815b710e19a3e483667cb6726f81`;
- `packages/bo-mcp-server/src/bo_mcp_server/operations/update_suggestion_status.py` blob `c029131599475898b53bdaafcaf548623526c4ed`;
- `packages/bo-mcp-server/tests/unit/test_idempotency.py` blob `83bb85afb67c7fda3c8b2ebaad8f681e4fb9a601`;
- `packages/bo-mcp-api/tests/test_rest_results_replicates.py` blob `bb394a40588b46e6ca4a5c10d1b9d2770937dba4`;
- `packages/bo-mcp-server/tests/integration/test_suggestion_id_validation.py` blob `dd366fd4d2e76a1b7cbea023f2d81b52ef57baf4`;
- `packages/bo-mcp-server/tests/unit/test_storage/test_soft_delete_and_snapshot.py` blob `449206af826b9fa3736a96624760eef57be42739`;
- `LICENSE` blob `1a5a1523a7bbfde1270ceb97f082c00d836af06b`;
- history commit `90186a1a9f42ba76b3ac051fc0ab9acfbda61c2f` records cancellation cleanup, bounded reservation heartbeat and campaign-version integrity work; later `07f0200ad21951af8afed49dde8ae96130a104ad` is explicitly a data-integrity hardening commit;
- corroborating campaign archive `the-matter-lab/La-Agente-Optima-artifacts@45425bcbfc06b83330b0d4714f0dd363dbebdd73`: `showcases/README.md` blob `71562e6570fddeaaded8a040d0acb57e0c219a30`, RAISE showcase README blob `337365de4f7a86ceb62cfd535347117e7e89faaa`, RoboChem-Flex showcase README blob `a1a2893e63cef63fd5f0907a9b0ba2f0bef38f6e`;
- physical comparator `Frank-Gu-Lab/RAISE@c3422c868ebf3fcfd8957cf560a3a6b71b023d91`, `Orchestrator.py` blob `fec8b7f0b593fc4941e8a2af602c3f12836d2d67`;
- external research evidence: Müller et al., *La Agente Óptima: Towards Agentic Self-Driving Laboratories*, arXiv:2609.04564, submitted 2026-09-03; physical platform papers for RAISE and RoboChem-Flex are peer-reviewed 2026 publications.

### Load-bearing claims
**VERIFIED / TESTED**
- BO-MCP persists a first-class **Suggestion** with its own parameter values and provenance, and a **Result** with independently supplied parameter values plus optional `suggestion_id`. A suggestion-linked result additionally stores a durable `suggestion_snapshot_json` containing the originating suggested parameters and provenance, so the intent context survives later deletion of the suggestion row.
- The result pipeline explicitly states that parameter equality is **not** required when resolving a suggestion: replicate/actual measurements may use different parameter values. The actual result parameters therefore coexist with the immutable suggestion snapshot and can be compared after the fact. Snapshot persistence and survival of suggestion deletion are regression-tested.
- A partial unique database index allows at most one active Result per non-null `suggestion_id`; phase-1 validation rejects duplicate actionable references before the DB constraint, and suggestion completion uses guarded state transitions rather than blind last-writer-wins updates.
- State-mutating tools support a database-backed idempotency reservation protocol keyed by `(tool_name, idempotency_key)` with request hashing, reservation tokens, in-progress/conflict envelopes, stale-owner protection and same-session finalize support. Unit/integration tests cover cached replay, concurrent retries with exactly one logical side effect, payload conflicts, exception cleanup, `CancelledError`, actual task cancellation, double-cancellation cleanup and stale reservation recovery.
- REST result tests pin the practical contract: reusing the same idempotency key replays the same result IDs and does not double-count; CSV-upload retries also replay rather than insert another measurement. The replay is explicitly surfaced as `idempotency_replay=True`.
- Suggestion lifecycle updates use compare-and-transition semantics and write audit Event rows; trace IDs are attached at the storage layer so operation-level audit rows retain workflow correlation.
- The released Óptima artifact repository identifies BO-MCP as the persistent campaign/observation/action-state backend for seven showcase campaigns, including two physical self-driving laboratories. The RAISE showcase preserves one artifact directory per approved increment with BO-MCP campaign exports/run logs; the RoboChem-Flex showcase reports 23 physical experiments and a campaign continuation after workstation replacement.
- The current code is MIT licensed.

**INDEPENDENTLY CORROBORATED SCIENTIFIC CLOSURE**
- The September 2026 Óptima preprint reports evaluation on two physical platforms, including a five-day, 23-experiment flow-chemistry campaign that raised yield from roughly 30% to 59%, and a closed-loop RAISE contact-angle campaign with mid-run failure handling. This is recent preprint evidence for Óptima/BO-MCP campaign use, not peer review of BO-MCP's software invariants.
- RAISE's separate 2026 Digital Discovery paper independently establishes a real closed-loop formulation→robotic execution→imaging→measurement→BO system; RoboChem-Flex's 2026 Nature Synthesis paper independently establishes a modular closed-loop flow-chemistry platform. These papers validate the physical platforms, not BO-MCP's exact-once guarantees.

### Independent RED-TEAM / VERIFIER pass
Verifier input excluded the proposed score and used only the frozen source/test/schema/history packet plus the public campaign/paper evidence above.

**Verdict: PASS_WITH_LIMITS.**

Reasons to pass:
1. The core value is visible in source, database schema and dedicated adversarial tests rather than a README claim: durable experiment identity, suggestion/result provenance snapshots, guarded state transitions, cross-process idempotency and audit events.
2. The candidate closes much more of the execution-governance axis than PRAXIS and has stronger durable/retry semantics than ALchemist's thread-level queue protection.
3. Unlike a simulation-only BO service, the related released campaign artifacts and current preprint show the backend was used across two real physical SDL families and across workstation/session interruption.
4. The public repository is low-attention relative to the depth of its reliability and campaign-state machinery.

Strongest objections / limits:
1. **No physical exactly-once guarantee.** BO-MCP can prevent duplicate database/tool mutations, but it cannot prove an external robot did not physically execute twice after an ambiguous network failure. External dispatch acknowledgement/readback remains a separate system-of-record problem.
2. **Idempotency is opt-in.** The tests deliberately show that an unlinked resend without an idempotency key is stored again; client discipline or a mandatory gateway is still required.
3. **Proposed→actual is reconstructable, not yet a first-class delta alert.** The result stores actual parameters and a snapshot of suggested parameters, but no inspected code automatically computes/flags their difference as ALchemist does.
4. **Reference degradation can become free-floating data.** Invalid, missing or foreign `suggestion_id` values follow a warning-only path and may persist as unlinked results. That is useful for imports but weakens strict chain-of-custody unless a deployment hardens the policy.
5. **Reservation timeout edge.** Source comments acknowledge that a genuinely long operation can outlive a pending reservation window and risk duplicate execution if its heartbeat/extension no longer protects the slot.
6. **Publication maturity.** The Óptima system-level result is a September 2026 arXiv preprint; this run did not independently rerun the full test suite or reproduce a physical campaign.

The verifier therefore passes BO-MCP as an unusually strong **experiment-integrity / campaign-state kernel**, while rejecting the stronger claim that it alone provides hardware-level exactly-once autonomous experimentation.

### Proposed score
A) speed to first revenue: **4/5** — a reliability/chaos audit and integration gateway can be sold before a full laboratory OS.  
B) customer value / ceiling: **5/5** — duplicate/misattributed experiments and unreconstructable campaigns are expensive in automated R&D environments.  
C) build/domain compression: **5/5** — persistent campaign BO, suggestion/result identity, provenance snapshots, idempotency, lifecycle, audit, API/MCP and regression corpus compress substantial engineering/domain work.  
D) rarity/advantage: **5/5** — the combination of agent-facing BO state, data-integrity machinery and real physical-campaign evidence is unusual at this attention level.  
E) evidence/completeness: **4/5** — excellent source/schema/tests/history plus physical artifacts, but no independent test execution and the physical exactly-once boundary remains external.  
F) rights/operability: **5/5** — MIT code, Docker/API/MCP deployment path; third-party lab hardware/services/papers retain separate rights.  
**Total: 28/30 — MASTER_CANDIDATE-grade technical finding inside shadow only; no central promotion is made.**

### Commercial / research implication
The most defensible wedge is an **Autonomous-Lab Experiment Integrity Gateway & Chaos Audit**, not another BO product. Put a reliability boundary between agent/optimizer and laboratory executor: require stable experiment/business IDs and idempotency keys, preserve suggestion snapshots and actual submitted conditions, surface proposed→actual divergence, chaos-test retries/cancellation/restarts, and add an external execution-ack/readback adapter so ambiguous hardware dispatches enter an explicit unresolved state instead of being blindly retried. Buyer: SDL/platform engineering lead, automated R&D group, CRO/CDMO automation team, or lab-informatics owner. Money path: fewer duplicate/wasted runs, faster recovery, defensible campaign reconstruction and lower scientist/debug labor.

### Comparator / negative evidence
- `Frank-Gu-Lab/RAISE@c3422c868ebf3fcfd8957cf560a3a6b71b023d91` is genuine physical SDL software and peer-reviewed, but the public orchestrator itself does not supply BO-MCP's database idempotency/audit layer and notes that some client/credential-dependent pieces are outside the public code path.
- `Goldferret/MEDAL-LAB@856d20e0462e9faa3a0b3bc9855c0e2eb4b9449e` was low-attention and structurally interesting, but its public tree exposed `.env`-named paths; no such files were opened and it was not used for the result. Do not chase accidental exposure surfaces as a discovery strategy.
- ALchemist remains stronger on explicit per-variable proposed→actual delta records; PRAXIS remains stronger as a self-contained protein physical-loop reference. BO-MCP is the strongest of the three on tested persistent mutation/retry integrity.

### Search lesson outcome
The decision→execution seam strategy succeeds a **third independent shadow run**, and the useful discriminant is now more precise: search not only for `suggested`/`actual`/`provenance`, but for **experiment identity + persistence-boundary invariants** such as `suggestion_snapshot`, partial unique `suggestion_id` indexes, `Idempotency-Key`, reservation tokens, cancellation cleanup, stale-owner fencing, audit events and physical campaign exports. This separates operational scientific infrastructure from notebooks and optimizer wrappers.

New negative lesson: database exactly-once and scientific closure are still insufficient for **physical exactly-once**. Future searches should explicitly require an executor acknowledgement/readback or uncertainty/reconciliation state at the hardware/API boundary.

### VALUE HANDOFF
1. **Capability delta:** durable campaign state now includes a tested bridge from optimizer intent → actual result → preserved suggestion snapshot, plus retry-safe mutation and audit primitives.
2. **Graph edge:** conceptually bridges the gap identified by ALchemist (governance without physical proof) and PRAXIS (physical proof without durable retry governance); no central graph file was edited.
3. **Radar signal:** a third implementation family supports the emerging category **autonomous-science experiment integrity**, distinct from generic Bayesian optimization.
4. **Experiment impact:** enables a concrete falsifiable chaos suite: concurrent submit, lost response/retry, task cancellation, restart, duplicate suggestion reference, altered actual parameters and external-dispatch ambiguity.
5. **Commercial impact:** strengthens the first paid wedge from generic integration to a fixed-price Experiment Integrity / Recovery Audit with measurable duplicate-run, orphan-state, reconstruction-time and failed-retry KPIs.
6. **Negative knowledge:** never infer hardware exactly-once from an idempotent database/API; do not treat opt-in idempotency or warning-only foreign IDs as a strict provenance guarantee.

### Cost proxies
- materially distinct discovery modes: 4;
- code/paper/history/search traversals: ~18;
- serious candidate/evidence-family inspections: 3;
- external GitHub/web reads: ~40;
- untrusted-repository code executions: 0 (source/test/schema/history inspection only).

## 2026-09-20 — Shadow Science Run 4

### Hypothesis
The missing third axis after campaign-level provenance and idempotency is **external-effect closure at the physical executor**. A valuable scientific-control kernel should mark state non-authoritative before actuation, avoid declaring success until physical completion is established, and fail closed after cancellation/crash/ambiguous device state until authoritative readback or explicit reconciliation restores certainty.

### Discovery modes
1. **Direct physical-executor search:** laboratory robots, SiLA2 connectors, instrument command acknowledgement/result polling, recovery and reconciliation semantics.
2. **Executable-invariant search:** `command_execution_uuid`, result polling, `valid=False` before actuation, `clean_shutdown`, `reconcile physical`, `unknown`/`missing` hardware state, home/recovery gates, fsync/atomic ledger commits and cancellation tests.
3. **Protocol/ecosystem adjacency:** compared the low-attention Opentrons Flex connector against SiLA observable-command semantics and MADSci's broader workcell orchestration/error-handling model.
4. **History archaeology:** inspected the commit that introduced durable fail-closed labware movement/recovery and the later pinned-runtime hardening at repository head.

Deep inspection was limited to `AccelerationConsortium/opentrons-flex` as the candidate and `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0` as the principal generic-orchestration comparator. No untrusted repository code was executed.

### Best candidate
**AccelerationConsortium/opentrons-flex**  
Canonical URL: https://github.com/AccelerationConsortium/opentrons-flex  
Exact revision: `2639016ee9f234949aaf596c2ab2b93694eb0e0b`  
Revision date: 2026-07-22  
Public license: **none detected in repository metadata/tree**  
Repository attention at inspection: 2 stars / 1 fork  
Evidence snapshot id: `shadow-science-20260920-opentrons-flex-2639016`

### Frozen evidence manifest
- `src/unitelabs/opentrons_flex/io/labware_state.py` blob `c064b167806158b5149683ee918c799e4c8b2ace`;
- `src/unitelabs/opentrons_flex/io/labware_movement.py` blob `40bfcc59ea36a30ae452ab384727b85b818e49b6`;
- `src/unitelabs/opentrons_flex/io/recovery_state.py` blob `ba1f539be02fc78aa2e2cafb5d41aa79ace9237a`;
- `src/unitelabs/opentrons_flex/io/run_authority.py` blob `2c62a0d9ca82b274d6663c2e5554318b81f9e423`;
- `src/unitelabs/opentrons_flex/run_mutation.py` blob `2ddd8b4851c198787f027743cbfa779302da2ba1`;
- `tests/io/test_labware_movement.py` blob `a87bcbaf98437cd27548b241e8caf88eb4944bce`;
- `tests/io/test_shared_recovery.py` blob `78ea6f460f3953192ff55407209e04eee6387521`;
- `tests/integration/observable.py` blob `1b46192485a0aa352253fab283eba66aeb1c2623`;
- `.github/workflows/test.yml` blob `92b6d756e9f0f36d7f8342699c701545da0c6a75`;
- `README.md` blob `ff0b24982d86aa5fefbbd3f69a85cde3079135b3`;
- `pyproject.toml` blob `7ed6f75d8c6c8ebd5a1d5708e465f60003744ce8`;
- history commit `b2c39de3d588d7b5f9ba9a2c06f5b0a8b1eb7d94` introduced the durable location-to-labware identity ledger, fail-closed restart/cancellation recovery, raw-gripper bypass prevention and guarded real-hardware coverage;
- head `2639016...` deliberately narrows support to the validated Python 3.10 / Opentrons 8.8.1 runtime instead of claiming an unvalidated matrix.

### Load-bearing claims
**VERIFIED / TESTED IN SOURCE CORPUS**
- `LabwareMovementState.begin_move()` sets the durable deck model to `valid=False` and fsyncs it **before the first physical actuation**. `complete_move()` only writes the new source→destination occupancy after the movement returns and the controller re-checks operation generation and machine health.
- The durable state file is written via temp-file + flush/fsync + atomic replace + parent-directory fsync. If the post-move durable commit itself fails, the prior in-memory occupancy remains non-authoritative and `valid=False` rather than pretending the software state matches the physical deck.
- On startup, a previously unclean ledger is invalidated. `validate_move()` then refuses another move and explicitly requires physical-deck reconciliation/replacement of the local ledger before restart.
- Dedicated regression tests cover: cancellation during an in-flight physical move; gripper failure; unclean restart after `begin_move`; durable state restoration after a clean completed move; and disk/replace failure during the completed-move commit. In the ambiguous cases the next actuation is blocked rather than retried as if nothing happened.
- Cancellation/failure also raises shared recovery gates requiring full robot home and/or gripper-jaw home before further operation. A separate cross-controller test shows an emergency halt cancels active operations and gates gripper/calibration until recovery.
- Flex Stacker recovery combines explicit software quarantine with **authoritative polled hardware state**: unknown limit-switch values, `platform_state` of `unknown`/`missing`, or inability to read a known position all fail closed and require recovery. This is materially stronger than trusting local task completion alone.
- SiLA observable commands return a `CommandExecutionUUID`; the integration helper uses that same UUID to poll the command result and treats `Result is not ready` as non-terminal. This provides protocol-level execution identity/result readback, though it is not a durable business id across server-process loss.
- `ProtocolRunAuthority` re-reads the embedded Protocol Engine's authoritative run owner before direct actuation and retains the gate on state-provider failure while a run was known active. Run mutation holds prevent resume/play when validation or partial-enqueue uncertainty remains.
- CI runs unit + gRPC simulator tests and a combined HTTP robot-server + gRPC integration suite against the pinned Opentrons 8.8.1 stack. Real hardware/HITL suites are opt-in and the README explicitly refuses to call a hardware combination validated without serial/firmware evidence.

### Independent RED-TEAM / VERIFIER pass
Verifier input excluded the proposed score and used the frozen source/test/history packet plus the comparator observations above.

**Verdict: PASS_WITH_LIMITS.**

Reasons to pass:
1. The candidate closes the exact boundary that BO-MCP left unresolved: it models physical movement as uncertain before actuation, only commits known deck state after verified completion, and blocks future physical effects after ambiguous termination.
2. The strongest claims are covered by adversarial tests for cancellation, unclean restart and durable-commit failure, not only documentation.
3. Recovery can depend on actual device/sensor readback (`unknown`/`missing` states fail closed), so the design does not assume that a local coroutine outcome is authoritative physical truth.
4. The repository is unusually low-attention relative to its lab-safety/recovery depth.

Strongest objections / limits:
1. **Not physical exactly-once.** The design intentionally chooses safe uncertainty quarantine. After a crash it may know that the ledger is invalid without knowing whether the plate physically completed its move. Human/local reconciliation can still be required.
2. **SiLA command UUID lifetime is not a durable business-effect identity.** The inspected helper proves command/result correlation while the server retains the command; it does not establish cross-process forever-idempotency or dedupe of a reissued physical command after server loss.
3. **Coverage is uneven by operation.** The deepest durable known/unknown semantics are concentrated in labware movement, stacker recovery and guarded run mutation; not every motion/liquid command was proven to have the same crash-atomic contract.
4. **Physical validation is gated, not independently reproduced here.** CI exercises real vendor simulators and HTTP+gRPC integration; HITL tests exist but were not run in this shadow pass.
5. **Portability/maintenance risk.** The connector is deliberately pinned to Python 3.10 and Opentrons 8.8.1 and reaches vendor Protocol Engine/private surfaces. A vendor upgrade can break the control boundary.
6. **Rights clarity is weaker than prior science finds.** GitHub reports no public license and the tree has no detected LICENSE file. Under the user's standing repository-code authorization this does not block technical evaluation, but independent Opentrons/SiLA/Unitelabs dependencies, trademarks, hardware and services retain their own terms.

The verifier therefore passes this as a rare **physical-effect uncertainty/recovery kernel**, while rejecting any claim that it alone provides universal hardware exactly-once execution.

### Proposed score
A) speed to first revenue: **4/5** — a focused robot/workcell integrity audit can be sold without building a new SDL platform.  
B) customer value / ceiling: **5/5** — duplicated/ambiguous plate movement, lost deck identity and unsafe recovery can destroy samples, halt workcells or cause hardware incidents.  
C) build/domain compression: **5/5** — SiLA + robot-server coexistence, device locking, durable deck identity, recovery gates, module interlocks, simulator/HITL tests and mutation governance encode substantial domain work.  
D) rarity/advantage: **5/5** — explicit pre-actuation invalidation plus post-actuation reconciliation/readback semantics are uncommon in public scientific automation code.  
E) evidence/completeness: **4/5** — strong implementation/tests/history/CI, but no independent HITL execution in this run and semantics are not uniform across every command.  
F) rights/operability: **4/5** — repository code is usable under the user's asserted commercial authorization, but no public license was detected and the runtime is tightly pinned to vendor software/hardware.  
**Total: 27/30 — MASTER_CANDIDATE-grade technical component inside shadow only; no central promotion is made.**

### Commercial / research implication
Combine **BO-MCP at the campaign boundary** with this pattern at the executor boundary. BO-MCP can make optimizer/result mutations retry-safe; a physical executor should then mark its world model non-authoritative before a side effect, use device readback/recovery evidence to re-establish truth, and refuse blind replay when the final physical outcome is unknowable. The first paid wedge is a **Physical Lab Command Integrity / Recovery Audit** for robotized labs: fault-inject cancellation/restart/storage failure, identify commands that can be blindly duplicated, and retrofit explicit `KNOWN / UNKNOWN_NEEDS_RECONCILIATION / RECOVERED` state plus device-specific readback/home gates.

### Comparator / negative evidence
- `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0` is broader and more mature as a modular workcell/resource/node orchestration platform, with explicit connection/action/result-retrieval failure handling. In this run, however, it did not displace the candidate on the narrower invariant of **persisting uncertainty before a physical move and refusing reuse until the world is reconciled**.
- SiLA observable-command UUID/result semantics are useful correlation primitives, but protocol correlation alone is not sufficient physical-effect closure; the important addition is device/world-state reconciliation after ambiguity.

### Search lesson outcome
A new LOCAL extension of the execution-seam skill succeeds once: **search physical-effect closure, not just orchestration retries**. High-signal terms are `valid=False`/invalid-before-actuation, `clean_shutdown`, `reconcile physical`, `unknown`/`missing` device state, generation fences, `require_home`, fsync/atomic state commits, command UUID/result polling and tests that cancel after side effects begin. Keep this LOCAL until a second independent implementation confirms it.

### VALUE HANDOFF
1. **Capability delta:** the stack can now distinguish campaign/API idempotency from physical-world certainty and has a concrete pattern for quarantine/reconciliation after ambiguous robot effects.
2. **Graph edge:** conceptually closes the external-effect gap identified in BO-MCP Run 3 by adding executor-side known/unknown state and authoritative recovery evidence; no central graph file was edited.
3. **Radar signal:** adds independent evidence for an emerging **scientific execution integrity** layer beneath autonomous-lab orchestration, distinct from BO, LIMS and generic workflow engines.
4. **Experiment impact:** the next chaos suite can test crash after physical dispatch/before local commit, cancelled movement, stale/unknown sensors, storage commit failure, cross-controller emergency stop and only then authorize replay/recovery.
5. **Commercial impact:** strengthens the experiment-integrity wedge into a two-boundary audit—campaign idempotency plus device-world reconciliation—with KPIs such as ambiguous-command rate, duplicate physical-action rate, recovery MTTR, unreconciled deck-state incidents and scientist/operator intervention time.
6. **Negative knowledge:** command IDs, locks and simulator success are not enough; a physically mutating system needs an explicit policy for when local state becomes non-authoritative and what evidence is required to restore certainty.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate/comparator inspections: 2;
- source/test/history/standard traversals: ~20;
- external GitHub/web reads: ~30;
- untrusted-repository code executions: 0.