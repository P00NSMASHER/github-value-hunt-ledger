# ACTIVATION RESPONSE LEARNING

Generation: **RESPLEARN:cf5e865f756d**
Mode: **observe_only_insufficient_evidence**
Resolved primary activations: **5 / 20**

V17 measures worker responsiveness only after fresh READY presence has produced a real activation.
READY→activation is system latency. Activation→claim is the only metric allowed to affect routing.
Claim→start and start→completion are descriptive only.

| Worker | Resolved | Claimed | Claim rate | Median activate→claim | Expired unclaimed | Routing adjustment | Evidence |
|---|---:|---:|---:|---:|---:|---:|---|
| HUNTER-01 | 1 | 1 | 100.0% | — | 0 | 0.000 | insufficient |
| HUNTER-02 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-03 | 2 | 0 | 0.0% | — | 2 | 0.000 | insufficient |
| HUNTER-04 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-05 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-06 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-07 | 1 | 1 | 100.0% | — | 0 | 0.000 | insufficient |
| HUNTER-08 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-09 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-10 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-11 | 1 | 0 | 0.0% | — | 1 | 0.000 | insufficient |
| HUNTER-12 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-13 | 0 | 0 | — | — | 0 | 0.000 | insufficient |
| HUNTER-14 | 0 | 0 | — | — | 0 | 0.000 | insufficient |

No adjustment is created from UNKNOWN/OFFLINE/PAUSED presence, unactivated READY events, pending activations, work-steal activations, or completion duration.
