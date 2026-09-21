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

## 2026-09-20 — Shadow Science Run 5

### Hypothesis
A second independent physical executor should validate the `physical-effect closure` search lesson only if it distinguishes **pre-actuation rejection** from **post-actuation uncertainty**, blocks ordinary motion after an ambiguous physical effect, and requires fresh device/readback evidence or explicit physical reconciliation before trust is restored. A correlated command/event ID that exists only in process memory does not satisfy durable cross-process command identity.

### Discovery modes
1. **Direct problem search:** laboratory robot/instrument crash recovery, ambiguous command completion, device readback, unknown state and reconciliation.
2. **Executor-invariant search:** `recovery_required`, `position_uncertain`, `mark_actuated`, `UNKNOWN`, action/result IDs, result polling, homing gates, state serialization and restart persistence.
3. **Ecosystem/analog comparison:** contrasted PyLabRobot's device-driver semantics with MADSci's durable workcell orchestration + SiLA observable-command layer and NIST AFL automation patterns.
4. **History archaeology:** followed the September 8, 2026 PyLabRobot VSpin/Access2 driver upgrade that introduced the explicit semantic state machine and recovery behavior.

Deep inspection was limited to `PyLabRobot/pylabrobot` and `AD-SDL/MADSci`; `usnistgov/AFL-automation` was triaged as a scientific-automation comparator. No untrusted repository code was executed.

### Best candidate
**PyLabRobot/pylabrobot — Agilent VSpin + Access2 state/recovery kernel**  
Canonical URL: https://github.com/PyLabRobot/pylabrobot  
Exact revision: `697272d3591da6e5be1fcf70448479904e326904`  
Revision date: 2026-09-19  
Public license: MIT  
Repository attention at inspection: 537 stars / 194 forks  
Evidence snapshot id: `shadow-science-20260920-pylabrobot-vspin-697272d`

### Frozen evidence manifest
- `pylabrobot/agilent/vspin/_state.py` blob `db24590aaaa7fc4391e47a6487a7bcb8ef1598a7`;
- `pylabrobot/agilent/vspin/vspin.py` blob `9ef7a6c3c46d1d1b60979887c7f64b892e17433a`;
- `pylabrobot/agilent/vspin/access2.py` blob `b70275a3a9908cef239063e6f11689a59537882a`;
- `pylabrobot/agilent/vspin/vspin_tests.py` blob `216b60e0d5d526e9b7c0fcf98f67496c0f55aa35`;
- `pylabrobot/agilent/vspin/access2_tests.py` blob `25fb6818765522b7c50ad6c522555f8c4f40fd71`;
- `pylabrobot/events/bus.py` blob `f31bd65eee2c9e7fc6afba9f8a997e631cd56293`;
- `docs/user_guide/agilent/vspin/state-machine.md` blob `8f85341d31f41633d6ff2b12f56820fe7d22c0f1`;
- `LICENSE` blob `a5f97475174013facefefa03917b53e507ea0c7f`;
- history commit `f8894b6e7d27ed734ae35bf849759d2e2f926145` (2026-09-08), “Upgrade Agilent VSpin and Access2 protocol drivers (#1227),” introduced the inspected state-machine/recovery family; current head retains it.
- comparator: `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0`, especially `workcell_engine.py`, `action_types.py`, `sila_node_client.py` and SiLA command-execution tests/spec.

### Specialist passes
- **CODE INSPECTOR:** traced VSpin/Access2 guarded operations from state schema through actuation markers, failure handling, readiness checks and tests.
- **SYSTEMS/SCIENCE VALIDATOR:** checked that the state machine maps to real centrifuge/loader concepts and fresh controller queries rather than a UI-only status layer; inspected documentation boundaries around plate-resource truth.
- **ECOSYSTEM ANALYST:** compared PyLabRobot's executor-local semantics with MADSci's persistent workflow/action model and SiLA observable-command correlation.
- **COMMERCIAL ANALYST:** evaluated the failure mode as a recoverability/duplicate-effect problem rather than a generic automation feature.
- **RED-TEAM / VERIFIER:** independently challenged cross-process durability, physical exactly-once claims, event identity and recovery reset semantics before accepting a STRONG_COMPONENT verdict.

### Load-bearing claims
**VERIFIED / TESTED IN SOURCE CORPUS**
- VSpin and Access2 define explicit semantic machine-state schemas. Both contain a sticky `recovery_required` flag; Access2 additionally records transfer direction/phase and last confirmed teachpoint, while VSpin separately tracks connection, initialization, homing and current activity.
- A `TransitionToken` distinguishes whether a guarded workflow crossed the physical actuation boundary and whether position became uncertain. If a command fails before actuation, prior operation state is restored. If it fails or is cancelled after actuation, the driver marks recovery required and invalidates uncertain position knowledge (`vspin.at_bucket=None` or `Access2.last_teachpoint=None`).
- Ordinary VSpin motion is rejected unless connected, initialized, homed, idle and `recovery_required == False`. Access2's readiness path similarly refuses operation while recovery is required and then queries fresh controller status for faults/initialization/homing.
- The Access2 transfer path records phase progression and performs physical status checks around source plate presence, grip, destination motion, release and park. Documentation explicitly warns that after a post-actuation failure the physical plate may no longer match PLR's recorded resource assignment and instructs the operator to establish actual arm/plate/rotor/interlock positions before recovery.
- Documentation states that neither `setup()` nor reconnecting the same driver clears the recovery flag, and there is no public reset that simply declares an interrupted transfer safe.
- Regression tests cover post-actuation motion failure/cancellation and assert recovery-required/uncertain-position state. VSpin tests also assert a concurrent follow-on/stop path raises “requires recovery” once the owning operation fails after actuation.
- PyLabRobot's structured event layer generates a per-operation UUID and correlated `started/completed/failed` lifecycle events. Tests assert the same operation ID reaches the terminal event.
- Public code is MIT licensed, and the repository has a conventional pytest corpus.

**IMPORTANT LIMITS / FALSIFIED OVERCLAIMS**
- The VSpin/Access2 semantic recovery state is **session memory**, not a durable crash ledger. A new process constructs a default state; no inspected serializer/persistent store was found for `VSpinMachineState`/`Access2MachineState`.
- The event bus explicitly describes itself as synchronous and in-process. Its operation UUID is useful correlation metadata, but persistence is delegated to subscribers and the ID is not a durable idempotency/business-effect key.
- Therefore a process death after physical actuation can erase the local `recovery_required` flag. Reinitialization/homing may re-establish some controller state, but this packet does not prove a restart-safe “ambiguous physical effect remains quarantined until reconciled” contract for resource/plate identity.
- Physical exactly-once is not established. The strong behavior is **fail-closed within the live driver session after known post-actuation failure**, not universal crash-safe dedupe.
- The VSpin/Access2 upgrade is very recent (September 8, 2026); the repository is mature overall, but this specific semantic-recovery layer has limited field-history at the pinned date.

### Comparator result — MADSci exposes the complementary half-gap
`AD-SDL/MADSci` has a durable Workcell layer and stable `ActionRequest.action_id`. Its workcell state is persisted in Valkey, and if action dispatch throws before a response is received, the engine deliberately keeps the same action ID and queries `get_action_result()` because the remote action may have been created. After result-query retries are exhausted, MADSci emits `ActionStatus.UNKNOWN` rather than fabricating success. These are strong orchestration semantics.

However, the current SiLA node client tracks observable commands in an in-process `_running_commands` map; querying an untracked action ID returns `UNKNOWN`, and that client advertises no action-history capability. At the workcell layer, `UNKNOWN` ultimately marks the workflow failed. A later failed-workflow resubmission can therefore create a new physical action unless the underlying device/system-of-record independently resolves the old command. MADSci has the durable workflow half; PyLabRobot VSpin/Access2 has the richer executor-local physical-recovery half. Neither independently closes the full cross-process physical-effect contract.

### Independent RED-TEAM / VERIFIER pass
Verifier input excluded the proposed score and used only the frozen source/test/schema/history packet above.

**Verdict: PASS_WITH_LIMITS.**

Reasons to pass:
1. The actuation-boundary distinction is implemented in source and tested, not a README claim.
2. Recovery-required state is sticky during the live session and ordinary motion checks explicitly reject operation until recovery conditions are addressed.
3. Fresh controller readback is part of readiness/recovery reasoning, and the documentation explicitly distinguishes software resource assignments from physical truth.
4. The implementation is independent of the prior Opentrons-Flex stack and therefore provides a second implementation-family signal for physical-effect closure.

Strongest objections / limits:
1. **Cross-process durability fails the original strongest hypothesis.** Recovery state and operation identity are in memory; after process loss, neither supplies a durable business-effect record that proves what physical command might have executed.
2. **Event correlation is not idempotency.** `operation_id` is generated in-process for telemetry and has no inspected provider/device dedupe semantics.
3. **Readback cannot always reconstruct plate identity.** Controller status can establish motion/fault/home facts, but the docs correctly warn that physical plate location may diverge from the resource model after interrupted transfer.
4. **No independent hardware execution in this run.** Tests and documentation were inspected; no vendor device was exercised.
5. **Popularity reduces rarity.** PyLabRobot itself is established; the unusual signal is the newly added actuation-aware recovery semantics, not repository obscurity.

The verifier therefore passes this as a **STRONG_COMPONENT physical-recovery reference pattern**, but rejects any claim that it completes durable physical exactly-once or the full Run-4 next-test requirement.

### Proposed score
A) speed to first revenue: **4/5** — the semantics can anchor a focused instrument-driver/workcell failure audit.  
B) customer value / ceiling: **4/5** — preventing unsafe retries, plate-state corruption and recovery guesswork is valuable, though this driver family is narrower than a full lab OS.  
C) build/domain compression: **5/5** — real device protocol handling plus actuation-aware state machines, transfer phases, fresh status queries and regression tests encode substantial domain work.  
D) rarity/advantage: **4/5** — the pattern is unusual, but the repository is established and the key layer is recent.  
E) evidence/completeness: **3/5** — excellent source/tests/docs/history for live-session recovery, but the decisive crash-persistence boundary is absent and hardware was not independently exercised.  
F) rights/operability: **5/5** — MIT license and broad Python lab-automation ecosystem.  
**Total: 25/30 — STRONG_COMPONENT inside shadow; no central promotion is made.**

### Commercial / research implication
The strongest product concept becomes more specific: a **Scientific Instrument Uncertainty Firewall / Recovery Audit**. For each physically mutating operation, persist one business-effect ID before dispatch; bind it to the workflow step and native device/protocol execution ID; record `NOT_SENT / SENT_OUTCOME_UNKNOWN / SUCCEEDED / FAILED_NO_EFFECT / NEEDS_RECONCILIATION`; and require device-specific readback or operator-confirmed physical state before allowing a new command after ambiguity. PyLabRobot supplies a strong executor-local state-machine pattern; MADSci supplies a strong orchestration/action-ID pattern; BO-MCP supplies campaign idempotency/provenance. The missing reusable kernel is the durable bridge among all three.

### Search lesson outcome
LOCAL-2 now has a **second independent implementation-family success**, but the success is narrower than the original durability target. The high-signal invariant generalizes: distinguish failure **before vs after actuation**, retain an unresolved/recovery state after post-actuation failure, invalidate uncertain position knowledge, and block ordinary motion until fresh evidence restores confidence. This is now eligible for STAGED consideration inside shadow evaluation, but it must retain an explicit warning that in-memory recovery flags and telemetry UUIDs do not satisfy crash-safe physical-effect identity.

New negative lesson: orchestration durability and executor recovery are frequently split across layers. Search them separately, then inspect the handoff: a durable workflow ID with an in-memory device command map is still unsafe after process loss, while a strong device recovery state with no persistent operation identity also loses uncertainty on restart.

### VALUE HANDOFF
1. **Capability delta:** a second executor family confirms actuation-aware recovery as a reusable scientific-control primitive; MADSci adds the complementary durable workflow/action-ID side.
2. **Graph edge:** conceptually sharpens the missing link between BO-MCP campaign integrity and Opentrons-Flex physical uncertainty closure into a durable `workflow step ↔ business effect ↔ native device command ↔ readback/reconciliation` record.
3. **Radar signal:** independent PyLabRobot and Opentrons-Flex implementations now support an emerging **scientific physical-effect integrity** category beneath generic lab orchestration.
4. **Experiment impact:** the next falsifiable prototype is no longer “find any recovery state”; it is to crash between device write and acknowledgement, restart the process, and prove the same durable effect record prevents blind redispatch until native readback/reconciliation resolves the outcome.
5. **Commercial impact:** upgrades the audit wedge from generic recovery review to a concrete cross-layer qualification: identify every operation whose workflow ID, device command ID, physical-state evidence and retry policy cannot be joined after restart.
6. **Negative knowledge:** session-sticky recovery flags, event UUIDs and durable workflow records are each insufficient alone; the value sits in their cross-process binding.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate inspections: 2, plus one comparator triage;
- source/test/schema/history traversals: ~22;
- external GitHub/web reads/searches: ~30;
- reproducible untrusted-repository code executions: 0 (source/test/history inspection only).

## 2026-09-20 — Shadow Science Run 6

### Hypothesis
A cross-domain physical-AI/robotics runtime that durably records a REAL action before/through physical execution and, after process restart, seals an interrupted action as **outcome unknown** while blocking ordinary redispatch can provide the missing persistence half of the scientific physical-effect ledger. The hypothesis fails if the recovery state is session-local, if restart silently retries the physical action, or if no stable action identity survives the crash. A stronger “physical exactly-once” claim additionally requires authoritative device reconciliation of the original effect.

### Discovery modes
1. **Direct invariant search:** searched public robotics/scientific-control repositories for `outcome unknown`, `needs reconciliation`, `recovery required`, command IDs, post-restart gates and authoritative readback semantics.
2. **Scientific/national-lab workflow comparison:** inspected Bluesky QueueServer persistence/recovery as a control showing that durable work queues and stable UIDs alone do not prove physical-effect closure.
3. **Protocol/ecosystem adjacency:** compared SiLA/LabThings-style action APIs and cross-domain physical-AI runtimes for a durable action ledger plus ambiguous-effect state rather than another in-process action manager.
4. **History archaeology:** traced ROSClaw's durable rosclawd control ledger back to its introduction commit and inspected the current release/CI lineage.

Deep inspection was limited to `ros-claw/rosclaw` as the candidate, `bluesky/bluesky-queueserver` as the durable-orchestration comparator, and `labthings/labthings-fastapi` as an action-API comparator. No untrusted repository code was executed.

### Best candidate
**ros-claw/rosclaw — durable REAL-action uncertainty ledger/recovery gate**  
Canonical URL: https://github.com/ros-claw/rosclaw  
Exact revision: `027c66d907a82432be1b0ce7a0e3e8bbd33ff773`  
Revision date: 2026-09-17  
Release state at pinned revision: `1.3.0 Internal Alpha`  
Public license: MIT  
Evidence snapshot id: `shadow-science-20260920-rosclaw-027c66d`

### Frozen evidence manifest
- pinned commit `027c66d907a82432be1b0ce7a0e3e8bbd33ff773`; its signed release commit points to tree `104fc0d0f5a62776f5393c8d1fd523328a9c5928`;
- `src/rosclaw/daemon/service.py` blob `fa4ad8e62c547c348116d5dadb4f1bd904cc682a`;
- `src/rosclaw/daemon/ledger.py` blob `4de3f00c8de02cfe1e3a066724c6a206c2e747ea`;
- `src/rosclaw/kernel/contracts.py` blob `de3fdae0f7637a908fbc65c1772bbc0a54477caa`;
- `src/rosclaw/integrations/lerobot/execution/executor.py` blob `6fdb06c915e841176c87f2fab4ec1c956e00df94`;
- `tests/daemon/test_server.py` blob `beed5468a85e72b87d748fa3a847e888153e1960`;
- `tests/daemon/test_ledger.py` blob `a2ee135cd4c23c5f14c57d44e7472ce34b4299d7`;
- `.github/workflows/ci.yml` blob `cea3c62933470b7cded0c590a598d803f0736531`;
- `docs/SAFETY.md` blob `5b7ac5a8f47855859dae5e39975ae4989eea5faf`;
- `LICENSE` blob `0ec040c949060bfcf7067eff8a6e9244e5640967`;
- history commit `0db0d79ca08c2ff382e43e98fd1097880712c39c` — `feat(runtime): persist rosclawd control ledger`;
- main-branch protection at inspection required broad unit/regression/integration/product/ROS deployment checks; the checked release commit itself exposed no combined-status records through the connector, so CI configuration is VERIFIED while that exact commit's green-run status remains UNKNOWN.

### Specialist passes
- **CODE INSPECTOR:** traced `ActionEnvelope.action_id` through daemon job persistence, ledger reconstruction, restart terminalization, recovery gating, execution receipts and LeRobot command-delivery/feedback state.
- **SYSTEMS/SCIENCE VALIDATOR:** evaluated whether the pattern transfers to autonomous scientific executors; compared against Bluesky's durable orchestration and LabThings' action API to isolate the physical-effect-specific invariant.
- **ECOSYSTEM ANALYST:** separated generic ROS/action correlation from durable daemon-owned physical uncertainty state and inspected the fail-closed safety contract around REAL work.
- **COMMERCIAL ANALYST:** mapped the primitive to duplicate-effect/sample-loss/recovery risk in laboratory automation rather than positioning ROSClaw itself as a lab product.
- **RED-TEAM / VERIFIER:** independently challenged durability, automatic replay, device-native identity, authoritative readback, hardware validation and release maturity before the score was assigned.

### Load-bearing claims
**IMPLEMENTED / TESTED**
- `DaemonLedger` is an append-only SQLite event ledger with stable `entity_id`, a contiguous event sequence, HMAC-linked events, an independently signed head anchor, `PRAGMA synchronous=FULL`, atomic anchor writes and startup verification that fails closed on rollback, broken MAC chain or external mutation.
- The daemon restores persisted action jobs from that ledger at construction. Startup then scans unfinished `QUEUED`/`RUNNING` jobs instead of forgetting them across process death.
- When a persisted job was `RUNNING` and its `ExecutionMode` was `REAL`, restart does **not** replay it. Source assigns error code `DAEMON_RESTART_OUTCOME_UNKNOWN` with the explicit statement that the physical outcome is unknown, requests E-Stop, and requires operator review. `tests/daemon/test_server.py` asserts the unknown-outcome terminal state and E-Stop latch, including repeated-restart behavior.
- Runtime status exposes `recovery.required`, `recovery.action_ids` and `recovery.real_action_ids`; the safety/architecture docs require review before new REAL work after an unclean restart. This means unresolved physical uncertainty itself survives process loss as durable daemon state.
- The action contract is versioned around a stable `action_id`, and execution receipts separate scheduler/final state from error codes and evidence/trust state.
- The LeRobot single-step executor sends at most one command per step, distinguishes `PROTOCOL_ACKNOWLEDGED`, `DELIVERY_INFERRED`, `REJECTED` and `UNCERTAIN`, and verifies returned position/force/current/temperature/status feedback before declaring completion. Communication loss after dispatch is therefore not collapsed into “never sent.”
- Emergency-stop semantics likewise separate dispatch, driver acknowledgement and `physical_stop_observed`; tests include states where a stop was dispatched/acknowledged but not physically observed rather than calling it verified.
- CI configuration runs daemon/kernel tests across Python 3.11–3.13 plus a full regression suite and black-box/product boundaries. Branch protection enumerates those checks as required on `main`.
- Public code is MIT licensed.

**CLAIMED / PARTIAL / UNKNOWN**
- ROSClaw documentation presents the system as a broader Physical AI/robotics safety runtime. This shadow result relies only on the durable action/recovery kernel, not the broader product claims.
- The repository contains real-system/ROS acceptance artifacts, but this run did not independently reproduce a robot-in-the-loop crash exactly in the write-before-ack window.
- No inspected universal record durably maps every ROSClaw `action_id` to a vendor-native command/execution ID that remains queryable after both daemon and device-server restart.
- Recovery acknowledgement is an operator/safety gate. It does **not** generically re-query the original device and prove whether the interrupted action physically occurred.
- LeRobot feedback verification and E-Stop physical observation are strong operation-specific readback patterns, not a universal post-crash reconciliation engine for arbitrary REAL actions.
- The pinned release is explicitly Internal Alpha; field maturity and deployment evidence are materially weaker than the source/test breadth.

### Comparator / negative evidence
- `bluesky/bluesky-queueserver@f65224d73733039a15ca17185178bfb366b68ece` has mature Redis-backed persistent queue/history state, stable item UIDs and restart recovery. It is a useful scientific-orchestration comparator, but no inspected path in this run supplied ROSClaw's specific invariant of reconstructing an interrupted physical effect as durable `OUTCOME_UNKNOWN` and blocking blind replay until review.
- `labthings/labthings-fastapi@c33924d4d01027d2a29a020d3d7178da3c56fdff` provides a useful scientific-instrument action API/manager, but the inspected action-management pattern was process/thread oriented; no equivalent durable cross-process physical-uncertainty ledger was established here. This is negative evidence against equating an observable action API with crash-safe effect identity.

### Independent RED-TEAM / VERIFIER pass
Verifier input excluded the proposed score and used only the frozen source/test/schema/history packet above.

**Verdict: PASS_WITH_LIMITS for a durable physical-uncertainty persistence kernel; FAIL for a complete physical exactly-once/reconciliation system.**

Proof obligations and verdicts:
1. **Does process restart reconstruct the same durable action/effect record? — PASS.** The ledger and action IDs survive restart and unfinished jobs are restored.
2. **Does an ambiguous in-flight REAL action avoid automatic redispatch? — PASS.** The restart path terminalizes it as `DAEMON_RESTART_OUTCOME_UNKNOWN` instead of retrying it.
3. **Does the system fail closed after ambiguity? — PASS.** E-Stop is requested and recovery state gates further REAL work pending review.
4. **Is the persistent record tamper/rollback aware? — PASS_WITH_LIMITS.** HMAC chaining and a signed head anchor detect ordinary mutation/rollback, while the project's own safety documentation correctly notes that a privileged/root state owner remains outside that threat boundary.
5. **Can the system authoritatively resolve whether the original physical command happened? — FAIL GENERICALLY.** Some executors verify feedback and E-Stop has physical observation, but the recovery path itself does not universally query a device/system-of-record for the interrupted command's final effect.
6. **Is there a durable action→native-command join for every hardware path? — NOT ESTABLISHED.** Stable ROSClaw action identity is strong, but provider/device-specific execution identity is not proven as a generic persisted contract.
7. **Is production maturity established? — NO.** The release is Internal Alpha and no real-hardware crash-window reproduction was run in this shadow pass.

Strongest objection: the candidate solves the **“do not forget uncertainty and do not blindly retry”** problem, but not the harder **“prove what the device actually did and close the uncertainty automatically”** problem. Calling it physical exactly-once would be an overclaim.

### Proposed score
A) speed to first revenue: **4/5** — the kernel can be adapted into a focused integrity/recovery audit without replacing a lab's optimizer or LIMS.  
B) customer value / ceiling: **5/5** — blind redispatch after uncertain physical effects can duplicate samples, moves, dispenses or robot actions and cause expensive recovery/downtime.  
C) build/domain compression: **5/5** — durable event ledger, action identity, restart reconstruction, permits, recovery gates, receipt/evidence semantics and a large safety regression corpus compress substantial systems work.  
D) rarity/advantage: **5/5** — preserving `OUTCOME_UNKNOWN` across process death and blocking replay is a rarer public invariant than ordinary action IDs or job queues.  
E) evidence/completeness: **4/5** — unusually strong source/schema/tests/history/CI configuration, but no independent hardware crash-window execution and no generic authoritative reconciliation.
F) rights/operability: **3/5** — MIT code is clear, but the project is Internal Alpha and scientific deployments would require adapter work plus separate robot/vendor/protocol diligence.  
**Total: 26/30 — STRONG_COMPONENT inside shadow; no central promotion is made.**

### Commercial / research implication
The transferable product is a **Physical Effect Uncertainty Gateway / Autonomous-Lab Recovery Control Plane**. Persist one business-effect/action record before dispatch; if process death occurs after a command may have reached hardware, restart into `SENT_OUTCOME_UNKNOWN`, block replay/new conflicting work, then require a device-specific reconciliation adapter to query native command history, sensors or the system-of-record before transitioning to `SUCCEEDED`, `FAILED_NO_EFFECT` or `NEEDS_HUMAN_RECONCILIATION`. The immediate paid wedge is a fault-injection/recovery audit for automated labs and workcells: enumerate each physically mutating operation, crash between write and acknowledgement, and score whether identity, uncertainty, readback and retry policy remain joinable after restart.

### Search lesson outcome
LOCAL-2 receives a **third independent implementation-family success**, now from a cross-domain robotics runtime rather than another laboratory connector. This strengthens the transferable pattern while sharpening the caveat: the valuable persistence invariant is not “exactly once”; it is **durably remember that an external effect may have happened, prevent blind replay, and make reconciliation an explicit state transition**. Keep the lesson STAGED-eligible locally; do not edit global `SEARCH_SKILLS.md` from the shadow lane.

New negative lesson: a durable action ledger and a fail-closed `OUTCOME_UNKNOWN` state are still only half of physical effect closure. The next discriminator is whether the same durable effect record carries a native device execution ID or enough authoritative readback coordinates to resolve the original action without reissuing it.

### VALUE HANDOFF
1. **Capability delta:** adds a concrete cross-process pattern for preserving physical-action uncertainty and preventing automatic replay after daemon death; stronger than session-local recovery flags.
2. **Graph edge:** conceptually fills the persistence gap between BO-MCP/MADSci durable orchestration and PyLabRobot/OpenTrons executor-local recovery; authoritative device reconciliation remains the missing edge. No central graph file was edited.
3. **Radar signal:** a third independent implementation family supports an emerging **physical-effect integrity** layer that spans robotics and scientific automation rather than belonging only to one lab framework.
4. **Experiment impact:** the next falsifiable test can require the exact same durable business-effect ID to survive a crash after device write, then demand native readback before any retry is permitted.
5. **Commercial impact:** strengthens the audit wedge into a concrete reliability product with measurable ambiguous-effect count, blind-replay exposure, recovery MTTR, unresolved-effect age and duplicate-physical-action KPIs.
6. **Negative knowledge:** never equate `OUTCOME_UNKNOWN + block replay` with physical exactly-once; without authoritative device reconciliation, uncertainty is safely preserved but not resolved.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate/comparator inspections: 3;
- source/test/schema/history traversals: ~24;
- external GitHub reads/searches: ~35;
- untrusted-repository code executions: 0.

## 2026-09-20 — Shadow Science Run 7

### Hypothesis
The sudden emergence of agent-to-hardware standards should expose a reusable **AI hardware safety-envelope / effect-truth kernel** before the category becomes mainstream. A strong implementation should enforce declared safety limits before bytes leave the process, independently verify post-command physical state, and represent the difference between `NOT_SENT`, `SENT_AND_VERIFIED`, `SENT_BUT_DESYNCED`, and `SEND_OUTCOME_UNKNOWN`. The stronger H3 hypothesis additionally requires a durable business-effect/native-command identity that survives a crash and blocks redispatch until authoritative reconciliation; merely writing an audit line after failure is insufficient.

### Discovery modes
1. **Emerging-standard search:** followed the August 27, 2026 Model Hardware Standard research-preview announcement and searched for independent public implementations created immediately afterward.
2. **Executable invariant search:** looked for zero-byte refusal tests, pre-transport policy gates, sensor-based verification, `transmitted: unknown`, desync errors, fsync/hash-chained audit state, and restart behavior rather than relying on “hardware safety” README language.
3. **Protocol adjacency:** compared the new MHS-style implementations with SiLA observable-command/ErrorRecoveryService concepts, especially command-execution identity and recoverable-error handling.
4. **Low-attention ecosystem search/history:** inspected very new/low-star projects and commit timelines to distinguish an emerging technical category from a single repository.

Deep inspection was limited to `Abenor-Labs/Open-MHS`; `SCUT-ESA/open-mhs` and the SiLA/Siloxide ErrorRecoveryService surface were used as comparators/independent emergence signals. No untrusted repository code was executed.

### Best candidate
**Abenor-Labs/Open-MHS — AI-to-hardware safety envelope and effect-truth boundary**  
Canonical URL: https://github.com/Abenor-Labs/Open-MHS  
Exact revision: `92b04b023915ba7cdf2cac55eb58e86a3c94cc0d`  
Public license: Apache-2.0  
Repository attention at inspection: 3 stars / 1 fork  
Evidence snapshot id: `shadow-science-20260920-open-mhs-92b04b0`

### Frozen evidence manifest
- `open_mhs/drivers/base.py` blob `d0462af0c9d2aee3a6ac910949cd2895507981c7`;
- `open_mhs/server/routers/rpc.py` blob `7a2d9bdc027ce6d105865593fdd6ab7a5adc312d`;
- `open_mhs/server/audit.py` blob `4df3d0821bb6844496ab95049f4e9d034d3123a9`;
- `open_mhs/server/safety.py` blob `9542c062f673ddb96ad35b0875455e5191cad223`;
- `open_mhs/server/capability_schema.json` blob `fb14e387b4aa0c56ed6f39ce2de2359cd04e00ac`;
- `tests/test_driver_compliance.py` blob `e106d45f001cc7d3e404860e0ae878d7d128ed85`;
- `tests/test_safety.py` blob `bec04aaeff9bb7c484c1bdb85a3381607ac6be5f`;
- `tests/test_audit.py` blob `3f28d0f6e5e4784a97c51cf58a105aaa0e0e3650`;
- `.github/workflows/test.yml` blob `939b8f3f0bbe80ba680ed2df7e23e594cecdd461`;
- `README.md` blob `ed1431873ddd578f8fd4300875c22bb592f42adc`;
- `SECURITY.md` blob `6356704094e0c4836e6c1ae11762ced6be425334`;
- `LICENSE` blob `6f09b0f1c69f0c0c39794defc8cc11468ce0ffdb`.

External emergence evidence frozen for this run:
- official Model Hardware Standard site, https://modelhardwarestandard.com/ — limited research preview, initiated by Anthropic + HHMI Janelia, open-source release planned after preview;
- Reuters, 2026-08-27, “Anthropic unveils new framework allowing AI agents to operate physical devices”;
- `SCUT-ESA/open-mhs@c5b9b8a677d490777be38686b01ae6df467d3b27`, another independent public implementation created 2026-08-30/31-era and MIT licensed.

### Specialist passes
- **CODE INSPECTOR:** traced `mhs.write` from RPC policy evaluation through driver re-check, transport write, post-command feedback verification and audit outcome classification.
- **SYSTEMS/SCIENCE VALIDATOR:** separated simulator/fake-transport evidence from physical-hardware evidence and checked whether the repository itself admits the boundary.
- **ECOSYSTEM ANALYST:** compared the official limited MHS preview, two independent open implementations, and SiLA recoverable-command semantics for evidence of category formation.
- **COMMERCIAL ANALYST:** mapped the kernel to driver/workcell safety qualification rather than positioning the repository as an official MHS implementation or certification authority.
- **RED-TEAM / VERIFIER:** independently tested the frozen packet against pre-dispatch safety, post-dispatch truth, persistence timing, crash-window identity/reconciliation and physical-validation proof obligations before any score was assigned.

### Load-bearing claims
**IMPLEMENTED / TESTED IN SOURCE CORPUS**
- A capability tag is validated before a driver is used; `BaseDevice.write()` refuses sensor/unknown targets, human-confirmation violations and safety-envelope violations before transport. The server performs an independent policy evaluation before calling the driver, so there are two enforcement points sharing an evaluator but not a cached verdict.
- Rejection tests assert **zero transport transmissions and unchanged device state**, including a deliberately naive/unsafe driver behind the middleware. This is stronger evidence than an HTTP/RPC error alone.
- Conditional safety bounds resolve against freshly read sensor state rather than the previously commanded value, so an actuator command that failed physically cannot silently relax the envelope.
- After an accepted write, the driver polls a declared feedback sensor until the settle deadline. If the wire accepted the command but the physical/simulated state did not move, `StateDesync` carries commanded and observed values; tests assert that the transport did receive the command.
- The RPC audit path distinguishes materially different effect states: a policy refusal records `transmitted: null`; a verified/desynced write records the transmitted value and observation; a transport-side hardware error is recorded as `transmitted: "unknown"` rather than falsely claiming that nothing happened.
- `AuditLog` is append-only/hash-chained JSONL with flush + `fsync`; reopening a fresh writer resumes sequence/hash state from the previous file. Tests prove clean restart continuation and detect edited/deleted lines.
- The public repository is Apache-2.0 and extremely low-attention relative to the implementation/test depth.

**CLAIMED / PARTIAL / UNKNOWN**
- The README reports 372 tests, CI on Python 3.10–3.12 across Linux/Windows, simulation benchmarks and mutation testing. The test files/CI configuration exist, but this shadow run did not independently execute the whole suite, so aggregate pass counts remain CLAIMED rather than reproduced.
- The repository contains a serial/G-code transport, but the project's own roadmap explicitly states that real-hardware validation has **not** occurred: the serial path is tested against fake/loopback transport and all manipulation results are simulated.
- The registry is explicitly in-memory. A restart forgets devices; persistent “stale until re-announced” registry state is roadmap work.
- The audit chain is hash-chained but not signed; a writer with sufficient file access can rebuild it.
- Signed capability tags, per-device credentials and broader deployment hardening are planned, not current guarantees.

### Independent RED-TEAM / VERIFIER pass
Verifier input excluded the proposed score and used only the frozen source/test/schema/history packet plus the public-standard/ecosystem evidence above.

**Verdict: PASS_WITH_LIMITS for an AI-to-hardware safety-envelope / effect-truth component; FAIL for H3 physical exactly-once or crash-safe physical-effect recovery.**

Proof obligations:
1. **Are unsafe commands blocked before bytes are emitted? — PASS.** Two enforcement points exist and regression tests explicitly require zero transmissions/state change on refusal.
2. **Does success depend on measured state rather than only transport acknowledgement? — PASS_WITH_LIMITS.** Feedback sensors are polled and desync is explicit where a tag declares feedback; actuators without feedback return `verified: false` rather than fabricated certainty.
3. **Does the software distinguish pre-dispatch refusal from ambiguous/post-dispatch outcomes? — PASS.** The RPC path records `null`, concrete transmitted values/desync, and `"unknown"` for transport ambiguity.
4. **Is that classification durably append-only once recorded? — PASS_WITH_LIMITS.** The audit is fsynced and restarts continue the chain, but it is not cryptographically signed/externally anchored.
5. **Does the durable record exist before the dangerous external effect? — FAIL.** The audit line is written after `_guard_hardware(driver.write(...))` returns or throws. A process/power loss after device transmission but before the audit write can leave no durable record that the physical effect may have happened.
6. **Is there a durable business-effect/native-command identity that survives process death and blocks redispatch? — FAIL.** No inspected command/effect ledger reserves identity before dispatch, and the in-memory registry/write history does not survive restart.
7. **Can restart authoritatively reconcile the original device effect without resending it? — FAIL.** No generic post-crash command-history/readback resolver is implemented.
8. **Is physical-hardware safety validated? — NO.** The repository itself states real-hardware validation is roadmap work and warns that independent hardware interlocks remain necessary.

Strongest objection: this is honest and well-tested **safety middleware**, but the audit semantics occur too late to serve as the crash-safe effect ledger sought by H3. `transmitted: "unknown"` is valuable when the process survives long enough to record the exception; it does not close the write-before-audit crash window.

### Proposed score
A) speed to first revenue: **4/5** — a fixed-scope driver/workcell conformance audit can be sold before a full platform.  
B) customer value / ceiling: **4/5** — bounding unsafe AI commands and detecting desync protects expensive lab/robot hardware, though current market budgets are still forming.  
C) build/domain compression: **4/5** — capability schema, safety evaluator, two-layer enforcement, MCP/HTTP surfaces, audit semantics, feedback verification and adversarial tests save substantial integration work.  
D) rarity/advantage: **5/5** — the category is weeks old, the repo has only 3 stars, and the explicit effect-truth distinctions are unusually mature for such a new public implementation.  
E) evidence/completeness: **4/5** — strong source/tests/schema/history; no independent full-suite execution or physical-hardware validation.  
F) rights/operability: **4/5** — Apache-2.0 and conventional Python deployment are clear, but alpha status, in-memory registry and absent physical validation constrain deployment.  
**Total: 25/30 — STRONG_COMPONENT inside shadow; no central promotion is made.**

### Commercial / research implication
The credible first wedge is an **AI Hardware Safety Envelope / Driver Conformance Audit** for autonomous-lab vendors, robotics integrators and equipment OEMs. Translate a device manual/risk envelope into declarative capability limits; run an adversarial corpus that proves unsafe commands emit zero bytes; test clamp/confirmation/state-conditioned behavior; deliberately induce stuck-axis/desync/transport failures; and produce an effect-truth report distinguishing `NOT_SENT`, `SENT_VERIFIED`, `SENT_DESYNC`, and `SEND_OUTCOME_UNKNOWN`. Do not market this as official MHS certification while the official standard remains a limited preview.

The larger product still needs the Run-6 durability kernel in front of this middleware: persist a business-effect ID **before** transmission, then let the safety envelope decide whether dispatch is permitted and use device-specific readback/reconciliation to close ambiguous outcomes after restart.

### Comparator / emergence evidence
- The official Model Hardware Standard was announced August 27, 2026 as a limited research preview for safe AI control of scientific/manufacturing hardware, with open-source publication planned later. That establishes the category but not a public official spec yet.
- `SCUT-ESA/open-mhs@c5b9b8a...` independently appeared within days and exposes a separate MIT-licensed implementation with CI and real-instrument/VISA work in its public history. It was not deep-verified enough for a score here, but it is meaningful independent evidence that the category is already branching before the official spec is public.
- SiLA's ErrorRecoveryService/Siloxide surface shows a mature adjacent pattern: recoverable errors are associated with command-execution UUIDs and continuation options. This is useful protocol precedent, but this run did not establish a persisted cross-restart native-command recovery engine from it.

### Search lesson outcome
A new LOCAL lesson succeeds once: **search the external-effect truth table, then inspect when each state becomes durable relative to actuation.** High-signal questions are: Can the system prove `not sent`? Can it distinguish `sent + verified` from `sent + desynced`? Can it admit `send outcome unknown`? Is that uncertainty persisted **before** or only **after** the external effect? Does restart block replay and use authoritative readback to close it? This prevents a sophisticated audit trail from being mistaken for a crash-safe physical-effect ledger.

Keep this lesson LOCAL; one successful task is not enough for staged/global promotion.

### VALUE HANDOFF
1. **Capability delta:** adds a reusable pre-dispatch safety-envelope + post-dispatch truth-classification layer for AI-controlled hardware, with adversarial zero-byte refusal tests and sensor-based verification.
2. **Graph edge:** conceptually sits between agent/campaign intent (BO-MCP/MADSci) and the durable uncertainty/reconciliation layer (ROSClaw/Opentrons/PyLabRobot patterns). It does not replace either.
3. **Radar signal:** official MHS preview plus at least two independent public implementations within days is a strong early signal for an emerging **agent-to-hardware safety standard/middleware** category.
4. **Experiment impact:** the next chaos prototype can combine a pre-dispatch durable effect reservation with Open-MHS-style safety checks, then kill the process after the transport write but before audit and require post-restart device reconciliation before retry.
5. **Commercial impact:** creates a nearer-term service wedge—AI Hardware Safety Envelope / Driver Conformance Audit—while the broader exactly-once recovery control plane remains a larger product opportunity.
6. **Negative knowledge:** a fsynced audit record written **after** hardware I/O is not a durable pre-dispatch effect ledger; `transmitted: unknown` does not survive a process crash unless uncertainty was persisted before the write.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate inspections: 1 deep + 2 comparator families;
- source/test/schema/history traversals: ~20;
- external GitHub/web reads/searches: ~30;
- untrusted-repository code executions: 0.

## 2026-09-20 — Shadow Science Run 8

### Hypothesis
A public scientific/physical executor now reaches **effect-integrity Level 3**: it persists a business-effect identity before dispatch, durably binds that identity to the native device/provider execution identity, survives a crash after the external write but before acknowledgement, blocks redispatch after restart, and resolves the original effect by authoritative read-only device/system-of-record evidence rather than issuing a second physical command.

The hypothesis is falsified for a candidate if any of those links are merely architectural prose, process-local state, simulator-only behavior, or post-effect logging.

### Discovery modes
1. **Direct invariant search:** searched scientific-control, robotics and instrument repositories for `outcome unknown`, command receipts, command IDs, crash/restart recovery, reconciliation and authoritative readback.
2. **Protocol/ecosystem adjacency:** followed SiLA observable-command `CommandExecutionUUID` semantics and MHS-style agent-to-hardware projects looking for persistent command-history/readback across server/process loss.
3. **Low-attention/current implementation search:** inspected very small/new physical-AI and MHS-style repositories rather than popularity-ranked frameworks.
4. **Architecture→source/history falsification:** when an architecture document exactly matched Level 3, checked its declared implementation status, implementation owner, tests and commit history before accepting it.

Serious inspection was limited to three near-matches: `ioi-foundation/ioi`, `MacKenzieLuong/sparkle`, and `tongriyaotxt/open-mhs`.

### Result
**NO_FIND for Level 3.** The three strongest near-matches fail different proof obligations, and none is promoted to STRONG on the Level-3 claim.

### Near-match 1 — IOI physical-action architecture
Repository: `ioi-foundation/ioi`  
Exact revision: `93f34155295b3c6122d7eb000cbe0333cc5a4f0b`  
Public license: Apache-2.0  
Attention at inspection: 2 stars / 0 forks

**Why it looked exceptional:** the canonical physical-action architecture names exactly the desired objects: controller idempotency keys, actuator receipts, ambiguous-effect reconciliation, local runtime assurance and an execution lifecycle that reconciles mission outcomes after actuation.

**Why the claim fails:** the canonical `physical-action-safety.md` explicitly labels implementation **partial admission precursor** and states that `PhysicalActionExecutionCore`, native controller mount, durable Agentgres receipt emission, cryptographic controller identity, controller-side idempotency and estate-wide coverage **remain planned**. History confirms the implemented work is admission-layer durability: commit `b2cc3025ad43cbf3653886e3ac7bfd0b4da26503` moves physical-action-intent admission into the Rust daemon, while `ceeb44235f40b98357a0fe493594a1dd5ddaa758` makes planner admissions durable and explicitly distinguishes durable admission from executing the admitted decision.

**Verifier verdict: FAIL for Level 3 / PLANNED ARCHITECTURE.** This is useful prior architecture, not evidence that the external physical effect contract is operational.

### Near-match 2 — Sparkle command receipts
Repository: `MacKenzieLuong/sparkle`  
Exact revision: `a9b4e38bfbfb0926723460c63cc4355b1bfabfc0`

**Implemented/tested:** the `/direct` command path accepts a caller `commandId`; a repeated identical request returns a duplicate receipt rather than starting another navigation command, `/commands/{command_id}` exposes the receipt, and integration tests cover this behavior. The control loop also contains strong runtime safety tests for stale perception, watchdog stop, late inference discard, rotation budgets, time limits and “no motor writes after stop.”

**Decisive failure:** command receipts live in the process-local `ControlLoop` receipt map. No inspected durable store or restart test preserves the command/effect identity. A process crash therefore destroys the dedupe evidence needed for Level 2/3.

**Verifier verdict: FAIL for Level 3 / SAME-PROCESS IDEMPOTENCY ONLY.** Good runtime control discipline, but not crash-safe effect identity.

### Near-match 3 — tongriyaotxt/Open-MHS cerebellum
Repository: `tongriyaotxt/open-mhs`  
Exact revision: `61ced4d976dd192623cfc715139a061783972cae`  
Public license: MIT  
Attention at inspection: 9 stars / 2 forks

**Implemented/tested:** this independent Open-MHS implementation has a genuine local-control “cerebellum” layer: reflex checks execute before the skill action each control tick; tests show obstacle/fall reflex abort, disturbance detection and correction, force-feedback grasp, DMP demonstration fitting/generalization, autonomous habit execution with reflex priority, and Microduck deadman/safety tests. An episode recorder writes observation/action/next-observation trajectories and camera-frame references to disk. Commit `3ea342e17ac8ffa3380f0e9d49dadfda75a9490f` introduced the cerebellum/Microduck/MuJoCo family.

**Decisive failures:** `BaseDevice` last-read/last-write state is in memory and a write is recorded only after `_do_write` returns; there is no durable pre-dispatch effect/native-command ledger. The repository also explicitly calls itself early alpha, says real-hardware testing remains needed, and its scientific lab adapters (microscope, liquid handler, centrifuge, laser, spectrometer) are simulated. This is therefore a useful **local reflex/control and imitation-learning kernel**, not a Level-3 physical-effect executor.

**Adjacent WATCH score:** A 3 / B 3 / C 4 / D 3 / E 4 / F 5 = **22/30 WATCH_COMPONENT** for portable local reflex/control + learning architecture; no STRONG promotion.

### Frozen evidence packet
- `ioi-foundation/ioi@93f34155295b3c6122d7eb000cbe0333cc5a4f0b`:
  - `docs/architecture/foundations/physical-action-safety.md` — canonical implementation-status statement: partial admission precursor; controller-side idempotency/execution core/durable execution receipts remain planned;
  - history commits `b2cc3025ad43cbf3653886e3ac7bfd0b4da26503` and `ceeb44235f40b98357a0fe493594a1dd5ddaa758` — durable physical-action admission, explicitly not equivalent to execution.
- `MacKenzieLuong/sparkle@a9b4e38bfbfb0926723460c63cc4355b1bfabfc0`:
  - `backend/server.py` — process-local receipt map and command duplicate logic;
  - `backend/test_integration.py` blob `cde5ff695cd7b7f9df4586ce17d3f4a8170c9ade` — duplicate `commandId` receipt test;
  - `backend/test_server.py` blob `956e4cbf277a3ce48c14d05000a5c0c573345a90` — deadman, stop and bounded-control regression corpus.
- `tongriyaotxt/open-mhs@61ced4d976dd192623cfc715139a061783972cae`:
  - `src/openmhs/core/device.py` — in-memory last-read/last-write state and post-return write recording;
  - `src/openmhs/cerebellum/reflex.py` blob `edf2e51ef1d31beb80b5da2f1dd69f67e46fae42`;
  - `tests/test_learning.py` blob `a06df7def27a306235aebbcf92a118ae42b804d0`;
  - `src/openmhs/cerebellum/episode.py` blob `d200ea82f5fdd0be5ca5d734d01e8eb75fd331cf`;
  - `tests/test_microduck.py` blob `adff954220161a5115107d7a92cbc27161db4739`;
  - `src/openmhs/adapters/lab/__init__.py` blob `894bf6b7fef85b3ecd0a7f86c8a2b03b66685071` — lab adapters explicitly simulated;
  - `README.md` blob `93e4e6905403dc876c4665565f0fb00851768a39` — early alpha and real-hardware-testing caveat;
  - history commit `3ea342e17ac8ffa3380f0e9d49dadfda75a9490f` — cerebellum/Microduck/MuJoCo introduction.

### Independent RED-TEAM / VERIFIER
The verifier received the frozen evidence packet without a proposed overall score and evaluated six Level-3 proof obligations:

1. **Durable business/effect identity persisted before dispatch? — FAIL across the inspected set.** IOI describes the target but marks its execution core planned; Sparkle receipts are memory-resident; Open-MHS records device write history in memory after the device method returns.
2. **Durable mapping to native device/provider execution identity? — FAIL / NOT ESTABLISHED.** SiLA UUID-style correlation exists in the wider ecosystem, but none of these candidates proves the required durable join through restart.
3. **Crash after external write/before ack restores the same effect record? — FAIL.** No inspected candidate supplies a tested end-to-end crash-window recovery with the same physical effect record.
4. **Redispatch remains blocked while outcome is unresolved? — FAIL GENERICALLY.** Prior ROSClaw/Opentrons findings cover much of this Level-2 property, but none of the new candidates advances it to Level 3.
5. **Authoritative read-only post-crash query resolves the original command without resend? — FAIL.** No qualifying implementation found.
6. **Implementation/test/history evidence rather than docs-only claims? — PASS as a falsification discipline.** The strongest apparent hit, IOI, was correctly rejected after its own canonical implementation-status and history were inspected.

**Overall verifier verdict: NO_FIND / HYPOTHESIS NOT YET SATISFIED.** Do not weaken the requirement or relabel planned architecture as an implemented kernel.

### Commercial / research implication
The gap remains commercially meaningful. A **Level-3 External Effect Qualification / Chaos Harness** can test each physical mutation for one invariant chain:

`durable business-effect ID reserved pre-dispatch → native device/provider operation ID → crash after write/before ack → restart with redispatch forbidden → authoritative read-only query → SUCCEEDED or FAILED_NO_EFFECT`

If the provider/device cannot supply the last query, the operation must remain `OUTCOME_UNKNOWN / NEEDS_HUMAN_RECONCILIATION` rather than be automatically retried. This can be sold as a reliability/qualification audit before attempting a universal control-plane product.

### Search lesson outcome
New LOCAL candidate lesson: **planned-vs-implemented collapse check**. When architecture/spec text perfectly matches a target invariant, immediately inspect its explicit implementation-status declaration, owning source path, executable tests, persistence timing and history. Run 8 rejected the most seductive near-match precisely because the canonical document said the hard execution pieces remain planned. One success only: keep LOCAL, do not stage or promote globally.

New negative lesson: a tested command receipt/deduplication API can still be entirely process-local. Always inspect the backing store and an actual restart/crash test before calling command identity durable.

### VALUE HANDOFF
1. **Capability delta:** no new Level-3 executor found; `tongriyaotxt/open-mhs` adds a useful WATCH-level local reflex/control + DMP/imitation kernel, but does not close external-effect durability.
2. **Graph edge:** the missing edge remains the durable join `workflow/business effect ↔ native device command ↔ authoritative post-crash readback`; IOI is architectural prior art, not implementation evidence.
3. **Radar signal:** agent-to-hardware control continues to branch quickly, but current public projects still separate local safety/control, durable orchestration and provider/device reconciliation rather than unifying all three.
4. **Experiment impact:** preserve the Level-3 crash test exactly; do not relax it to “has command IDs” or “has receipts.”
5. **Commercial impact:** reinforces a qualification/audit wedge because the same failure gap recurs across unrelated stacks.
6. **Negative knowledge:** reject planned execution cores, process-local receipt maps and simulation-only device layers as substitutes for crash-safe authoritative effect reconciliation.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate deep inspections: 3;
- source/test/history/protocol traversals: ~22;
- external GitHub searches/reads: ~30;
- untrusted-repository code executions: 0.

## 2026-09-20 — Shadow Science Run 9

### Hypothesis
A transferable effect-integrity **Level-3 kernel** is more likely to be fully implemented in an adjacent external-effect domain with a stable provider system of record—especially payments/refunds—than in current public lab robotics. The qualifying pattern need not know the provider-native operation ID before acknowledgement if it durably reserves the business effect before dispatch, sends a stable external reference/idempotency key with the mutation, survives ambiguity/restart without blind replay, and can later resolve the original effect through an authoritative read-only provider query rather than issuing another mutation.

### Discovery modes
1. **Cross-lane referral traversal:** followed the existing AI shadow referral to `auths-dev/auths-proof` because it specifically claimed Stripe refund `OutcomeUnknown` plus provider readback.
2. **Direct adjacent-domain search:** searched payment/refund/external-effect implementations for durable reservation, `OutcomeUnknown`, reconciliation, deterministic idempotency, provider lookup and no-resend recovery semantics.
3. **Code-invariant search:** looked for reservation state machines, persistent backing stores, restart tests, `ReconciledCommitted/ReconciledReleased`, exact business metadata, provider idempotency headers, and read-only reconcile paths.
4. **Comparator/history pass:** compared against `flyingrobots/echo` durable external-action settlement and `hyeonsangjeon/polaris-agent` durability/crash-test structure, then inspected auths-proof feature history to distinguish implemented machinery from roadmap prose.

Deep inspection was limited to `auths-dev/auths-proof` as the candidate and `flyingrobots/echo` as the principal external-action comparator; `hyeonsangjeon/polaris-agent` was triaged but not used for the final claim.

### Best candidate
**auths-dev/auths-proof — Stripe bounded-refund reservation + ambiguous-outcome reconciliation kernel**  
Canonical URL: https://github.com/auths-dev/auths-proof  
Exact inspected revision: `34fa1f33cf365fa54075a2002710aee52ab42394`  
Public package license: `MIT OR Apache-2.0`  
Repository attention at inspection: 0 stars / 0 forks  
Evidence snapshot id: `shadow-science-20260920-auths-refund-level3-34fa1f33`

### Frozen evidence manifest
- `product/integrations/auths-stripe/src/reservation.rs` — durable reservation state machine with `Reserved`, `Committed`, `Released`, `OutcomeUnknown`, `ReconciledCommitted`, `ReconciledReleased`; crash-persistent/cross-process store; exact reservation fields including workflow/action digests and idempotency-key digest; restart regression `persistent_state_survives_restart_and_is_canonical`;
- `product/integrations/auths-stripe/src/bounded_service.rs` — durable reservation/execution intent before provider mutation; replay/conflict handling; provider `OutcomeUnknown` transition; reconcile entrypoint restricted to ambiguous state;
- `demos/stripe-refund/src/stripe.rs` — one mutation path to Stripe refunds using a deterministic `Idempotency-Key`; exact Auths/workflow metadata is attached to the request; network-send ambiguity maps to `PortError::OutcomeUnknown`; reconciliation uses a read-only refund listing/query and matches stable workflow metadata plus amount/currency rather than sending a second refund;
- `demos/stripe-refund/src/app.rs` — regression `exact_refund_executes_once_and_replay_fails_closed`; regression `ambiguous_stripe_response_holds_budget_until_reconciliation` keeps the reservation active, reconciles it to committed, and asserts the Stripe mutation-call count remains exactly one;
- `docs/specs/0012-stripe-bounded-refunds.md` — status `Implemented`; documents the same ordered reserve→intent→provider mutation→receipt/commit flow and states that restart treats `reserved` as potentially ambiguous because process failure can occur during provider I/O;
- history: `4e44d0a0795947fc50229b3093c6168f6628f59a` introduced the shared durable Stripe lifecycle; subsequent qualification/replay hardening commits retain the pattern through the inspected revision;
- root workspace metadata at the inspected revision declares `MIT OR Apache-2.0` and both license texts are present.

### Load-bearing claims
**IMPLEMENTED / TESTED IN SOURCE CORPUS**
- Refund capacity/business intent is durably reserved before credential acquisition/provider mutation. The persistent reservation records workflow/action identity, exact amount/account/currency context, budget intents, state and a digest of the provider idempotency key.
- The reservation API explicitly treats both `Reserved` and `OutcomeUnknown` as reconcilable because a process can die during provider I/O after the request may have reached the provider but before local state advances.
- `PersistentRefundReservationStore` is explicitly crash-persistent and cross-process locked. A restart regression reserves state, drops/reopens the store, recovers the same `Reserved` record and transitions it through reconciliation rather than creating a new reservation.
- The Stripe mutation carries a deterministic `Idempotency-Key` plus stable Auths/workflow metadata. A transport/send uncertainty maps to `OutcomeUnknown` instead of “no effect.”
- The live reconcile path is **read-only**: it queries existing refunds for the original charge and matches the fixed workflow reference plus amount/currency constraints. It does not issue a second refund mutation.
- The ambiguous-response regression keeps the budget reservation active and then reconciles to committed while asserting the Stripe mutation call count stays **one**. The exact-refund replay regression similarly asserts a second logical execution does not perform another provider mutation.
- Source/history/specification agree on the same semantics, so this is not a documentation-only architecture target.

### Comparator / negative evidence
- `flyingrobots/echo` implements a strong generic durable external-action settlement model with explicit `OutcomeUnknown`, claim/settlement states and a rule that recovering a claimed action creates a reconciliation obligation rather than permission to repeat it. In this run, however, no provider-specific authoritative readback adapter comparable to the Stripe refund lookup was established, so Echo remains a Level-2/general-framework comparator rather than the qualifying Level-3 transfer example.
- `hyeonsangjeon/polaris-agent` has extensive journal/recovery and crash-window test structure, but this bounded pass did not establish a provider-specific durable effect→authoritative-readback join. It was not scored.

### Independent RED-TEAM / VERIFIER
The verifier received only the frozen implementation/test/history packet above and evaluated the Level-3 proof obligations without the proposed score.

**Verdict: PASS_WITH_LIMITS as a transferable Level-3-style external-effect reconciliation kernel; do not call it universal exactly-once.**

Proof obligations:
1. **Durable business/effect identity exists before provider mutation? — PASS.** Persistent reservation and exact execution intent are created before the refund call.
2. **Stable identity reaches the provider? — PASS_WITH_LIMITS.** Deterministic provider idempotency plus stable workflow metadata are sent. The local system does not need the provider refund ID before acknowledgement because the provider can later be searched by the embedded business reference.
3. **Ambiguous provider outcome is preserved rather than retried blindly? — PASS.** `OutcomeUnknown`/reconcilable `Reserved` states hold capacity; replay tests keep the mutation count at one.
4. **State survives restart? — PASS.** A persistent-store restart regression proves the reservation survives process loss and remains canonically reconcilable.
5. **Can the original external effect be resolved through authoritative read-only provider evidence without a second mutation? — PASS_WITH_LIMITS.** The live adapter performs a refund GET/list query and matches stable workflow metadata + exact money fields; the ambiguity test proves the reconcile path itself does not increment the mutation count.
6. **Is the exact crash window “provider accepted mutation, process killed before local transition, restart, provider readback” exercised in one end-to-end failpoint test? — NO.** The repository separately tests crash-persistent reserved state and ambiguous-provider reconciliation, so the strongest crash-window conclusion is compositional rather than a single kill/restart/provider-acceptance regression.
7. **Is reconciliation collision-proof under every provider edge case? — NOT FULLY ESTABLISHED.** The inspected lookup scans a bounded refund listing and matches workflow metadata/amount/currency; unusual provider-history/cardinality or metadata-collision cases require further testing.
8. **Does this transfer directly to laboratory hardware? — NO.** This is an adjacent-domain reference kernel. Scientific transfer depends on instruments/LIMS/robot queues exposing a stable client-supplied job/business reference and authoritative read/history API.

The verifier therefore accepts the architectural discovery but narrows the claim: **Level 3 does not require a pre-known native provider operation ID if the original mutation carries a durable externally queryable business reference and the provider itself is the authoritative system of record.**

### Proposed score
A) speed to first revenue: **4/5** — the science-facing product can begin as a fixed-scope effect-reconciliation audit/adapter rather than a replacement lab OS.  
B) customer value / ceiling: **5/5** — duplicate physical experiments, duplicate dispenses/moves, orphaned jobs and unrecoverable ambiguous effects can be expensive in automated R&D.  
C) build/domain compression: **5/5** — durable reservation, exact action identity, ambiguous-outcome lifecycle, idempotency, provider-readback reconciliation and adversarial tests encode a difficult reliability pattern.  
D) rarity/advantage: **5/5** — this is the first inspected public implementation in the shadow sequence that substantially closes the full ambiguity→restart→authoritative-readback loop, albeit in payments rather than science.  
E) evidence/completeness: **4/5** — strong implementation/tests/history/spec coherence; no single one-shot crash-after-remote-commit failpoint was independently executed here.  
F) rights/operability: **4/5** — code is `MIT OR Apache-2.0`; provider/service semantics and any scientific-device APIs remain independently governed.  
**Total: 27/30 — STRONG_COMPONENT / TRANSFER_KERNEL inside shadow; no central promotion is made.**

### Commercial / research implication
The science opportunity becomes more concrete: build an **Autonomous-Lab External Effect Reconciliation Gateway** modeled on the proven adjacent-domain pattern. Before dispatch, persist one experiment/business-effect reservation and request digest. Send a stable client job/reference ID and idempotency token into the device/LIMS/robot queue when supported. If acknowledgement is lost, keep the effect `OUTCOME_UNKNOWN` and prohibit a second physical command. After restart, query the instrument/LIMS/job-history read API by that same stable reference and reconcile the original effect to `SUCCEEDED`, `FAILED_NO_EFFECT`, or `NEEDS_HUMAN_RECONCILIATION`.

This also changes the next science search target. Requiring every instrument to expose a client-chosen native command UUID was unnecessarily strict. The more general Level-3 requirement is **provider-queryable effect identity**: either a provider-native operation ID survives, or the original effect is tagged with a stable business reference that the authoritative system of record can query later.

### Search lesson outcome
New LOCAL candidate lesson: **search adjacent external-effect systems for provider-queryable business identity, not only native command IDs.** High-signal invariants are durable pre-dispatch reservation, deterministic idempotency, externally persisted workflow/reference metadata, `OutcomeUnknown`, no-blind-retry state, restart recovery, and a read-only provider/system-of-record query that finds the original effect.

This is one successful transfer task. Keep LOCAL; do not edit global `SEARCH_SKILLS.md`.

### VALUE HANDOFF
1. **Capability delta:** substantially closes the previously missing Level-3 architecture by proving an alternate route: stable externally queryable business-effect metadata can substitute for knowing the native provider operation ID before acknowledgement.
2. **Graph edge:** conceptually connects ROSClaw-style durable uncertainty with authoritative reconciliation. For science, the missing implementation edge is now narrower: instrument/LIMS/robot systems must expose stable client references plus read/history APIs.
3. **Radar signal:** external-effect reliability patterns from payments are technically transferable into autonomous science; reliable agent-to-hardware systems may converge on the same reserve→dispatch→unknown→readback→reconcile lifecycle.
4. **Experiment impact:** the next falsifiable search/prototype should select a scientific executor with client-set job metadata or external job IDs, crash after dispatch, restart, and resolve the original job through read-only device/LIMS history before permitting any resend.
5. **Commercial impact:** strengthens the earlier audit wedge into a productizable adapter/gateway with measurable duplicate-command rate, ambiguous-effect age, reconciliation success rate, and manual-recovery hours.
6. **Negative knowledge:** do not require a pre-known native operation UUID when the provider can authoritatively rediscover the original effect from stable embedded business metadata; conversely, metadata without durable reservation or authoritative readback is still insufficient.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate/comparator inspections: 2 deep + 1 triage;
- source/test/spec/history traversals: ~24;
- external GitHub reads/searches: ~35;
- untrusted-repository code executions: 0.

## 2026-09-20 — Shadow Science Run 10

### Hypothesis
A scientific executor can validate the Run-9 **provider-queryable business identity** transfer if it accepts a caller-stable request/idempotency identity on a physically mutating operation and exposes a passive read-only path that resolves that same identity to the canonical native command and current receipt after an ambiguous response. The stronger Level-3 hypothesis additionally requires durable local custody of that effect identity before dispatch and survival across process/browser restart; a session-only caller record or a mocked provider lookup is not enough.

### Discovery modes
1. **Direct scientific executor search:** instrument servers, LIMS/robot job queues and BioXP/SiLA-style adapters with client-set job/reference IDs plus status/history/readback APIs.
2. **Code/invariant search:** `Idempotency-Key`, request-by-key lookup, command receipts, `retry_forbidden`, outcome ambiguity, passive reconciliation, durable dispatch outboxes, preallocated scheduler IDs and restart-safe materialization.
3. **Comparator search:** MADSci and current Opentrons server/client semantics to separate stable workflow IDs and server-created run IDs from provider-queryable effect identity.
4. **Low-attention/history archaeology:** inspected a zero-star scientific platform and the commits that introduced direct-liquid recovery, canonical command lookup and duplicate-pending-submission protections.

Deep inspection was limited to `MolBioFreak/BioModStack` as the candidate, with `AD-SDL/MADSci` and `Opentrons/opentrons` as comparators. No untrusted repository code was executed.

### Best candidate
**MolBioFreak/BioModStack — BioXP stable-request reconciliation + durable scientific-job outbox primitives**  
Canonical URL: https://github.com/MolBioFreak/BioModStack  
Exact revision: `9b36a0b106cd538d772de39092c1d532ad361083`  
Public license: MIT  
Repository attention at inspection: 0 stars / 0 forks  
Evidence snapshot id: `shadow-science-20260920-biomodstack-bioxp-9b36a0b`

### Frozen evidence manifest
- `platform/api/routers/bioxp/operator_controls.py` blob `7ede9228ccae05c3972027940681677eadca8b98`;
- `platform/api/services/bioxp/operator_models.py` blob `64991ed8e5fe382d89f2975ca39b7c54abd08dfb`;
- `platform/frontend/src/lib/bioxpClient.ts` blob `54bd421ea116a68f47cc651c1685bb86c6569e9e`;
- `platform/api/tests/test_bioxp_direct_liquid_idempotency.py` blob `05feb0feef3f78d8c1ef678580f3dd22d0bc1dc4`;
- `platform/api/tests/test_bioxp_deck_queue_relay.py` blob `80ae675f2ec73614370f735fee1a8418f81efd07`;
- `platform/api/experiment_services.py` blob `d08e408489aa09e083e3d94f0538de3820789822`;
- `platform/api/experiment_models.py` — durable run-group/run-attempt/dispatch-outbox schemas inspected at the pinned revision;
- `platform/api/services/global_experiments/worker.py` — durable outbox dispatch + reconciliation worker inspected at the pinned revision;
- `platform/api/tests/test_project_manager_resource_dispatch.py` — SQLite reopen/concurrent-claim dispatch tests inspected at the pinned revision;
- `LICENSE` blob `b28f99a6a7c79ce02901c1a9895c6b9992401adb`;
- history commit `0e10e7b115c8a424665e297c70f658f937bd95ef` (2026-09-06), `fix(bioxp): retain and validate direct liquid recovery`;
- later BioXP hardening includes `14008967062c948a728514cbaaba5be0a9745223` (`prevent duplicate pending submissions`) and `7eae444dbdf11f45170e5901bc04b89d10025a54` (`canonical OEM workflow jobs and controls`).

### Load-bearing claims
**IMPLEMENTED / TESTED IN THE PUBLIC BMS BOUNDARY**
- Normal BioXP v2 operator actions carry a caller-supplied `idempotency_key`; physical deck submissions disable automatic mutation retry and classify unresolved network/receipt outcomes as `uncertain` rather than silently resending.
- When a deck submission is uncertain, the client polls a **GET-only** BMS route using the original key: `/operator-controls/v2/requests/{idempotency_key}`. The implementation comment explicitly says a 404 is an unsettled lookup, **not permission to replay a POST**.
- That request lookup performs two passive reads against the robot provider: first `GET /operator/idempotency/command/{key}` to resolve the stable client key to the canonical `command_id`, then `GET /operator/v2/actions/receipts/{command_id}` to read the current authoritative receipt. It verifies the returned key/kind/command identity and fences a connection-generation change between the two reads.
- Dedicated tests prove this exact request-by-key→current-receipt relay, reject mismatched key/command/kind, preserve the passive lookup lane while active enqueue is unavailable, and propagate a missing identity 404 without issuing a POST.
- The direct-liquid path carries the same stable `Idempotency-Key`; a lost-response regression asserts exactly one POST and no recovery mutation. Its separate recovery route performs a bodyless GET by the original key and returns typed `unknown/pending/incomplete/resolved/conflict/unavailable` states with `retry_forbidden=True`. The test file explicitly labels this an HTTP-boundary recovery contract rather than proof of real robot-store acceptance.
- BioXP error handling distinguishes post-dispatch uncertainty and emits `do_not_resubmit_reconcile_by_command_id` guidance when a command identity is available.

**IMPORTANT LIMITS / FALSIFIED OVERCLAIMS**
- The physical deck client's own source explicitly says its short HTTP admission custody **does not persist across reload**. The stable key is therefore not yet a crash-durable local effect reservation at this boundary.
- The public tests validate the BMS bridge/contracts with fake/provider-bound responses; they do not prove that the underlying BioXP robot-side idempotency/receipt store survives a robot process/power restart or that a real physical command is never reissued after such a failure.
- No inspected end-to-end test executes the decisive sequence `persist effect → physical BioXP accepts command → acknowledgement lost/process dies → restart → GET same key → resolve original command → zero second POST`.
- The exact pinned merge commit exposed no combined-status/workflow-run evidence through the connector, so source/test presence is verified while green CI at that exact revision is UNKNOWN.
- BioXP hardware/runtime/API rights are independent of BioModStack's MIT code; commercial deployment requires separate authorization and access to the instrument/vendor runtime.

### Same-repository compression signal — the missing durable primitive already exists elsewhere
BioModStack's global experiment subsystem separately implements the persistence half that the physical BioXP path lacks. Its schema has unique idempotent run groups, unique run-attempt scheduler IDs, a durable `ExperimentDispatchOutbox` with payload hash, status, attempts, lease token/owner/expiry, errors and acknowledgement JSON, and control-command fencing. The materializer deterministically preallocates the scheduler job ID, queries the authoritative Job by that ID before creation, rejects identity/body conflicts, reuses an already-existing matching Job after replay, and reconciles lifecycle from authoritative `job.status`. Tests include committed SQLite reopen and concurrent-claim authority. This proves a reusable crash-safe scientific-job pattern in the **same repository**, but it is not yet wired to BioXP's physical `idempotency_key` path.

### Comparator evidence
- `AD-SDL/MADSci@6b1ab6a70ce8b15af7aa8968479c90d9138753d0` has durable workflow/action identity and action-result lookup, but its inspected SiLA observable-command map remains in-process; the durable workflow ID is not yet a cross-restart provider-native command join.
- `Opentrons/opentrons@03b991fb263b97b6bb767ce311ca56e103d635e4` exposes server-created run IDs and run-status APIs, but this bounded pass did not establish a caller-chosen stable business/job reference on run creation that can later rediscover an ambiguously accepted run.

### Independent RED-TEAM / VERIFIER
The verifier received the frozen source/test/schema/history packet without the proposed score.

**Verdict: PASS_WITH_LIMITS as a STRONG near-Level-3 scientific transfer component; FAIL for completed physical Level 3.**

Proof obligations:
1. **Caller-stable effect/request identity reaches the physical provider boundary? — PASS.** BioXP operator requests carry caller-supplied idempotency identity.
2. **Can the same identity be resolved later through passive provider reads to the canonical command/receipt? — PASS in the public BMS contract/tests.** Key→command→receipt lookup is explicit and GET-only.
3. **Does ambiguous response handling forbid blind automatic mutation replay? — PASS.** The deck client disables mutation retries and switches to request lookup; direct-liquid lost-response tests assert no recovery mutation.
4. **Does the caller-side physical effect reservation survive process/browser restart? — FAIL at the inspected BioXP deck boundary.** Source explicitly says custody does not persist across reload.
5. **Is robot-side idempotency/receipt durability across provider restart independently proven? — UNVERIFIED.** The strongest public tests stop at the BMS/provider contract boundary.
6. **Is the exact crash-after-physical-acceptance/no-second-POST scenario tested end to end? — NO.** This remains the decisive missing proof.
7. **Are the missing durability mechanics available as reusable code nearby? — PASS_WITH_LIMITS.** The global scientific-job outbox/materializer proves durable reservation/replay/reconciliation machinery, but integration with BioXP physical commands is not implemented in the inspected path.

The verifier therefore rejects “physical exactly-once” and accepts a narrower but commercially useful conclusion: **BioModStack demonstrates the scientific provider side of the Run-9 architecture—stable externally queryable business identity plus no-blind-retry lookup—and separately contains a durable outbox pattern that could close the caller-side crash gap.**

### Proposed score
A) speed to first revenue: **4/5** — a reliability retrofit/chaos audit can be sold without replacing a laboratory platform.  
B) customer value / ceiling: **5/5** — duplicate deck moves/dispenses/builds, orphaned robot jobs and ambiguous recovery can waste expensive samples and instrument time.  
C) build/domain compression: **5/5** — same-repo physical request/receipt semantics plus durable scientific-job outbox/materializer substantially compress the design space for a reconciliation gateway.  
D) rarity/advantage: **5/5** — a zero-star repository containing both halves of this integrity problem is unusually high-signal.  
E) evidence/completeness: **3/5** — strong implementation/tests/schema/history, but no real robot-store restart proof or one-shot physical crash-window test.  
F) rights/operability: **3/5** — MIT code is clear; proprietary BioXP hardware/runtime/API and deployment access remain independently governed.  
**Total: 25/30 — STRONG_COMPONENT / NEAR_LEVEL3_TRANSFER inside shadow; no central promotion is made.**

### Commercial / research implication
The concrete product is an **Autonomous-Lab Physical Effect Reconciliation Retrofit**. Persist a local `EffectReservation`/outbox row before each dangerous physical POST; bind it to the exact external idempotency key and request digest; transition lost acknowledgements to `OUTCOME_UNKNOWN`; forbid a second physical submission; and after restart resolve `idempotency key → native command → canonical receipt/device truth` until the original effect becomes `SUCCEEDED`, `FAILED_NO_EFFECT`, or `NEEDS_HUMAN_RECONCILIATION`. BioModStack matters because its BioXP layer already supplies the provider-queryable key/receipt side while its experiment subsystem already supplies a reusable durable-outbox side.

### Search lesson outcome
The Run-9 LOCAL lesson **provider-queryable business identity** succeeds on a **second distinct task**: first in payments (`auths-proof`), now as a strong scientific near-match (`BioModStack`). The refined high-signal query is `Idempotency-Key` + read-only request/command lookup + explicit “404 is not permission to replay”/no-retry semantics + durable-outbox terms. Always verify whether caller custody of the key is itself crash-persistent before calling the system Level 3.

Evidence count: **2 distinct tasks**. This is now STAGED-eligible inside shadow evaluation only; do not modify global `SEARCH_SKILLS.md` from this lane.

### VALUE HANDOFF
1. **Capability delta:** establishes a real scientific provider-queryable effect-identity bridge—stable client key→native command→canonical receipt—plus same-repository durable dispatch/outbox primitives.
2. **Graph edge:** conceptually narrows the missing Level-3 edge to wiring durable local `EffectReservation` state to the already-queryable BioXP external identity; no central graph file was edited.
3. **Radar signal:** scientific middleware is beginning to adopt the same idempotency/readback separation seen in payment APIs, suggesting cross-domain convergence on external-effect reconciliation.
4. **Experiment impact:** the next falsifiable test is exact and small: persist a physical effect reservation, dispatch once, kill after provider acceptance/before acknowledgement, restart, GET by the same key, and prove no second POST occurs.
5. **Commercial impact:** upgrades the generic audit concept into a concrete retrofit architecture with measurable duplicate-effect exposure, unresolved-effect age, reconciliation success rate and recovery labor.
6. **Negative knowledge:** provider-queryable command identity without durable caller-side reservation is a near-match, not Level 3; mock/provider-contract tests are not evidence that a real robot-side receipt store survives power/process loss.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate/comparator inspections: 3;
- source/test/schema/history traversals: ~25;
- external GitHub reads/searches: ~40;
- untrusted-repository code executions: 0.

## 2026-09-20 — Shadow Science Run 11

### Hypothesis
A low-attention embodied/robot execution runtime may already implement the caller-side half of Level-3 effect integrity more rigorously than public lab middleware: durably reserve command/effect identity before side effects, preserve an unresolved effect across process death, and forbid replay even after attended recovery. The hypothesis does not claim Level 3 unless the same effect can later be resolved from authoritative device/system-of-record evidence without a second physical command.

### Discovery modes
1. **Direct scientific/protocol search:** instrument servers, SiLA observable commands, robot/LIMS job identity and recovery semantics.
2. **Code/invariant search:** `idempotency_key`, `command_id`, journal-before-execute, `EXECUTION_OUTCOME_UNKNOWN`, process-loss tests, fsync/atomic persistence, and restart replay blocking.
3. **Adjacent external-effect search:** warehouse-control/device tasks and browser-to-printer job identity/status to test whether other physical domains provide provider-queryable completion evidence.
4. **Low-attention/history archaeology:** recent low-star robot runtimes, feature-introducing commit history, and explicit physical-acceptance/maturity documentation.

Serious inspection centered on `SUSTechWLA/tangying-robot-agent-os`, with `bitdreamit/laravel-qz-tray` as a negative comparator and `brettljausn-ai/openwcs` as a bounded triage comparator. No untrusted repository code was executed.

### Best candidate
**SUSTechWLA/tangying-robot-agent-os — durable unknown-effect tombstone / crash barrier**  
Canonical URL: https://github.com/SUSTechWLA/tangying-robot-agent-os  
Exact revision: `774bd2a2f4035dbe48f9016a88af1cb6fb4096ae`  
Public license: MIT  
Repository attention at inspection: 3 stars / 0 forks  
Evidence snapshot id: `shadow-science-20260920-tangying-unknown-tombstone-774bd2a`

### Frozen evidence manifest
- `robot/gateway/tangying_robot_gateway/journal.py` blob `bb3d51b2fcc5cfda59682611d1ee8a106652f238`;
- `robot/gateway/tangying_robot_gateway/service.py` blob `9e7e6ce923779862d7a10f159065bbcb2b3c91f9`;
- `robot/gateway/tests/test_service.py` blob `c0c7623eff7987b60ea995b58256e0910a810404`;
- `robot/gateway/tests/test_plugin_execution_outcome.py` blob `cb4acfdccb2255e51436a9f4b87fefe6c3069905`;
- `robot/gateway/tangying_robot_gateway/local_recovery.py` blob `c7686382f65d2df3d1b7aee6eed77f04fcdc4ed7`;
- `proto/robot/v1/robot.proto` blob `1881e37a46686fe664cdc2c8f48ffd9e34743d9b`;
- `LICENSE` blob `63070cfb97303994fb3ae1e43338f0523815f104`;
- history includes the earlier durable-runtime-safety-state feature family and the pinned head `774bd2a2f4035dbe48f9016a88af1cb6fb4096ae`; current history also records operational maturity/performance caveats rather than presenting the project as a finished production runtime;
- `docs/operations/safety-checklist.md` explicitly states that the repository has no completed physical acceptance result and that software readiness is not permission to move hardware.

### Specialist passes
- **CODE INSPECTOR:** traced `SkillCommand.command_id` / `idempotency_key` into journal reservation, replay/unknown lookup, backend execution and recovery semantics; verified the journal write precedes backend side effects.
- **SYSTEMS / SCIENCE VALIDATOR:** separated software crash-window simulation from physical-hardware evidence and checked the repository's own acceptance caveat.
- **ECOSYSTEM ANALYST:** compared the durable tombstone pattern with SiLA command correlation, BioModStack provider-queryable receipts, browser-print job identity and WCS task/callback patterns.
- **COMMERCIAL ANALYST:** evaluated the primitive as a crash-safety/recovery kernel for automated labs rather than another robotics framework.
- **RED-TEAM / VERIFIER:** challenged authoritative readback, native provider identity, hardware acceptance and whether attended recovery accidentally re-enables the old command before assigning a score.

### Load-bearing claims
**IMPLEMENTED / TESTED IN SOURCE CORPUS**
- `SkillCommand` carries stable `command_id`, `task_id` and `idempotency_key` plus deadline/lease, approval, robot/resource identity, world/task/aggregate revisions, fencing token and step ID. The capability schema separately marks world-mutating operations as requiring fresh post-command observation rather than treating a successful return as completion evidence.
- `RuntimeJournal.begin()` durably reserves execution **before a backend may produce side effects**. Persistence uses a temporary file, flush + `fsync`, atomic replace and parent-directory `fsync`; if the journal write fails, regression tests prove backend execution never begins and the safety latch is raised.
- A dedicated crash-window regression enters `backend.execute()`, records that execution was attempted, then raises a `BaseException` to simulate process loss before a terminal journal transition. Reopening the same journal and resubmitting the original command executes the fresh backend **zero times**, returns `EXECUTION_OUTCOME_UNKNOWN`, and leaves the E-stop latched.
- A separate physical-adapter regression models `driver lost response after sending motion`. The runtime returns `EXECUTION_OUTCOME_UNKNOWN`, persists the stop, restarts, then rejects a **fresh command ID and fresh idempotency key** while the unresolved physical effect remains; the movement count stays exactly one.
- The runtime deliberately distinguishes a known no-effect/known-failure result from ambiguity. A `TARGET_UNREACHABLE` result does not become `OUTCOME_UNKNOWN`, does not latch the same uncertainty state, and a later retry can succeed.
- Attended recovery is local-only and auditable: the operator must be present and interactive and supply identity/reason; recovery writes an fsynced copy of the original journal before reconciling pending state. The old uncertain keys are retained as reconciled/unknown tombstones rather than deleted and made replayable.

**IMPORTANT LIMITS / FALSIFIED OVERCLAIMS**
- The recovery path does **not** authoritatively query a device or external system of record to determine whether the interrupted physical command actually happened. Operator attestation restores liveness but does not establish physical truth for the old effect.
- No inspected durable schema binds every local command/business-effect identity to a vendor-native operation ID that can be re-queried after restart.
- The repository's own physical safety checklist says there is **no completed physical acceptance result**. The strongest crash evidence here is unit/plugin/fake-transport style testing, not an independently reproduced hardware-in-loop process kill.
- Current history contains explicit operational/maturity caveats, including large-ledger performance issues; source/test depth should not be silently upgraded into production field maturity.

### Independent RED-TEAM / VERIFIER
The verifier received only the frozen source/test/schema/history packet above and evaluated the effect-integrity obligations before seeing the proposed score.

**Verdict: PASS_WITH_LIMITS as a durable unknown-effect tombstone / crash-barrier kernel; FAIL for full Level-3 physical exactly-once or authoritative reconciliation.**

Proof obligations:
1. **Durable command/effect identity before side effects? — PASS.** Journal reservation is persisted before backend execution; persistence failure blocks the backend.
2. **Crash after physical execution may have begun preserves uncertainty across restart? — PASS in adversarial software tests.** The process-loss regression reopens the journal and refuses to execute the same command again.
3. **Does unresolved physical uncertainty block even a new logical command? — PASS.** The plugin lost-response test restarts and attempts a new command/key; the movement count remains one while the E-stop/unknown state is unresolved.
4. **Known failure versus unknown effect distinguished? — PASS.** The known `TARGET_UNREACHABLE` path remains retryable instead of being over-quarantined.
5. **Can attended recovery erase the old uncertainty and make it replayable? — PASS_WITH_LIMITS.** Recovery preserves an audit copy and reconciled unknown tombstones; it can restore liveness, but that is not proof of the original effect's physical outcome.
6. **Authoritative read-only device/system-of-record reconciliation of the original effect? — FAIL.** No qualifying post-restart provider/device lookup closes the tombstone to success or proven no-effect.
7. **Durable local effect → native provider operation join? — NOT ESTABLISHED.** The command identity is strong locally, but no universal external operation ID binding was found.
8. **Physical hardware validation? — NO.** The project's own checklist explicitly says completed physical acceptance is absent.

Strongest objection: this kernel can permanently remember **“the effect may have happened; never blindly repeat it”**, but it still cannot prove what actually happened. A human reset is a liveness decision, not authoritative physical reconciliation.

### Proposed score
A) speed to first revenue: **4/5** — a crash/retry integrity audit can be delivered as a bounded integration service.  
B) customer value / ceiling: **4/5** — avoiding duplicate robot/lab effects and unsafe recovery has direct value, though the economic ceiling needs lab-specific validation.  
C) build/domain compression: **5/5** — durable pre-effect reservation, atomic persistence, replay/unknown classification, restart tests, safety fencing and attended-recovery audit compress difficult reliability engineering.  
D) rarity/advantage: **4/5** — the exact tombstone behavior is uncommon, but adjacent ROSClaw patterns already show durable unknown-state gating.  
E) evidence/completeness: **4/5** — strong source/tests/schema/history; no real hardware acceptance and no authoritative reconciliation.  
F) rights/operability: **4/5** — MIT code and clear protocol boundaries help, but maturity/performance caveats and hardware-specific validation remain.
**Total: 25/30 — STRONG_COMPONENT inside shadow; no central promotion is made.**

### Comparator / negative evidence
- `bitdreamit/laravel-qz-tray` exposes a unique `client_job_id` and job statuses, but its completion lifecycle is fundamentally browser/client reported around QZ printing rather than authoritative printer/spooler readback. It is therefore a false positive for provider-queryable physical completion.
- `brettljausn-ai/openwcs` exposes persistent/idempotent device-task concepts and callback/status machinery, but this bounded pass did not establish the full crash-persistent same-identity → authoritative device-status reconciliation chain, so it remains unscored triage evidence.
- SiLA observable-command UUID/result polling remains a valuable correlation primitive, but correlation lifetime alone is not a durable business-effect ledger across server loss.

### Commercial / research implication
The reusable component is an **Unknown-Effect Tombstone / External Effect Crash Barrier** inside the broader Autonomous-Lab External Effect Reconciliation Gateway. Persist the effect identity and request fingerprint before physical dispatch; after ambiguous execution, keep that identity permanently non-replayable; allow an attended recovery to release the global stop only without deleting the old tombstone; and, where the instrument exposes authoritative history, bind the tombstone to a BioModStack-style `stable key → native command → canonical receipt` lookup so the original effect can eventually be resolved without a second physical command.

A realistic first paid wedge is a fault-injection **Physical Effect Crash/Recovery Audit** for automated labs and robotic workcells: kill the controller exactly after device write, restart it, prove that neither the old command nor a fresh surrogate command can blindly duplicate the effect, and classify which operations can be automatically reconciled versus which require human state inspection.

### Search lesson outcome
New LOCAL candidate lesson: **unresolved-effect tombstones are a first-class safety primitive**. After ambiguous dispatch, attended/manual recovery may restore system liveness without making the original idempotency/effect identity replayable. Future reviews should explicitly ask whether a reset/recovery deletes old uncertainty or preserves it as a non-replayable tombstone.

One direct success only. Keep LOCAL; do not modify global `SEARCH_SKILLS.md`.

### VALUE HANDOFF
1. **Capability delta:** adds a tested caller-side crash barrier that survives process death and permanently blocks replay of an ambiguous physical effect identity, even through attended recovery.
2. **Graph edge:** complements BioModStack's provider-queryable `key → command → receipt` side. The missing high-value edge is now the binding of this durable tombstone to authoritative provider readback.
3. **Radar signal:** physical-effect integrity patterns are converging across lab middleware, robotics runtimes and payments: durable intent, explicit unknown state, replay blocking, then provider/system-of-record reconciliation.
4. **Experiment impact:** the next falsifiable prototype can be very small: bind a durable tombstone to a provider-queryable scientific command key, crash after provider acceptance, restart, perform GET-only reconciliation, and assert **zero second mutation**.
5. **Commercial impact:** supports a fixed-scope crash/recovery qualification service and a reusable gateway component with measurable duplicate-effect exposure, unresolved-effect age, recovery MTTR and reconciliation success rate.
6. **Negative knowledge:** manual recovery is not authoritative physical truth; self-reported print/job completion and idempotent callbacks do not qualify unless the status comes from the actual external system of record and survives restart.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate/comparator inspections: 2 deep/moderate + 1 triage;
- source/test/schema/history traversals: ~22;
- external GitHub/web reads/searches: ~40;
- untrusted-repository code executions: 0.

## 2026-09-20 — Shadow Science Run 12

### Hypothesis
A low-attention scientific orchestration runtime may already implement the missing Level-3 control lifecycle: durably reserve execution intent before dispatch, preserve ambiguous provider outcomes, reconcile by a stable idempotency/business key before any repeat submission, and fail closed when authoritative lookup is unavailable. The hypothesis fails as a completed scientific Level-3 implementation if the only concrete provider is an in-memory dry run or real execution is explicitly not installed.

### Discovery modes
1. **Direct scientific execution search:** laboratory execution adapters, provider job lookup, restart-safe experiment dispatch and reconciliation semantics.
2. **Code/schema invariant search:** `submit_intent_key`, `find_by_idempotency_key`, `AMBIGUOUS`, `RECONCILING`, durable intent rows, provider execution IDs, unique submit keys and reconcile-before-resubmit paths.
3. **Crash/retry test search:** concurrent ambiguous callers, process/reopen recovery, idempotent submit contracts, no-duplicate side-effect assertions and durable intent-before-write patterns.
4. **Provider-binding/history falsification:** inspected the concrete runtime adapter factory, supported execution modes and feature history to distinguish a complete architecture from a real laboratory integration.

### Result
**NO_FIND for completed physical Level 3.** The best near-match is a strong architecture/watch component whose real laboratory provider is deliberately absent.

### Best near-match
**trieu04/lab-in-the-loop — durable execution-intent + reconcile-before-resubmit architecture**  
Canonical URL: https://github.com/trieu04/lab-in-the-loop  
Exact revision: `80eb9524a4a36178b35810a7999cd95e8394d4fc`  
Public license: **none detected in GitHub repository metadata (`license: null`)**  
Repository attention at inspection: 0 stars / 0 forks  
Evidence snapshot id: `shadow-science-20260920-lab-in-loop-80eb952`

### Frozen evidence manifest
- `apps/lab-agent/lab_agent/execution_lifecycle.py` blob `9f76a9084eba65cf36e1f15a5a2ca6a9ffd92550`;
- `apps/lab-agent/lab_agent/integrations/lab_execution.py` blob `001dd9e16c0db86597974d13d649a4f72083d579`;
- `apps/lab-agent/tests/test_execution_reconciliation.py` blob `2d1469c31891c8e7e9643c95bd20247d7e83246e`;
- `apps/lab-agent/tests/contracts/test_lab_execution_contract.py` blob `518e30410868fb2d94d85b082414ce7e4bc57baa`;
- `apps/lab-agent/lab_agent/migrations/010_execution_analysis_knowledge.sql` blob `efb1acfd1fbf1c621a6fcb97ae755ee3ba8e2d72`;
- `apps/lab-agent/lab_agent/runtime.py` blob `28dd38478be2fc7381be80afcc9de6e0e908aaf8`;
- `apps/lab-agent/tests/test_durable_recovery_integration.py` blob `e52953c717b0bd37b946379db43316907d389dcb`;
- history for `execution_lifecycle.py` includes `39603d...` and `099e21...`, showing the lifecycle was implemented/hardened in the repository's short July 2026 history.

### Specialist passes
- **CODE INSPECTOR:** traced `run_execution()` from durable run/intent creation through submit, ambiguity, reconciliation and terminal result handling.
- **SCHEMA / SYSTEMS VALIDATOR:** verified unique submit-intent keys, provider execution IDs and explicit `submitted/running/reconciling/ambiguous/.../blocked` durable status states.
- **TEST VALIDATOR:** inspected concurrent reconciliation and adapter-contract tests plus a separate restart-safe durable-write corpus.
- **ECOSYSTEM / COMMERCIAL ANALYST:** compared the lifecycle to the previously verified BioModStack key→command→receipt boundary and the Tangying unknown-effect tombstone.
- **RED-TEAM / VERIFIER:** challenged the concrete runtime binding, real-provider availability, physical evidence, rights and one-shot crash-window proof before scoring.

### Load-bearing claims
**IMPLEMENTED / TESTED**
- `run_execution()` calls `prepare_execution_run()` and `prepare_intent()` before provider submission. The durable intent is keyed by `submit_intent_key`; active/submitted/executed state routes to reconciliation instead of blind replay.
- Provider uncertainty is represented explicitly. A non-typed exception after submission marks the intent ambiguous and the run `AMBIGUOUS` instead of assuming no effect.
- `reconcile_execution()` requires reconciliation support and performs `find_by_idempotency_key(tenant_id, submit_intent_key)` **before** any possible repeat submission. A found remote run must match tenant/canvas/run/key/input hash/mode/evidence identity before its provider ID is accepted. Lookup failure or unsupported reconciliation transitions the run to `BLOCKED`, not to another submit.
- The migration gives execution runs a unique `submit_intent_key`, optional `provider_execution_id`, a unique adapter/provider-execution identity and durable states including `RECONCILING`, `AMBIGUOUS` and `BLOCKED`.
- Concurrent reconciliation tests create two callers around an absent remote lookup and assert only **one** provider submit occurs; the durable run finishes succeeded and the intent is reconciled. Adapter contract tests separately prove same-key/same-input replay returns the same provider run while same-key/different-input fails.
- The repository has a separate durable-write recovery corpus that exercises the intent-before-write pattern across reopen/restart and proves an already-landed external object is discovered/reused rather than duplicated. This supports the authors' durability discipline, though it is not the laboratory provider path itself.

**DECISIVE LIMITS / FALSIFIED OVERCLAIMS**
- The concrete `DeterministicLabExecutionAdapter` is explicitly **memory-only dry run**. Its `find_by_idempotency_key()` therefore proves the orchestration contract only against process-local mock provider state.
- `DisabledRealLabExecutionAdapter` explicitly says **“No real laboratory implementation exists in the Phase 8 dry-run scope.”** Its reconciliation support is false and every operation fails closed.
- The process-wide runtime builder rejects every Phase 8 mode except `dry_run` and hard-wires `DeterministicLabExecutionAdapter()`. A real or sandbox laboratory adapter is therefore not merely unverified; it is intentionally not constructible in this revision.
- No inspected test proves `real provider accepts physical command → acknowledgement lost/process dies → restart → authoritative provider GET/find by same key → zero second physical mutation`.
- No public license is declared in GitHub repository metadata, and there is no established physical provider/runtime deployment surface in this revision.

### Independent RED-TEAM / VERIFIER
The verifier evaluated the frozen source/test/schema/runtime packet without the proposed score.

**Verdict: FAIL for completed scientific Level 3; PASS_WITH_LIMITS as a WATCH-level transfer architecture.**

Proof obligations:
1. **Durable pre-dispatch business/effect intent? — PASS at the orchestration store.** The run and submit intent are prepared before provider submission.
2. **Explicit ambiguity plus replay block/reconciliation path? — PASS.** Ambiguity is durable and active/ambiguous runs enter `find_by_idempotency_key()` before any possible resubmit; unsupported reconciliation blocks.
3. **Concurrent/retry duplicate suppression? — PASS in the dry-run test corpus.** Two reconciliation callers produce one submit; same-key replay returns the same provider run.
4. **Authoritative scientific provider lookup? — FAIL.** The only installed implementation is an in-memory deterministic dry run.
5. **Real scientific/physical execution adapter? — FAIL EXPLICITLY.** Real mode is rejected at runtime and the sentinel says implementation is not installed.
6. **Exact crash-after-provider-acceptance/no-second-mutation test? — FAIL.** No real provider exists at this revision, so the decisive Level-3 physical boundary cannot be exercised.
7. **Rights/operability clarity? — WEAK.** GitHub repository metadata reports no public license and production execution is intentionally disabled.

Strongest objection: this repository encodes almost the ideal Level-3 **orchestration contract**, but the thing that would make it scientifically valuable—the authoritative external laboratory system of record—is a protocol interface backed only by an in-memory mock. Calling it a Level-3 scientific executor would confuse architecture quality with provider implementation.

### Proposed score
A) speed to first revenue: **3/5** — useful as a blueprint/retrofit pattern, but a real provider must be built first.  
B) customer value / ceiling: **4/5** — the lifecycle addresses expensive duplicate/ambiguous scientific execution once connected to real automation.  
C) build/domain compression: **5/5** — durable intent, explicit ambiguity, reconcile-before-retry, schema and adversarial tests save meaningful reliability design work.  
D) rarity/advantage: **5/5** — unusually complete external-effect semantics for a zero-star scientific repo.  
E) evidence/completeness: **4/5** — strong source/schema/tests/history for orchestration, but no real lab provider.  
F) rights/operability: **1/5** — no detected public license and real/sandbox execution intentionally unavailable.  
**Total: 22/30 — WATCH_COMPONENT / TRANSFER_ARCHITECTURE. Do not promote to STRONG.**

### Commercial / research implication
This is a high-value blueprint for the **Autonomous-Lab External Effect Reconciliation Gateway** lifecycle:

`persist intent → submit once → outcome ambiguous → authoritative find-by-stable-key → reconcile or BLOCK → only resubmit after authoritative absence`

The shortest path to a stronger scientific implementation is to bind this lifecycle to BioModStack's already-inspected BioXP `stable key → native command → canonical receipt` read path, while retaining a Tangying-style permanent unknown-effect tombstone after ambiguous dispatch. That combination would close substantially more of Level 3 than any of the three components alone.

### Search lesson outcome
New LOCAL lesson: **provider-binding / dry-run collapse check**. When a reconciliation architecture appears to perfectly match an external-effect invariant, immediately inspect the concrete runtime adapter factory, enabled execution modes and provider backing store. An abstract `find_by_idempotency_key()` plus durable schema/tests is not provider evidence when the only installed implementation is memory-only dry-run and real mode fails closed.

Evidence count: **1 task**. Keep LOCAL; do not stage or promote to global `SEARCH_SKILLS.md`.

### VALUE HANDOFF
1. **Capability delta:** adds a clean, tested orchestration reference for durable intent → ambiguity → authoritative lookup-before-resubmit, but no new real physical capability.
2. **Graph edge:** identifies an almost plug-shaped architecture for connecting Tangying-style durable tombstones to BioModStack-style provider-queryable receipts; the remaining edge is a concrete real adapter.
3. **Radar signal:** scientific orchestration projects are independently converging on payment-grade reconciliation semantics even before real provider integrations are complete.
4. **Experiment impact:** the exact next test is now implementation-shaped: wrap a real scientific provider behind `find_by_idempotency_key`, persist the key before dispatch, inject lost acknowledgement/process death, restart and assert provider mutation count stays one.
5. **Commercial impact:** reinforces the fixed-scope crash/recovery audit and suggests a reusable adapter contract for a productized reconciliation gateway.
6. **Negative knowledge:** architecture-complete + mock-provider is a major false-positive class; inspect runtime wiring before calling a repository externally effect-safe.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate/comparator inspections: 1 deep candidate + prior verified comparators;
- source/test/schema/history traversals: ~18;
- external GitHub reads/searches: ~25;
- untrusted-repository code executions: 0.

## 2026-09-20 — Shadow Science Run 13

### Hypothesis
A mature scientific repository can hide a newly-added **operational reproducibility kernel** that is more reusable than its headline algorithm: idempotent run admission, crash/restart recovery, retry lineage, immutable lifecycle transitions and typed measured-hardware evidence. The hypothesis fails as a strong finding if those properties are only UI bookkeeping or README claims. It does **not** satisfy physical-effect integrity Level 3 unless the runtime also preserves a provider/native-device execution identity and can authoritatively reconcile an ambiguous physical effect after restart.

### Discovery modes
1. **Direct/current scientific-runtime search:** searched mature RF/DPD research software for experiment services, worker supervision and reproducible measured-hardware workflows rather than another model architecture.
2. **Code/schema invariant search:** followed `idempotency_key`, terminal-state transitions, worker identity, heartbeat/event cursors, `parent_run_id`, config hashes, measurement capture hashes and evidence attestations.
3. **Commit-history archaeology:** inspected September 2026 Studio/runtime hardening commits to identify operational capabilities added after the core scientific project became established.
4. **Paper↔code validation:** checked OpenDPDv2 / MP-DPD research evidence to confirm that the repository is grounded in measured RF hardware rather than a synthetic-only ML demo.

### Best candidate
**lab-emi/OpenDPD — crash-aware experiment runtime + typed RF measurement-evidence kernel**  
Canonical URL: https://github.com/lab-emi/OpenDPD  
Exact revision: `aba888b87199d7ae7802ce931987e3aa3c951410`  
Revision date: 2026-09-18  
Public license: Apache-2.0  
Repository attention at inspection: 177 stars / 43 forks  
Evidence snapshot id: `shadow-science-20260920-opendpd-runtime-aba888b`

### Frozen evidence manifest
- `opendpd/runtime/db.py` blob `d67c6e3b0a13c9a11996d1b960e732c5c6b403f8`;
- `opendpd/runtime/supervisor.py` blob `b32410aa4c5afb62fa40b9d966147b2e6c2d074f`;
- `tests/integration/test_runtime.py` blob `51c2f15b133e2b9ce079f7f32594b42e3b37d701`;
- `opendpd/schemas/run.py` blob `fa1ee528e4f9757149e0fd7e80de223dd8b5e75e`;
- `opendpd/schemas/measurement.py` blob `e313ac4ce6566efffe00a42babac07a7edaba68c`;
- `.github/workflows/ci.yml` blob `c1b9a74dee707b5c541c1f8cd8226c5313c61eac`;
- `pyproject.toml` blob `4a168b5457a794d96398e09d01f03a9c332d576a`;
- `LICENSE` blob `df09eb934f8608ff252fe300ce9eacd418a03ec1`;
- runtime history includes September 2026 service/worker hardening commits `8b3a36...`, `2dd755...` and `2ad281...`;
- pinned release commit `aba888...` is signed/verified and visible check-runs at inspection include a successful Python 3.10 test job plus successful build/publish checks;
- external science evidence: Wu, Li & Gao, *OpenDPDv2: A Unified Learning and Optimization Framework for Neural Network Digital Predistortion* (arXiv:2507.06849; reported accepted to IEEE GLOBECOM 2026), plus earlier MP-DPD work using measured wideband PA data.

### Specialist passes
- **CODE INSPECTOR:** traced run admission through SQLite store, supervisor process spawning, event ingestion, cancellation, worker death, restart recovery and explicit retry lineage.
- **SCHEMA / PROVENANCE VALIDATOR:** verified immutable terminal states, stable run/idempotency/config hashes, append-only event sequencing and typed physical-measurement evidence binding the played artifact to capture hashes and declared conditions.
- **SCIENCE VALIDATOR:** checked that OpenDPD's scientific lineage includes measured wideband GaN PA experiments rather than only simulation.
- **ECOSYSTEM / COMMERCIAL ANALYST:** compared the runtime to generic experiment/workflow tools and isolated the value in the RF-specific execution/evidence contract rather than generic job queuing.
- **RED-TEAM / VERIFIER:** challenged storage durability, physical side-effect semantics, manual-attestation boundaries, generic-substitute risk and recentness of the operational layer before scoring.

### Load-bearing claims
**IMPLEMENTED / TESTED**
- `RunStore` is the authoritative local runtime record. Its SQLite schema makes `run_id` primary and `idempotency_key` unique, and stores append-only per-run events with a compound `(run_id, seq)` key. Explicit transactions validate lifecycle transitions and advance the run/event cursor together.
- Run schemas encode `queued/running/succeeded/failed/cancel_requested/cancelled/interrupted`; terminal states cannot transition again. `WorkerInfo` stores PID plus creation time because PID reuse is not trusted. Retry creates a new child run through `parent_run_id` rather than rewriting the old scientific record.
- `RunSupervisor.submit()` returns the existing run for a repeated idempotency key. Integration tests prove same-key admission returns the same run ID and a real worker process completes with strict monotonic event sequence/cursor-resume semantics.
- Adversarial integration tests kill a worker process, test idempotent/cooperative cancellation, reject late cancelled→succeeded resurrection, and restart the service with dead-running/queued/orphan-worker records. Recovery interrupts those stale records, kills a surviving orphan worker, and leaves no running rows rather than silently pretending old work completed.
- The measurement schema carries an explicit attestation, source run (`apply_run_id`), SHA-256 of the played artifact, capture-file hashes, PA/capture-chain/sample-rate/drive/calibration/timestamp conditions, alignment/correlation/gain diagnostics and processing version. The module explicitly states that OpenDPD itself does **not** make the measurement; user-provided evidence remains labeled as such, while mock-adapter output has a separate synthetic attestation.
- CI configuration runs the main test corpus across Python 3.10–3.13 and contains API/build/package checks. At the pinned release, visible check-run evidence includes a successful Python 3.10 test job and successful build/publish jobs.
- Public code is Apache-2.0.

**SCIENCE VALIDATION**
- OpenDPDv2 reports measured evaluation on a 3.5 GHz GaN Doherty PA with a 200 MHz 256-QAM OFDM test signal, including strong ACPR/EVM results and a quantized/sparse deployment result with an estimated 4.5× forward-pass energy reduction. This validates that the evidence/runtime layer sits inside a real RF research program; it does not independently validate the newer runtime's field reliability.

**IMPORTANT LIMITS / FALSIFIED OVERCLAIMS**
- The store is local SQLite with WAL and `PRAGMA synchronous=NORMAL`, not a replicated or fully synchronous transaction service. Do not overstate it as a universal durable-outbox implementation.
- Restart safety is **run-level**, not physical-effect Level 3. In-flight/queued work becomes `interrupted`, and explicit retry creates a new child run. If an external instrument had already produced an irreversible physical effect before process loss, OpenDPD does not inspectedly preserve a native instrument operation ID or query authoritative device history to prove what happened.
- The measurement-evidence layer is honest but largely operator/import oriented. Its own source states that OpenDPD does not perform the physical measurement; therefore capture provenance is not equivalent to instrument-command readback or exactly-once actuation.
- Generic platforms such as MLflow/Prefect/Airflow/ClearML can cover substantial generic tracking/orchestration functionality. The differentiated value is the integrated RF run lifecycle + hashes + measured-evidence semantics, not “has a job queue.”
- The service/runtime hardening is recent (September 2026) relative to the older DPD research core, so field maturity should not be inferred from the project's scientific history.
- This shadow run inspected source/tests/history/CI evidence but did not independently execute the full test suite.

### Independent RED-TEAM / VERIFIER
The verifier evaluated the frozen source/test/schema/history packet without the proposed score.

**Verdict: PASS_WITH_LIMITS as a reproducible scientific-runtime / measurement-provenance STRONG_COMPONENT; FAIL for H3 external-effect integrity Level 3.**

Proof obligations:
1. **Stable local run identity + idempotent admission? — PASS.** Unique idempotency keys and tests return the same run rather than duplicating admission.
2. **Crash/restart/orphan/cancel behavior tested? — PASS.** Real subprocess, kill, restart and stale-worker cases are exercised; terminal-state resurrection is prohibited.
3. **Typed measured-hardware provenance? — PASS_WITH_LIMITS.** Played/capture hashes and experimental conditions are first-class, but measurement truth is explicitly user-attested rather than independently device-verified.
4. **Current CI/test support? — PASS_WITH_LIMITS.** CI configuration is broad and visible pinned-commit checks include successful tests/build/publish, but this run did not rerun the whole corpus.
5. **Durable native instrument/provider execution identity across a crash? — FAIL.** No qualifying device-command/effect join was established.
6. **Authoritative post-crash readback that resolves the original physical effect without a second mutation? — FAIL.** The runtime interrupts computational work; it does not inspectedly close external instrument ambiguity.
7. **Rarity beyond generic orchestration? — MODERATE.** Generic run supervision is substitutable; RF-specific evidence lineage, retry ancestry and measured-capture contracts provide the useful domain compression.

Strongest objection: if positioned as a generic experiment runner, this is commodity infrastructure. The strong finding is the integration of crash-aware scientific run lifecycle with domain-specific measured-hardware evidence and explicit epistemic labeling; it should not be marketed as physical command safety or exactly-once execution.

### Proposed score
A) speed to first revenue: **3/5** — best as a focused retrofit/audit into an existing RF R&D workflow.  
B) customer value / ceiling: **4/5** — rerun/reconstruction costs and invalid benchmark comparisons can be material, but buyer/ROI needs validation.  
C) build/domain compression: **4/5** — worker supervision, retry lineage, idempotency, event cursoring and RF evidence schemas save meaningful engineering/domain work.  
D) rarity/advantage: **3/5** — mature generic alternatives exist; RF-specific evidence integration is the differentiator.  
E) evidence/completeness: **5/5** — unusually strong source/schema/integration-test/history/CI/paper packet for the narrower claim.  
F) rights/operability: **5/5** — Apache-2.0, packaged Python application, active current release.  
**Total: 24/30 — STRONG_COMPONENT inside shadow; no central promotion is made.**

### Commercial / research implication
First paid wedge: **RF Experiment Reproducibility & Campaign Reliability Retrofit/Audit** for PA/DPD research teams, telecom hardware labs and measured-hardware scientific-ML groups. Add stable/idempotent run admission, retry ancestry, crash/restart qualification, capture/config hashes, experimental-condition attestations and exportable evidence packets around existing model sweeps. The money path is reduced rerun/debug/reconstruction labor and fewer irreproducible or invalid comparisons; exact ROI remains a commercial-lane question.

This component belongs **upstream of** the physical-effect Level-3 gateway. It can prove which computational/scientific run and which capture/evidence artifact were involved, but a separate executor layer is still required to prove whether an ambiguous instrument mutation physically occurred.

### Search lesson outcome
New LOCAL lesson: **commit-history archaeology in mature scientific software can expose newly-added operational reproducibility kernels that algorithm/paper-centric search misses.** OpenDPD is known for DPD modeling, yet its recent Studio/service history contains reusable idempotent admission, process-recovery, retry-lineage and typed evidence machinery.

Failure mode: the new operational layer may be generic backend plumbing and may stop before the physical/provider boundary. Always inspect external-effect identity/readback before upgrading a run-level recovery system into a physical-effect integrity claim.

Evidence count: **1 shadow task**. Keep LOCAL; do not stage or promote to global `SEARCH_SKILLS.md`.

### VALUE HANDOFF
1. **Capability delta:** adds a reusable scientific run ledger/supervisor plus typed measured-hardware evidence, capture hashes and retry lineage.
2. **Graph edge:** complements H3's external-effect stack upstream of the executor by improving scientific/run provenance; it does not close the provider/device effect edge.
3. **Radar signal:** mature scientific frameworks are adding operational reliability and typed evidence layers after their headline algorithms become established, suggesting a broader research→production maturation pattern.
4. **Experiment impact:** supplies a concrete crash/restart/idempotency/evidence test reference that can be combined with BioModStack/Tangying-style physical-effect reconciliation primitives.
5. **Commercial impact:** exposes a nearer-term RF reproducibility/reliability retrofit with buyers distinct from autonomous-lab platform teams.
6. **Negative knowledge:** run-level idempotency + restart recovery + manual measurement provenance is not physical effect integrity; do not equate imported capture truth with authoritative instrument readback.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate deep inspections: 1 plus prior-provider comparators;
- source/test/schema/history traversals: ~18;
- external GitHub/web reads/searches: ~25;
- untrusted-repository code executions: 0.

## 2026-09-20 — Shadow Science Run 14

### Hypothesis
A second mature scientific repository whose headline scientific capability predates 2025 will contain a **recently added operational-reproducibility kernel** that is independently reusable: safer checkpoint publication, reconstructable scientific state, or restart semantics added after the core platform was already established. The hypothesis fails as a strong candidate if the new layer is merely documentation, if equivalent recovery existed unchanged for years, or if per-file safety is overstated as campaign-level crash consistency.

### Discovery modes
1. **Direct scientific reliability search:** mature molecular-simulation/HPC software with checkpoint, resume and restart behavior around expensive long-running campaigns.
2. **Code/invariant search:** `safesave`, `resume=True`, checkpoint serializers, reconstruction tests, flush/order behavior and multi-artifact writers rather than generic “checkpoint” mentions.
3. **Commit-history archaeology:** followed 2025–2026 OpenMM commits introducing generalized safe overwrite, `ReplicaExchangeReporter` and `ExpandedEnsembleSampler`, then subtracted the older baseline that OpenMM already supported checkpoints.
4. **Paper→code baseline validation + falsification:** used the 2017 OpenMM 7 paper to establish that the scientific platform long predates this reliability layer, then constructed a source-faithful crash-boundary model for the current multi-file reporter ordering.

Deep inspection was limited to `openmm/openmm` as the candidate, with the prior verified OpenDPD result as the H4 comparator. No untrusted repository code was executed.

### Best candidate
**openmm/openmm — recent safer checkpoint/restart hardening in a mature molecular-simulation platform**  
Canonical URL: https://github.com/openmm/openmm  
Exact revision: `5a7a268616b55d6a85e1c804f1c38681a2756cde`  
Revision date: 2026-09-18  
Public provenance: inspected Python source files carry OpenMM's permissive license grant; a single root `LICENSE` file was not established in this bounded pass.  
Evidence snapshot id: `shadow-science-20260920-openmm-recovery-5a7a268`

### Frozen evidence manifest
- head revision `5a7a268616b55d6a85e1c804f1c38681a2756cde`;
- `wrappers/python/openmm/app/internal/safesave.py` blob `63e4d77174b2d076ebc5ddebefe1e06ffa542a34`;
- `wrappers/python/openmm/app/replicaexchangereporter.py` blob `2721353d2e4d5c417f87b48a617f143bfef3e8e1`;
- `wrappers/python/tests/TestReplicaExchangeSampler.py` blob `7a497d4f631cffc7d0404e58c4e571fbf111d269`;
- `wrappers/python/openmm/app/expandedensemblesampler.py` at the pinned revision;
- `wrappers/python/tests/TestExpandedEnsembleSampler.py` blob `73ee69f47f4042b5ed8409c312f1b7edce03039f`;
- introducing commit `50f9085ca0471f69a866cc1fda903b9c1bd35c3c` (2025-07-24), “Always safely save checkpoints and states when filenames are given,” merged as `546d1a4e286cd1b3769027cc673c283081981eaa`;
- `ReplicaExchangeReporter` introduction `46376ea3e4d0ff37cdaa5e55e034dbf5c3296b81` (2026-04-17);
- `ExpandedEnsembleSampler` introduction `ce9fcace1c7c3835ab3970781a2bceebb3e563e7` (2026-05-05);
- current combined CI status at the pinned revision: Jenkins branch check **pending** at inspection, so green-head CI is UNKNOWN;
- external baseline: Eastman et al., *OpenMM 7: Rapid development of high performance algorithms for molecular dynamics*, PLOS Computational Biology, published 2017-07-26;
- current OpenMM development documentation exposes `ReplicaExchangeReporter(..., resume=True, checkpoints=True)` and describes resuming from saved checkpoint/log files.

### Specialist passes
- **CODE INSPECTOR:** traced filename-based checkpoint/state saves through `safesave`, inspected reporter write order and resume reconstruction, and separated single-file replacement semantics from multi-file campaign semantics.
- **SCIENCE / HISTORY VALIDATOR:** established that OpenMM's molecular-simulation platform and checkpointing long predate the 2025–2026 hardening, so novelty is assigned only to the new operational layer rather than to checkpointing itself.
- **TEST / SCHEMA VALIDATOR:** inspected reconstruction/resume regressions for replica exchange and expanded ensemble, including state, iteration, weights, log, energy, volume and trajectory continuation.
- **COMMERCIAL ANALYST:** evaluated value as a campaign-durability/restart audit for expensive molecular simulation rather than as another simulation engine.
- **RED-TEAM / VERIFIER:** challenged filesystem durability, concurrent writer behavior, multi-artifact atomicity, historical novelty and current CI state before scoring.

### Load-bearing claims
**IMPLEMENTED / TESTED**
- Filename-based `Simulation.saveCheckpoint()` and `saveState()` now route through the shared `safesave.save()` helper instead of directly overwriting the destination. The 2025 introducing commit explicitly broadened safer overwrite behavior across checkpoints/states.
- `ReplicaExchangeReporter` can restore every per-replica serialized `State`, the latest replica→thermodynamic-state assignment and `currentIteration`, then append subsequent outputs. Its regression test runs a campaign, destroys the sampler/simulation/integrator objects, reconstructs them with `resume=True`, verifies the restored serialized states, continues the campaign and validates log/energy/volume/trajectory output.
- `ExpandedEnsembleSampler` persists the sampler's algorithmic state together with an OpenMM `State` containing positions/velocities/parameters and supports `resume=True`. Its regression destroys and reconstructs the simulation stack, then verifies restored physical state, current step, iteration, state index and weights before continuing.
- The history makes the operational delta temporally clear: generalized safe overwrite landed in July 2025, while the new multistate reporter/sampler recovery paths arrived in April–May 2026, years after OpenMM's established scientific platform.

**INDEPENDENT FALSIFICATION / LIMITS**
- OpenMM already had checkpoint/restart functionality years before 2025. The newly valuable delta is safer/generalized overwrite plus newer multistate recovery, not checkpointing as a novel capability.
- `ReplicaExchangeReporter.__call__()` flushes the new log row and then updates checkpoint files one replica at a time. There is no inspected generation manifest or group commit tying the log plus every checkpoint to one atomic campaign generation.
- A source-faithful fault model injected a crash after the log and `checkpoint_0` advanced but before `checkpoint_1`. The resulting durable-looking set was `log=1`, `checkpoint_0=gen1`, `checkpoint_1=gen0`. Per-file safe replacement therefore does **not** establish campaign-level crash consistency.
- Current `safesave.py` writes a temporary file and then rename/replaces it, but performs no explicit file or parent-directory `fsync`; do not describe this as power-loss durability.
- The current `_getTempFilename()` docstring says an empty file is created/reserved, but the pinned implementation only checks `os.path.exists()` and returns a name. The original 2025 introducing commit used exclusive `open(name, 'x')`; the current implementation therefore exposes a potential concurrent-writer temp-name race that the old version avoided.
- The restart regressions destroy/reconstruct Python objects; they do not kill the OS process exactly between individual filesystem operations.
- The pinned revision's combined Jenkins status was still pending during inspection, so source/test presence is verified while a claim that the exact head's full CI passed is withheld.

### Independent RED-TEAM / VERIFIER
The verifier received the frozen source/test/history packet and the source-faithful crash artifact without the proposed score.

**Verdict: PASS_WITH_LIMITS for H4 and a WATCH-level operational-reproducibility component; do not promote to STRONG.**

Proof obligations:
1. **Is there a real post-core operational reliability delta? — PASS.** The 2025–2026 history adds generalized safer saves and reconstructable multistate resume behavior to a platform whose core scientific publication dates to 2017.
2. **Are the new capabilities in implementation/tests rather than README prose? — PASS.** Source plus dedicated reconstruction/resume tests cover the central narrower claims.
3. **Does single-file safe replacement imply campaign-level atomicity? — FAIL.** Reporter ordering can expose mixed generations after interruption.
4. **Does atomic rename/replace establish power-loss durability? — FAIL.** No explicit `fsync` protocol was found in the helper.
5. **Is concurrent temporary-name reservation robust at the pinned head? — NOT ESTABLISHED / POTENTIAL REGRESSION.** Current code checks existence without atomically reserving the name; the 2025 introducing version used exclusive creation.
6. **Is checkpoint/restart itself a 2025–2026 novelty? — FAIL.** It predates the hardening; novelty must be subtracted to the newer safer-overwrite and multistate-resume layer.
7. **Is current full CI green? — UNKNOWN.** The visible combined status was pending.

Strongest objection: this is valuable scientific reliability hardening, but the term **safe checkpoint** can invite an overclaim. The current implementation is safer per file and strongly reconstructable at ordinary restart boundaries; it is not a transactional, generation-consistent or proven power-loss-durable campaign snapshot.

### Proposed score
A) speed to first revenue: **3/5** — best as a focused audit/retrofit for existing simulation teams.  
B) customer value / ceiling: **3/5** — failed long-running simulations can waste meaningful GPU/HPC time, but this is a narrower budget than physical lab integrity.  
C) build/domain compression: **4/5** — state-complete checkpoints plus multistate reconstruction/tests save meaningful scientific engineering.  
D) rarity/advantage: **3/5** — operational hardening is useful but checkpoint/restart is established practice.  
E) evidence/completeness: **5/5** — strong source/tests/history plus a falsifiable ordering reproduction; exact head CI remains pending.  
F) rights/operability: **4/5** — inspected source carries permissive license text and OpenMM is mature, while this pass did not establish a single root SPDX/license file.  
**Total: 22/30 — WATCH_COMPONENT. Do not promote to STRONG.**

### Commercial / research implication
First paid wedge: **Molecular Simulation Campaign Durability / Restart Audit** for computational-chemistry, free-energy, replica-exchange and enhanced-sampling teams. Inject failures around checkpoint boundaries, measure mixed-generation exposure, and retrofit a generation ID + per-artifact hashes + a single manifest visibility point with process-kill qualification. The money path is avoided GPU/HPC reruns, less scientist time reconstructing interrupted campaigns, and fewer invalid analyses caused by silently inconsistent restart artifacts.

The strongest combination is **OpenDPD run/event/evidence lineage + OpenMM state-complete checkpoints**. OpenDPD contributes stable run identity, retry ancestry and explicit evidence semantics; OpenMM contributes reconstructable scientific state. A transactional manifest/generation layer would turn the pair into a more general scientific campaign snapshot/evidence kernel.

### Search lesson outcome
H4 receives a **second independent success**: OpenDPD exposed a recent crash-aware run/evidence layer inside a mature RF research project; OpenMM independently exposes 2025–2026 checkpoint/restart hardening inside a mature molecular-simulation platform. The LOCAL lesson **commit-history archaeology for operational reproducibility** is therefore **STAGED-eligible inside shadow evaluation**.

Do not edit global `SEARCH_SKILLS.md`. Refine the lesson before any wider promotion: subtract historical baseline capability, then test whether the new reliability guarantee is per-file, per-process, or truly campaign-wide. Search terms such as `checkpoint` or `resume` alone are too noisy and can surface ordinary pretrained-model loading or longstanding recovery features.

### VALUE HANDOFF
1. **Capability delta:** adds evidence for safer per-file checkpoint publication and state-complete multistate resume; a group-atomic campaign generation remains missing.
2. **Graph edge:** strengthens H4's research→production reliability pattern and combines naturally with OpenDPD's run/evidence lineage; it does not advance H3 physical-effect Level 3.
3. **Radar signal:** a second mature scientific codebase independently added an operational reliability layer after its scientific core was established, supporting a broader maturation signal beyond one domain.
4. **Experiment impact:** defines the next concrete crash test: generation-tag every campaign artifact, kill after each write boundary, and prove readers observe complete generation N or N+1 but never a mixed set.
5. **Commercial impact:** supports a fixed-scope simulation campaign durability audit with measurable failed-restart rate, mixed-generation incidence, rerun GPU-hours and scientist recovery time.
6. **Negative knowledge:** per-file atomic overwrite, `resume=True`, and object-reconstruction tests are each weaker than generation-consistent crash recovery; filesystem rename without explicit fsync is not power-loss durability.

### Cost proxies
- materially distinct discovery modes: 4;
- serious candidate deep inspections: 1 plus the prior OpenDPD comparator;
- source/test/history/status traversals: ~14;
- public web/documentation queries: 2;
- reproducible tests: 1 source-faithful crash-ordering model;
- untrusted-repository code executions: 0.
