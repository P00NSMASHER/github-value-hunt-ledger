# WORKER ROUTING PLAN

Routing generation: **ROUTING:0bf9660a0ff1**
Worker profiles: **WORKERS:90e860630e42**

V12/V13 routes workers using positive historical fit, assignment priority, and evidence-gated routing outcome adjustments. Active V11 claims remain locked.

Routing learning: **ROUTELEARN:3427dfe228b7** / mode **observe_only_insufficient_evidence**

| Worker | Profile | Route | Slot | Assignment | Score | Reason |
|---|---|---|---|---|---:|---|
| HUNTER-01 | SPARSE | ROUTED | SLOT-10 | ASSIGN:eb05f1921aad:slot-10 | 16.44 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-02 | UNMEASURED | ROUTED | SLOT-04 | ASSIGN:eb05f1921aad:slot-04 | 15.60 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-03 | SPARSE | ROUTED | SLOT-07 | ASSIGN:eb05f1921aad:slot-07 | 14.15 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-04 | SPARSE | ROUTED | SLOT-02 | ASSIGN:eb05f1921aad:slot-02 | 20.93 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-05 | SPARSE | ROUTED | SLOT-03 | ASSIGN:eb05f1921aad:slot-03 | 19.23 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-06 | LOCKED_ACTIVE_CLAIM | LOCKED | SLOT-01 | ASSIGN:eb05f1921aad:slot-01 | — | Existing V11 active claim is authoritative and preserved. |
| HUNTER-07 | SPARSE | ROUTED | SLOT-06 | ASSIGN:eb05f1921aad:slot-06 | 21.55 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-08 | UNMEASURED | ROUTED | SLOT-11 | ASSIGN:eb05f1921aad:slot-11 | 15.12 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-09 | SPARSE | ROUTED | SLOT-08 | ASSIGN:eb05f1921aad:slot-08 | 19.23 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-10 | UNMEASURED | ROUTED | SLOT-12 | ASSIGN:eb05f1921aad:slot-12 | 11.64 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-11 | SPARSE | ROUTED | SLOT-09 | ASSIGN:eb05f1921aad:slot-09 | 18.67 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-12 | UNMEASURED | ROUTED | SLOT-13 | ASSIGN:eb05f1921aad:slot-13 | 14.56 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-13 | SPARSE | ROUTED | SLOT-05 | ASSIGN:eb05f1921aad:slot-05 | 15.88 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-14 | UNMEASURED | ROUTED | SLOT-14 | ASSIGN:eb05f1921aad:slot-14 | 13.00 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |

## Routing interpretation

- Assignment priority is preserved in every worker-slot score.
- Historical strategy, objective, experiment, capability, domain and completed-role experience can only add fit.
- Unmeasured workers get an exploration bonus; they are not treated as low quality.
- Current active claims are locked and consume worker capacity.
- V13 learned adjustments are zero unless routing_learning_policy evidence thresholds are satisfied.
- Routing is recomputed after execution-state, telemetry, outcomes, or routing-learning changes.
