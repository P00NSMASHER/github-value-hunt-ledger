"""External ingestion integrations for RecoveryOS."""

from .cletrics import (
    CLETRICS_BUNDLE_SCHEMA,
    CLETRICS_BUNDLE_TYPE,
    CletricsBundleEntry,
    CletricsCloudBundle,
    load_cletrics_bundle,
    ANOMALY_ROLE,
    RECONCILIATION_ROLE,
    SAVINGS_ROLE,
)

__all__ = [
    "CLETRICS_BUNDLE_SCHEMA",
    "CLETRICS_BUNDLE_TYPE",
    "CletricsBundleEntry",
    "CletricsCloudBundle",
    "load_cletrics_bundle",
    "ANOMALY_ROLE",
    "RECONCILIATION_ROLE",
    "SAVINGS_ROLE",
]

from .cletrics_exporter import (
    CletricsExportReceipt,
    CletricsSourceArtifact,
    FocusExportMapping,
    export_cletrics_focus_snapshot,
)

__all__ += [
    "CletricsExportReceipt",
    "CletricsSourceArtifact",
    "FocusExportMapping",
    "export_cletrics_focus_snapshot",
]

from .cletrics_supersession import (
    CloudSupersessionCandidate,
    build_cloud_supersession_candidate,
)

__all__ += [
    "CloudSupersessionCandidate",
    "build_cloud_supersession_candidate",
]
