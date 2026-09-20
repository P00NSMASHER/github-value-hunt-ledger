# Production Upgrade Backlog

## P0 — must complete before any fleet-wide cutover

### P0.1 Finish frozen benchmark
- Owner: current 15-task system / Hunt 15 integrator.
- Exit: all 50 matched task pairs scored; frozen conclusion committed; no mid-test treatment changes.

### P0.2 Authoritative state service
- Deploy PostgreSQL using production/schema.sql.
- Implement append-only run/candidate/evidence/verification/skill/lease APIs.
- Exit: a legacy hunter can write/reconstruct a complete run without relying on chat transcript.

### P0.3 Evidence freeze service
- Store exact revision, claim list, evidence locators/hashes and manifest hash.
- Exit: mutation test invalidates verdict; old SHA remains reproducible after repository changes.

### P0.4 Independent verifier service
- Separate identity and read-only evidence permissions.
- Implement PASS / PASS_WITH_LIMITS / INCOMPLETE / CONTRADICTED / BLOCKED_SAFETY / BLOCKED_RIGHTS.
- Exit: planted executor self-certification is rejected.

### P0.5 Skill staging + held-out verifier
- Implement LOCAL -> STAGED -> VERIFIED -> CANARY -> GLOBAL states.
- Exit: one-success poisoning cannot become global; regression quarantines.

### P0.6 Task lease / dedupe service
- Durable task claim with owner/generation/expiry and stale recovery.
- Exit: collision/recovery tests pass without duplicate promotion.

### P0.7 External sandbox
- gVisor-class default isolation; higher-risk microVM option later.
- Exit: untrusted test workload cannot read host/sibling/cloud-metadata or unapproved network.

### P0.8 Governance / kill switch
- Route model/tool traffic through policy/budget/approval plane.
- Exit: budget runaway and global kill tests pass.

### P0.9 Hard sealed holdout
- Freeze after prompts/skills/runtime are frozen.
- Include README deception, stale authority, fail-open verification, rights ambiguity, hard negatives and cross-source disagreement.
- Exit: acceptance metrics in ARCHITECTURE.md are computed automatically.

## P1 — production-quality scale

### P1.1 Prime Agent worker adapter
- Pin revision; verify RPC, persistence, retained subagents, local refine and restart semantics.
- Global refine must be intercepted.
- Exit: kill/restart resumes goal without treating unverified work as complete.

### P1.2 Three-hunter shadow
- Post-benchmark AI/science/commercial lanes already wired.
- Exit: >=15 combined shadow runs; zero verifier bypass/sensitive incident; measurable yield/effort metrics.

### P1.3 Canary 3 -> 7 -> 15
- Roll verified global skills and persistent runtime gradually.
- Exit: zero skill regression in canary and no worse false-promotion rate than control.

### P1.4 Outcome attribution
- Link MASTER candidate -> experiment -> build effort -> revenue/savings.
- Exit: cost per validated MASTER and realized research ROI can be computed.

### P1.5 Integrator separation
- After frozen benchmark, move verifier/integrator outside the 15 researcher identities.
- Exit: all 15 lanes can research; trusted-state authority remains separate.

## P2 — leverage after core correctness

### P2.1 Preloop vs Archestra bake-off
- Compare policy enforcement, approvals, cost, identity/RBAC, deployment and licensing.
- Choose one governance path; do not run both in critical path.

### P2.2 Symphony downstream queue
- Convert approved build experiments into isolated implementation tasks with proof-of-work.
- Research truth remains upstream of Symphony.

### P2.3 Scientific branching specialist
- Adapt AI-Scientist-style branching hypotheses without making its code a core dependency.
- Exit: measurable quality/cost gain on scientific discovery tasks.

### P2.4 Patent/package emergence service
- Track independent implementations, papers, patents, packages and production adoption.
- Exit: radar signal can be recomputed from structured events rather than prose.

## Global launch rule
Do not call the system self-improving because it stores memory. Call it self-improving only when a verified skill improves an unseen task without increasing false promotion or unacceptable cost.
