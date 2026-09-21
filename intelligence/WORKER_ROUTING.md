# WORKER ROUTING PLAN

Routing generation: **ROUTING:a26fa288ad53**
Worker profiles: **WORKERS:fc22659849b1**

V12/V13 routes workers using positive historical fit, assignment priority, and evidence-gated routing outcome adjustments. Active V11 claims remain locked.

Routing learning: **ROUTELEARN:bc40639ef4db** / mode **observe_only_insufficient_evidence**
Activation-response learning: **RESPLEARN:5e9d152cf4a8** / mode **observe_only_insufficient_evidence**
Routing exploration: **ROUTEEXP:a585fc62d929** / applied **True**

| Worker | Profile | Route | Slot | Assignment | Score | Reason |
|---|---|---|---|---|---:|---|
| HUNTER-01 | SPARSE | ROUTED | SLOT-08 | ASSIGN:c080a1f0d909:slot-08 | 13.54 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-02 | UNMEASURED | ROUTED | SLOT-03 | ASSIGN:c080a1f0d909:slot-03 | 15.66 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-03 | SPARSE | ROUTED | SLOT-02 | ASSIGN:c080a1f0d909:slot-02 | 15.78 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-04 | SPARSE | ROUTED | SLOT-04 | ASSIGN:c080a1f0d909:slot-04 | 16.42 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-05 | SPARSE | ROUTED | SLOT-07 | ASSIGN:c080a1f0d909:slot-07 | 12.10 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-06 | MEASURED | ROUTED | SLOT-06 | ASSIGN:c080a1f0d909:slot-06 | 26.24 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-07 | SPARSE | ROUTED | SLOT-13 | ASSIGN:c080a1f0d909:slot-13 | 15.75 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-08 | UNMEASURED | ROUTED | SLOT-09 | ASSIGN:c080a1f0d909:slot-09 | 13.23 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-09 | SPARSE | ROUTED | SLOT-01 | ASSIGN:c080a1f0d909:slot-01 | 19.97 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-10 | UNMEASURED | ROUTED | SLOT-11 | ASSIGN:c080a1f0d909:slot-11 | 16.17 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-11 | SPARSE | ROUTED | SLOT-14 | ASSIGN:c080a1f0d909:slot-14 | 11.55 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-12 | UNMEASURED | ROUTED | SLOT-10 | ASSIGN:c080a1f0d909:slot-10 | 16.17 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-13 | SPARSE | ROUTED | SLOT-05 | ASSIGN:c080a1f0d909:slot-05 | 19.17 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-14 | UNMEASURED | ROUTED | SLOT-12 | ASSIGN:c080a1f0d909:slot-12 | 11.64 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |

## Routing interpretation

- Assignment priority is preserved in every worker-slot score.
- Historical strategy, objective, experiment, capability, domain and completed-role experience can only add fit.
- Unmeasured workers get an exploration bonus; they are not treated as low quality.
- Current active claims are locked and consume worker capacity.
- V13 learned task-context adjustments are zero unless routing_learning_policy evidence thresholds are satisfied.
- V17 activation-response adjustment is penalty-only and stays zero until READY→activation→claim evidence thresholds are satisfied.
- V18 may apply at most one deterministic low-regret matched worker swap to create controlled assignment variation.
- Routing is recomputed after execution-state, telemetry, outcomes, or routing-learning changes.
