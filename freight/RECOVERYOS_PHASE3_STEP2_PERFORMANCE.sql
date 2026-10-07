-- RecoveryOS Phase 3 Step 2 performance hardening.
-- Applied to the deployed Floot/Neon data plane on 2026-10-07.
--
-- These indexes target measured query shapes. They do not imply a production
-- latency SLA and do not alter the evidence/financial semantics.

-- Every governed INSERT resolves the tenant's current audit-chain head.
CREATE INDEX IF NOT EXISTS recovery_audit_chain_head_idx
  ON recovery_audit_events(tenant_id, occurred_at DESC, id DESC);

-- Priority review queue: tenant filter + largest variance first.
CREATE INDEX IF NOT EXISTS recovery_findings_review_queue_idx
  ON recovery_challenge_findings(tenant_id, variance_cents DESC, id);

-- Latest human disposition per finding.
CREATE INDEX IF NOT EXISTS recovery_review_latest_idx
  ON recovery_review_dispositions(
    tenant_id, finding_id, created_at DESC, id DESC
  );

-- Latest provider state per payment instruction.
CREATE INDEX IF NOT EXISTS recovery_payment_event_latest_idx
  ON recovery_payment_events(
    tenant_id, instruction_id, occurred_at DESC, created_at DESC, id DESC
  );

-- Human payment queue returns the most recent 250 instructions.
CREATE INDEX IF NOT EXISTS recovery_payment_instruction_recent_idx
  ON recovery_payment_instructions(tenant_id, created_at DESC, id DESC);
