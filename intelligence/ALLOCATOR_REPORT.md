# HUNT ALLOCATOR REPORT

- Generation: **ALLOCGEN:34f76c214c64**
- Candidate work items: **324**
- Assigned slots: **14 / 14**

## Portfolio mix

| Work kind | Slots |
|---|---:|
| adjacency | 2 |
| capability_gap | 1 |
| coverage_gap | 3 |
| experiment_execution | 5 |
| independent_verification | 1 |
| strategy_measurement | 1 |
| wildcard | 1 |

## Concentration controls

- Maximum assignments on one capability: **2** / allowed 2
- Maximum assignments on one experiment: **2** / allowed 2
- Maximum assignments using one strategy: **3** / allowed 3

## Guardrails

- Domain-specific STOP and authorization gates override allocator rank.
- BLOCKED_EXTERNAL experiments are not assigned as autonomous work.
- Coverage, adjacency or popularity never substitute for technical evidence.
- One wildcard slot is preserved even when exploitation scores are high.
- Do not send outreach, contact people, purchase services or take external actions without explicit authorization.
- Never inspect or retain credentials, private data, confidential material or accidental secrets.
- Automatic portfolio adaptation may move at most one slot per generation and only after sufficient attributed-run evidence.
- Manual overrides are measured separately and do not influence automatic portfolio adaptation.

## Interpretation

- The allocator combines existing measured intelligence; it does not create new evidence.
- READY/RUNNING experiments can outrank more repository discovery.
- Coverage and adjacency slots preserve exploration breadth while hard concentration caps prevent swarm collapse.
- One wildcard slot is always reserved for discoveries outside the current ontology.
- Manual overrides should be recorded in V9 run telemetry rather than silently editing historical scores.
