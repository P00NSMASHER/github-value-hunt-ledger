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
