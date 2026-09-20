# DISPATCH BOARD

Dispatch generation: **DISPATCHGEN:3c7a1c700fc4**

Generated dispatch tickets bind V12/V13 routing decisions to V11 claims. A generated claim must present the exact ticket below.

| Worker | Slot | Assignment | Dispatch ticket | Routing score | Claim file |
|---|---|---|---|---:|---|
| HUNTER-05 | SLOT-01 | ASSIGN:51522654b284:slot-01 | DISPATCH:67551dbb93ef | 19.2169 | intelligence/execution_events/SLOT-01.jsonl |
| HUNTER-06 | SLOT-02 | ASSIGN:51522654b284:slot-02 | DISPATCH:2c5cfe00cd7a | 17.2222 | intelligence/execution_events/SLOT-02.jsonl |
| HUNTER-13 | SLOT-03 | ASSIGN:51522654b284:slot-03 | DISPATCH:2b72e0a3e66e | 15.8780 | intelligence/execution_events/SLOT-03.jsonl |
| HUNTER-07 | SLOT-04 | ASSIGN:51522654b284:slot-04 | DISPATCH:188619272b97 | 21.5274 | intelligence/execution_events/SLOT-04.jsonl |
| HUNTER-04 | SLOT-05 | ASSIGN:51522654b284:slot-05 | DISPATCH:44f105ac0993 | 25.7300 | intelligence/execution_events/SLOT-05.jsonl |
| HUNTER-03 | SLOT-06 | ASSIGN:51522654b284:slot-06 | DISPATCH:9ab353e106cb | 15.7878 | intelligence/execution_events/SLOT-06.jsonl |
| HUNTER-09 | SLOT-07 | ASSIGN:51522654b284:slot-07 | DISPATCH:7e181fa1a30b | 19.2199 | intelligence/execution_events/SLOT-07.jsonl |
| HUNTER-02 | SLOT-08 | ASSIGN:51522654b284:slot-08 | DISPATCH:f1f35ad3a064 | 15.1180 | intelligence/execution_events/SLOT-08.jsonl |
| HUNTER-08 | SLOT-09 | ASSIGN:51522654b284:slot-09 | DISPATCH:2924d80c171d | 14.1988 | intelligence/execution_events/SLOT-09.jsonl |
| HUNTER-01 | SLOT-10 | ASSIGN:51522654b284:slot-10 | DISPATCH:2d28b0a3afdb | 16.4299 | intelligence/execution_events/SLOT-10.jsonl |
| HUNTER-10 | SLOT-11 | ASSIGN:51522654b284:slot-11 | DISPATCH:c635d6c3ed20 | 15.1180 | intelligence/execution_events/SLOT-11.jsonl |
| HUNTER-12 | SLOT-12 | ASSIGN:51522654b284:slot-12 | DISPATCH:97d2e939fd36 | 11.6380 | intelligence/execution_events/SLOT-12.jsonl |
| HUNTER-14 | SLOT-13 | ASSIGN:51522654b284:slot-13 | DISPATCH:6152f74c7e2f | 14.5600 | intelligence/execution_events/SLOT-13.jsonl |
| HUNTER-11 | SLOT-14 | ASSIGN:51522654b284:slot-14 | DISPATCH:c9f4ee58b9b7 | 11.5475 | intelligence/execution_events/SLOT-14.jsonl |

## Claim modes

- **generated** — use the current dispatch ticket exactly; this is eligible for routing-learning attribution.
- **manual_override** — allowed only with an explicit reason; it is excluded from generated-route learning.

Current dispatch tickets are derived from claimable V11 slots only. Active/locked workers do not receive a new ticket.
