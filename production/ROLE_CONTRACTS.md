# Role and Interface Contracts

## Specialist task envelope
Required fields: task_id, candidate_id, exact_revision, role, question, allowed_sources, allowed_tools, evidence_snapshot_id or null during discovery, token/time/tool budget, requested outputs.

Specialist output: role, claims, evidence_refs, contradictions, unknowns, confidence (HIGH|MEDIUM|LOW|BLOCKED), recommended_verdict, resource_usage, trace_id.

## Hunter contract
Hunter may search public/authorized sources, create hypotheses/candidates, collect non-sensitive evidence, spawn typed specialists, and write lane-local findings/shadow proposals.

Hunter may not write MASTER, edit verifier verdicts, globally promote skills, execute untrusted repo code outside a sandbox, or use accidental credentials/private/confidential material.

For Freight Recovery, hunter work additionally requires an approved EXP-001-linked freight work request: named gap_id, allowed trigger, commercial-decision evidence, insufficiency statement, and stop condition. Broad generic freight subsystem discovery is outside contract until the commercialization freeze is lifted.

Completion packet: candidate URI + exact revision; load-bearing claims separated into VERIFIED/CLAIMED/PLANNED/UNKNOWN; evidence manifest; strongest objection; commercial wedge; A-F proposed score; referrals; candidate lessons (local only).

## Verifier contract
Input is a frozen evidence snapshot. No hunter scratch state and no promotion score.
Proof obligations: exact identity/revision; central capability implemented; source/test/reproduction evidence; claim boundaries explicit; contradictions assessed; simpler/commonplace alternative checked; evidence independent of sensitive/accidental material; verdict reproducible from snapshot.

Allowed verdicts: PASS | PASS_WITH_LIMITS | INCOMPLETE | CONTRADICTED | BLOCKED_SAFETY | BLOCKED_RIGHTS.
Verifier may not mutate candidate evidence or workspace.

## Red-team contract
Receive candidate thesis + frozen evidence, not its score. Identify the least-supported claim, closest commodity alternative, benchmark/circularity risk, README-only claims, operational blocker and evidence that would reverse the recommendation.

## Skill promoter contract
1 success -> local memory only. 2 distinct successes -> STAGED. Then require >=5 held-out tasks, 100% pass, zero regressions, adversarial pass, adjacent-domain pass, separate curator approval and a 3-hunter zero-regression canary. Only then GLOBAL. Any regression -> QUARANTINED until a new version passes the full gate.

## Integrator contract
Only Integrator may write MASTER, write globally verified SEARCH_SKILLS, approve MASTER promotions, and approve GLOBAL skill versions. Integrator must use verifier output and frozen evidence; UNKNOWN cannot be converted into fact.

Freight-specific promotion also requires a valid freight work request and an explicit link to EXP-001 or a paying-customer gap. A technically strong component with no named freight gap remains lane-local/WATCH rather than expanding the Freight Recovery critical path.

## Referral contract
A referral records source lane/run, destination lane/role, candidate + exact revision, exact unanswered question, evidence refs, dedupe/capability fingerprint, priority and task/lease identity.
