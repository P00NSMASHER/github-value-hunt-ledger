# WORKER ROUTING PLAN

Routing generation: **ROUTING:4cbdac332260**
Worker profiles: **WORKERS:d1242505c989**

V12/V13 routes workers using positive historical fit, assignment priority, and evidence-gated routing outcome adjustments. Active V11 claims remain locked.

Routing learning: **ROUTELEARN:bc40639ef4db** / mode **observe_only_insufficient_evidence**
Activation-response learning: **RESPLEARN:5e7e2a0c8a79** / mode **observe_only_insufficient_evidence**
Routing exploration: **ROUTEEXP:a7b5b644916a** / applied **False**

| Worker | Profile | Route | Slot | Assignment | Score | Reason |
|---|---|---|---|---|---:|---|
| HUNTER-01 | LOCKED_ACTIVE_CLAIM | LOCKED | SLOT-07 | ASSIGN:34f76c214c64:slot-07 | — | Existing V11 active claim is authoritative and preserved. |
| HUNTER-02 | UNMEASURED | ROUTED | SLOT-08 | ASSIGN:20e446545c5f:slot-08 | 12.43 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-03 | SPARSE | ROUTED | SLOT-02 | ASSIGN:20e446545c5f:slot-02 | 26.03 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-04 | SPARSE | ROUTED | SLOT-06 | ASSIGN:20e446545c5f:slot-06 | 23.59 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-05 | MEASURED | ROUTED | SLOT-09 | ASSIGN:20e446545c5f:slot-09 | 11.92 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-06 | MEASURED | ROUTED | SLOT-03 | ASSIGN:20e446545c5f:slot-03 | 26.24 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-07 | MEASURED | ROUTED | SLOT-05 | ASSIGN:20e446545c5f:slot-05 | 25.16 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-08 | LOCKED_ACTIVE_CLAIM | LOCKED | SLOT-04 | ASSIGN:71337ecbacfb:slot-04 | — | Existing V11 active claim is authoritative and preserved. |
| HUNTER-09 | SPARSE | ROUTED | SLOT-01 | ASSIGN:20e446545c5f:slot-01 | 28.10 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-10 | UNMEASURED | ROUTED | SLOT-10 | ASSIGN:20e446545c5f:slot-10 | 16.15 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-11 | MEASURED | ROUTED | SLOT-14 | ASSIGN:20e446545c5f:slot-14 | 11.09 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-12 | UNMEASURED | ROUTED | SLOT-11 | ASSIGN:20e446545c5f:slot-11 | 16.15 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-13 | MEASURED | ROUTED | SLOT-13 | ASSIGN:20e446545c5f:slot-13 | 28.20 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |
| HUNTER-14 | UNMEASURED | ROUTED | SLOT-12 | ASSIGN:20e446545c5f:slot-12 | 11.63 | Maximum-total-fit exact assignment across currently idle registered workers and claimable slots. |

## Routing interpretation

- Assignment priority is preserved in every worker-slot score.
- Historical strategy, objective, experiment, capability, domain and completed-role experience can only add fit.
- Unmeasured workers get an exploration bonus; they are not treated as low quality.
- Current active claims are locked and consume worker capacity.
- V13 learned task-context adjustments are zero unless routing_learning_policy evidence thresholds are satisfied.
- V17 activation-response adjustment is penalty-only and stays zero until READY→activation→claim evidence thresholds are satisfied.
- V18 may apply at most one deterministic low-regret matched worker swap to create controlled assignment variation.
- Routing is recomputed after execution-state, telemetry, outcomes, or routing-learning changes.
