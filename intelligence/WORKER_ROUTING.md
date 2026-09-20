# WORKER ROUTING PLAN

Routing generation: **ROUTING:ff524bcab4b2**
Worker profiles: **WORKERS:dde32346eaff**

V12/V13 routes workers using positive historical fit, assignment priority, and evidence-gated routing outcome adjustments. Active V11 claims remain locked.

Routing learning: **ROUTELEARN:3427dfe228b7** / mode **observe_only_insufficient_evidence**

| Worker | Profile | Route | Slot | Assignment | Score | Reason |
|---|---|---|---|---|---:|---|
| HUNTER-01 | SPARSE | ROUTED | SLOT-10 | ASSIGN:51522654b284:slot-10 | 16.43 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-02 | UNMEASURED | ROUTED | SLOT-08 | ASSIGN:51522654b284:slot-08 | 15.12 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-03 | SPARSE | ROUTED | SLOT-06 | ASSIGN:51522654b284:slot-06 | 15.79 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-04 | SPARSE | ROUTED | SLOT-05 | ASSIGN:51522654b284:slot-05 | 25.73 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-05 | SPARSE | ROUTED | SLOT-01 | ASSIGN:51522654b284:slot-01 | 19.22 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-06 | MEASURED | ROUTED | SLOT-02 | ASSIGN:51522654b284:slot-02 | 17.22 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-07 | SPARSE | ROUTED | SLOT-04 | ASSIGN:51522654b284:slot-04 | 21.53 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-08 | UNMEASURED | ROUTED | SLOT-09 | ASSIGN:51522654b284:slot-09 | 14.20 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-09 | SPARSE | ROUTED | SLOT-07 | ASSIGN:51522654b284:slot-07 | 19.22 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-10 | UNMEASURED | ROUTED | SLOT-11 | ASSIGN:51522654b284:slot-11 | 15.12 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-11 | SPARSE | ROUTED | SLOT-14 | ASSIGN:51522654b284:slot-14 | 11.55 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-12 | UNMEASURED | ROUTED | SLOT-12 | ASSIGN:51522654b284:slot-12 | 11.64 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-13 | SPARSE | ROUTED | SLOT-03 | ASSIGN:51522654b284:slot-03 | 15.88 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-14 | UNMEASURED | ROUTED | SLOT-13 | ASSIGN:51522654b284:slot-13 | 14.56 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |

## Routing interpretation

- Assignment priority is preserved in every worker-slot score.
- Historical strategy, objective, experiment, capability, domain and completed-role experience can only add fit.
- Unmeasured workers get an exploration bonus; they are not treated as low quality.
- Current active claims are locked and consume worker capacity.
- V13 learned adjustments are zero unless routing_learning_policy evidence thresholds are satisfied.
- Routing is recomputed after execution-state, telemetry, outcomes, or routing-learning changes.
