# Pair 5 — CONTROL results

Frozen benchmark result log. Append one task result block per scheduled run. Do not rewrite prior completed blocks.

TASK: 30
CONDITION: CONTROL
STARTING HYPOTHESIS: A strong match will separate the worker from an independent acceptance reviewer, persist the original goal/gates and task state outside chat context, and resume from durable state rather than relying on transcript memory.
DISCOVERY METHODS: Broad web search for manager/executor/auditor and task-ledger architectures; targeted search for independent verifier/supervisor + resume/ledger patterns; code/tree inspection of the strongest candidate's runtime templates and real-run evidence.
CANDIDATE: levi-qiao/longgraph-skill — loop-graph architecture
CANONICAL URL: https://github.com/levi-qiao/longgraph-skill
EXACT REVISION: b27376fd44f30505cbc52c2520c42e725b028ea1
VERDICT: STRONG
A-F SCORE: A4 B4 C5 D5 E4 F5 = 27/30
EVIDENCE INSPECTED: Repository metadata/license and exact head commit; skills/loop-graph/templates/executor.md; templates/supervisor.md; templates/ledger.md; loop-graph README; redacted-multiday-control-plane example. The implementation is a Markdown control-plane rather than an orchestration server, but the actual runtime contracts are present: executor is sole ledger writer, supervisor has separate context and only reads ledger/writes directives, milestone promotion cannot self-pass, and durable run state is explicitly carried in ledger/directives/ops files.
CLAIMS VERIFIED: Independent verification is structurally enforced: supervisor starts from separate context, treats transcripts as hearsay, re-runs gates, inspects real diffs/artifacts against North Star/acceptance criteria, and can accept/redo/stop through a one-way directives edge. Executor may mark a milestone pending-audit but cannot advance until supervisor acceptance lands. Durable task state is explicit in ledger status/current slice/gate scoreboard/pending promotion/gap register/round log, with archived cold history and bounded live files. Resume behavior is explicit: each activation rereads durable files, timers or another host can restart against the same workspace, and no node depends on chat memory. A redacted multi-day example reports tens of rounds on one durable ledger and a clean-context supervisor overturning self-reported done when evidence was not independent.
CLAIMS NOT VERIFIED: No independently reproducible private production run was available; the multi-day real-run evidence is intentionally redacted. I did not verify a large third-party deployment, measured defect-reduction rate, or economic ROI. The architecture does not itself provide a durable orchestration runtime/server; host timers/schedulers execute the nodes.
STRONGEST OBJECTION: This is a sophisticated prompt/file-state architecture, not an executable workflow engine. Most evidence for effectiveness is maintained by the project itself, and the strongest real-run example cannot be publicly replayed, so operational robustness at enterprise scale remains less proven than the control-plane design.
COMMERCIAL WEDGE: Managed verified coding-agent control plane for teams running long migrations/refactors: compile original requirements and gates into a durable run, let a lower-cost executor work continuously, and sell clean-context acceptance audits/checkpointing/governance as a per-team or per-run service.
SEARCH EFFORT: 8 materially distinct external search queries; 1 candidate deep-inspected across repository metadata plus 5 implementation/evidence files.
FALSE-PROMOTION RISK: LOW-MEDIUM — task fit is unusually exact and source-level runtime contracts are concrete, but effectiveness claims beyond structural enforcement have limited independent production evidence.
LESSON: N/A
COMPLETED_AT: 2026-09-20T01:33:03-04:00
