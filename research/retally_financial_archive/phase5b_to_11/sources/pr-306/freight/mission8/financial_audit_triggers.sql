-- Mission 9 consolidation: extend the EXISTING RecoveryOS tenant audit chain.
-- Requires Phase 3 recovery_append_audit_event() and Mission 8 staging objects.
-- Staging-only release candidate. No production DDL authorization.
DROP TRIGGER IF EXISTS recovery_eligibility_audit_t ON recovery_eligibility_certifications;
CREATE TRIGGER recovery_eligibility_audit_t
  AFTER INSERT ON recovery_eligibility_certifications
  FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();

DROP TRIGGER IF EXISTS recovery_allocation_audit_t ON recovery_value_allocations;
CREATE TRIGGER recovery_allocation_audit_t
  AFTER INSERT ON recovery_value_allocations
  FOR EACH ROW EXECUTE FUNCTION recovery_append_audit_event();
