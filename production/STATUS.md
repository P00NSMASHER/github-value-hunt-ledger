# Production Upgrade Status — 2026-09-20

## Implemented now
- Reference architecture committed: production/ARCHITECTURE.md.
- Typed role and authority contracts committed: production/ROLE_CONTRACTS.md.
- Production role prompts committed: production/PROMPTS.md.
- Deterministic prototype committed: production/prototype.py.
- Prototype tests committed: production/test_prototype.py.
- Local execution result before commit: **11/11 tests passed**.
- Reference PostgreSQL schema committed: production/schema.sql.
- Three shadow state/result ledgers initialized under production/shadow/.
- Shadow protocol committed: production/SHADOW_PILOT.md.
- Three existing benchmark experiment automations have a post-benchmark shadow override:
  - Hunt 10 -> commercial/direct-money shadow;
  - Hunt 12 -> scientific software shadow;
  - Hunt 14 -> AI/agent-infrastructure shadow.
- The frozen benchmark itself was not modified.

## Deterministic rules currently encoded in prototype
- exact revision required;
- independent verifier required;
- frozen evidence snapshot required;
- README-only core claim cannot promote;
- sensitive-source contamination fails closed;
- critical contradiction fails closed;
- clean verified high score becomes MASTER_CANDIDATE, never automatic MASTER;
- one skill success remains local;
- two successes only stage a skill;
- held-out/adversarial/adjacent-domain/canary gates precede global skill;
- any held-out/canary regression quarantines;
- leases prevent duplicate active work and support stale recovery by generation.

## Live but prompt-enforced
The current scheduled system still executes through ChatGPT automations and GitHub shared memory, not a deployed Prime Agent runtime. The production contracts are therefore enforced partly by prompt/ledger discipline until the external runtime/control plane exists.

## Not yet deployed because they require external infrastructure
- Prime Agent daemon/RPC worker pool.
- External PostgreSQL instance using production/schema.sql.
- Immutable object store for evidence bytes.
- Preloop or Archestra governance deployment.
- gVisor/Firecracker sandbox broker.
- Independent service identity/RBAC outside agent prompts.
- Separate verifier process with read-only evidence credentials.
- External kill switch terminating model/tool traffic.
- Symphony downstream engineering queue.

These are deployment tasks, not research-design gaps. They should not be represented as already live.

## Next launch gate
Finish the frozen 50-task A/B benchmark. Do not promote the new architecture fleet-wide before:
1. benchmark completes;
2. post-benchmark shadow phase accumulates at least 15 combined runs;
3. harder sealed holdout is frozen;
4. external runtime/governance/sandbox is deployed and passes security tests.
