# ACTIVATION RESPONSE LEARNING

Generation: **RESPLEARN:b9d234e59f1a**
Mode: **measured_feedback**
Resolved primary activations: **35 / 20**

V17 measures worker responsiveness only after fresh READY presence has produced a real activation.
READY→activation is system latency. Activation→claim is the only metric allowed to affect routing.
Claim→start and start→completion are descriptive only.

| Worker | Resolved | Claimed | Claim rate | Median activate→claim | Expired unclaimed | Routing adjustment | Evidence |
|---|---:|---:|---:|---:|---:|---:|---|
| HUNTER-01 | 1 | 1 | 100.0% | — | 0 | 0.000 | insufficient |
| HUNTER-02 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-03 | 10 | 1 | 10.0% | — | 9 | 0.000 | insufficient |
| HUNTER-04 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-05 | 9 | 1 | 11.1% | — | 8 | 0.000 | insufficient |
| HUNTER-06 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-07 | 3 | 1 | 33.3% | — | 2 | 0.000 | insufficient |
| HUNTER-08 | 7 | 2 | 28.6% | 1.6 | 5 | -0.429 | sufficient |
| HUNTER-09 | 4 | 1 | 25.0% | — | 3 | 0.000 | insufficient |
| HUNTER-10 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-11 | 1 | 0 | 0.0% | — | 1 | 0.000 | insufficient |
| HUNTER-12 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-13 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-14 | 0 | 0 | — | — | 0 | 0.000 | insufficient |

No adjustment is created from UNKNOWN/OFFLINE/PAUSED presence, unactivated READY events, pending activations, work-steal activations, or completion duration.
