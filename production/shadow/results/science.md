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
