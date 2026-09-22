"""RecoveryWorks / RecoveryOS shared recovery intelligence layer."""
from .authorization import (
    AuthorizationEvaluation,
    AuthorizationRevocation,
    AuthorizationState,
    RecoveryActionAuthorization,
    RecoveryActionType,
    assert_action_allowed,
    evaluate_authorization,
    issue_authorization,
    revoke_authorization,
)
from .engine import RecoveryEngine, RecoveryObservation
from .ledger import RecoveryLedger
from .sqlite_ledger import SQLiteRecoveryLedger
from .scan import RecoveryScanBatch, RecoveryScanManifest, SourceManifestEntry, freeze_scan, run_scan
from .models import (
    Branch,
    CaseState,
    EvidenceRef,
    FindingState,
    RecoveryFinding,
    RecoveryMode,
    RuleRef,
)

__all__ = [
    "AuthorizationEvaluation",
    "AuthorizationRevocation",
    "AuthorizationState",
    "Branch",
    "CaseState",
    "EvidenceRef",
    "FindingState",
    "RecoveryActionAuthorization",
    "RecoveryActionType",
    "RecoveryEngine",
    "RecoveryFinding",
    "RecoveryLedger",
    "SQLiteRecoveryLedger",
    "RecoveryMode",
    "RecoveryObservation",
    "RecoveryScanBatch",
    "RecoveryScanManifest",
    "RuleRef",
    "SourceManifestEntry",
    "assert_action_allowed",
    "evaluate_authorization",
    "freeze_scan",
    "issue_authorization",
    "revoke_authorization",
    "run_scan",
]
