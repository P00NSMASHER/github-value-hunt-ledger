# WORKER ROUTING PLAN

Routing generation: **ROUTING:24b43dc0ec51**
Worker profiles: **WORKERS:45cdbf855c3e**

V12/V13 routes workers using positive historical fit, assignment priority, and evidence-gated routing outcome adjustments. Active V11 claims remain locked.

Routing learning: **ROUTELEARN:bc40639ef4db** / mode **observe_only_insufficient_evidence**
Activation-response learning: **RESPLEARN:fe6cd179d69a** / mode **measured_feedback**
Routing exploration: **ROUTEEXP:3270f1f97388** / applied **False**

| Worker | Profile | Route | Slot | Assignment | Score | Reason |
|---|---|---|---|---|---:|---|
| HUNTER-01 | MEASURED | ROUTED | SLOT-07 | ASSIGN:b88db354751e:slot-07 | 18.30 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-02 | UNMEASURED | ROUTED | SLOT-08 | ASSIGN:b88db354751e:slot-08 | 12.43 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-03 | SPARSE | ROUTED | SLOT-02 | ASSIGN:b88db354751e:slot-02 | 26.03 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-04 | SPARSE | ROUTED | SLOT-06 | ASSIGN:b88db354751e:slot-06 | 28.25 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-05 | MEASURED | ROUTED | SLOT-11 | ASSIGN:b88db354751e:slot-11 | 13.32 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-06 | MEASURED | ROUTED | SLOT-03 | ASSIGN:b88db354751e:slot-03 | 26.24 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-07 | MEASURED | ROUTED | SLOT-05 | ASSIGN:b88db354751e:slot-05 | 25.16 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-08 | SPARSE | ROUTED | SLOT-04 | ASSIGN:b88db354751e:slot-04 | 23.51 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-09 | SPARSE | ROUTED | SLOT-01 | ASSIGN:b88db354751e:slot-01 | 28.10 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-10 | UNMEASURED | ROUTED | SLOT-09 | ASSIGN:b88db354751e:slot-09 | 12.79 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-11 | MEASURED | ROUTED | SLOT-12 | ASSIGN:b88db354751e:slot-12 | 12.66 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-12 | UNMEASURED | ROUTED | SLOT-10 | ASSIGN:b88db354751e:slot-10 | 16.15 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-13 | MEASURED | ROUTED | SLOT-13 | ASSIGN:b88db354751e:slot-13 | 32.97 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-14 | UNMEASURED | ROUTED | SLOT-14 | ASSIGN:b88db354751e:slot-14 | 13.00 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |

## Routing interpretation

- Assignment priority is preserved in every worker-slot score.
- Historical strategy, objective, experiment, capability, domain and completed-role experience can only add fit.
- Unmeasured workers get an exploration bonus; they are not treated as low quality.
- Current active claims are locked and consume worker capacity.
- V13 learned task-context adjustments are zero unless routing_learning_policy evidence thresholds are satisfied.
- V17 activation-response adjustment is penalty-only and stays zero until READY→activation→claim evidence thresholds are satisfied.
- V18 may apply at most one deterministic low-regret matched worker swap to create controlled assignment variation.
- Routing is recomputed after execution-state, telemetry, outcomes, or routing-learning changes.
