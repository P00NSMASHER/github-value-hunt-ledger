"""Read-only, source-scoped healthcare purchasing audit entry point."""
from .aggregation import combine_results
from .ap_credit import audit_ap_credit
from .models import AuditResult, CanonicalBatch, RuleSetVersion
from .procurement import audit_procurement


def run_audit(batch: CanonicalBatch, rules: RuleSetVersion) -> AuditResult:
    """Calculate review candidates only: no claims, ERP writes, or recovered cash."""
    procurement = audit_procurement(batch, rules)
    ap_credit = audit_ap_credit(batch, rules)
    return combine_results((procurement, ap_credit), batch)
