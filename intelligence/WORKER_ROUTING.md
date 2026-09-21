# WORKER ROUTING PLAN

Routing generation: **ROUTING:c05003d3cbf5**
Worker profiles: **WORKERS:fc22659849b1**

V12/V13 routes workers using positive historical fit, assignment priority, and evidence-gated routing outcome adjustments. Active V11 claims remain locked.

Routing learning: **ROUTELEARN:bc40639ef4db** / mode **observe_only_insufficient_evidence**
Activation-response learning: **RESPLEARN:efdfca633185** / mode **observe_only_insufficient_evidence**

| Worker | Profile | Route | Slot | Assignment | Score | Reason |
|---|---|---|---|---|---:|---|
| HUNTER-01 | SPARSE | ROUTED | SLOT-09 | ASSIGN:be768c686587:slot-09 | 13.90 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-02 | UNMEASURED | ROUTED | SLOT-05 | ASSIGN:be768c686587:slot-05 | 13.74 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-03 | SPARSE | ROUTED | SLOT-08 | ASSIGN:be768c686587:slot-08 | 13.23 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-04 | SPARSE | ROUTED | SLOT-03 | ASSIGN:be768c686587:slot-03 | 25.79 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-05 | SPARSE | ROUTED | SLOT-01 | ASSIGN:be768c686587:slot-01 | 19.20 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-06 | MEASURED | ROUTED | SLOT-02 | ASSIGN:be768c686587:slot-02 | 17.22 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-07 | SPARSE | ROUTED | SLOT-04 | ASSIGN:be768c686587:slot-04 | 21.42 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-08 | UNMEASURED | ROUTED | SLOT-10 | ASSIGN:be768c686587:slot-10 | 15.12 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-09 | SPARSE | ROUTED | SLOT-07 | ASSIGN:be768c686587:slot-07 | 20.17 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-10 | UNMEASURED | ROUTED | SLOT-11 | ASSIGN:be768c686587:slot-11 | 15.00 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-11 | SPARSE | ROUTED | SLOT-14 | ASSIGN:be768c686587:slot-14 | 11.55 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-12 | UNMEASURED | ROUTED | SLOT-12 | ASSIGN:be768c686587:slot-12 | 11.64 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-13 | SPARSE | ROUTED | SLOT-06 | ASSIGN:be768c686587:slot-06 | 16.78 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-14 | UNMEASURED | ROUTED | SLOT-13 | ASSIGN:be768c686587:slot-13 | 14.56 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |

## Routing interpretation

- Assignment priority is preserved in every worker-slot score.
- Historical strategy, objective, experiment, capability, domain and completed-role experience can only add fit.
- Unmeasured workers get an exploration bonus; they are not treated as low quality.
- Current active claims are locked and consume worker capacity.
- V13 learned task-context adjustments are zero unless routing_learning_policy evidence thresholds are satisfied.
- V17 activation-response adjustment is penalty-only and stays zero until READY→activation→claim evidence thresholds are satisfied.
- Routing is recomputed after execution-state, telemetry, outcomes, or routing-learning changes.
