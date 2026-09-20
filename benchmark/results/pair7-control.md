# Pair 7 — CONTROL results

Frozen benchmark result log. Append one task result block per scheduled run. Do not rewrite prior completed blocks.

TASK: 44
CONDITION: CONTROL
STARTING HYPOTHESIS: A strong match should restore a real PostgreSQL backup into an isolated scratch database, then independently fail on corrupted artifacts, stale verification coverage, and invalid/unverified restore state rather than treating backup creation as proof.
DISCOVERY METHODS: Direct public-GitHub/web search for PostgreSQL restore verification and restore drills; hosted-Postgres/Supabase/Neon-oriented search; negative-control search using corruption/stale/unverified terminology; comparison against adjacent restore-drill candidates before deep inspection.
CANDIDATE: vncwr/backwyn
CANONICAL URL: https://github.com/vncwr/backwyn
EXACT REVISION: 57f4b8afc3d9ce14f2a35febc802536cfa816839
VERDICT: STRONG
A-F SCORE: A=5, B=4, C=5, D=5, E=5, F=5; Total=29/30
EVIDENCE INSPECTED: Repository metadata/license; exact commit; scripts/localtest.sh; tests/check/check_test.go; .github/workflows/ci.yml; GitHub Actions run 29473799797 and jobs for PostgreSQL 15/17. The E2E script creates its own source and scratch databases, performs backup->verify->restore, compares restored row counts to source, tampers with the encrypted artifact, requires corruption verification failure, forces stale-coverage failure, refuses unverified restore, and checks prune safety when no verified backup remains. Unit tests separately cover no-backup, stale verified backup, broken latest backup, none-verified, and ordering/freshness semantics. CI at the inspected commit completed successfully, including end-to-end jobs on PostgreSQL 15 and 17 plus race-tested unit tests/build.
CLAIMS VERIFIED: Real scratch restore occurs against throwaway PostgreSQL databases; restored data is compared to source row counts; corruption is deliberately injected and must fail verification; a failed verification query marks the backup unverified and a passing re-verification restores verified status; stale proof is unhealthy under max-age; unverified backups do not count as coverage; newer broken backups do not mask the age of older verified coverage; restore refuses non-empty targets, the source database, and unverified backups by default; even the allow-unverified escape hatch still fails on a corrupted AES-GCM artifact; pruning refuses destructive action when no verified backup exists; CI ran the full end-to-end script successfully on PostgreSQL 15 and 17 at the exact revision. Public license is MIT.
CLAIMS NOT VERIFIED: I did not independently rerun the repository locally. The inspected E2E uses local throwaway PostgreSQL rather than a live Supabase/Neon managed restore target, so provider-specific Auth/Storage/RLS recovery behavior is not proven by these tests. The repo documents RLS-specific handling, but full hosted-platform recovery semantics were not independently validated here.
STRONGEST OBJECTION: The verifier strongly proves logical PostgreSQL backup recoverability, freshness and artifact integrity, but it does not prove a complete hosted application recovery including provider-managed services such as Supabase Auth/Storage/RLS behavior; buyers could overgeneralize the proof if the product is presented as full-platform disaster recovery.
COMMERCIAL WEDGE: Fixed-price Hosted-Postgres Recovery Proof audit for Supabase/Neon/Postgres teams: install least-privilege off-provider backup, run scheduled scratch restores, inject negative controls, and deliver evidence of RPO/freshness plus verified recovery state. Money path is reduced disaster-recovery risk and compliance/audit labor rather than generic backup storage.
SEARCH EFFORT: 8 materially distinct search queries; 1 deep candidate inspection with source/tests/CI and comparison against several adjacent restore-drill repositories.
FALSE-PROMOTION RISK: LOW-MEDIUM — implementation and CI evidence are unusually strong, but the hosted-provider scope must be stated narrowly because scratch-Postgres success does not equal full Supabase/Neon application recovery.
LESSON: N/A
COMPLETED_AT: 2026-09-20T01:33:25-04:00
