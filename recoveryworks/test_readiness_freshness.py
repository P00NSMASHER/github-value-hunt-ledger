import hashlib
import unittest

from recoveryworks import (
    build_seven_figure_readiness,
    record_external_signature_verification,
    record_external_timestamp_verification,
    record_object_lock_verification,
)
from recoveryworks.test_custody_provenance import build_custody_chain


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def signature_for(public_record, *, verified_at: str):
    return record_external_signature_verification(
        signature_id="SIM-FRESHNESS-SIGNATURE",
        payload_kind="recoveryworks_public_verification_record_v1",
        payload_hash=public_record.record_hash,
        provider="SIM-KMS",
        key_id="sim-kms-asymmetric-key-freshness",
        algorithm="RSA_PSS_SHA256",
        public_key_fingerprint=sha(b"SIMULATED FRESHNESS PUBLIC KEY"),
        signature_hash=sha(b"SIMULATED FRESHNESS SIGNATURE"),
        provider_request_id="SIM-KMS-FRESHNESS-VERIFY",
        verification_receipt_hash=sha(b"SIMULATED FRESHNESS KMS RESPONSE"),
        signed_at="2026-09-22T16:46:00Z",
        verified_at=verified_at,
        verified_by_adapter="sim-kms-freshness-adapter",
        provider_verified=True,
    )


def timestamp_for(signature, *, verified_at: str):
    return record_external_timestamp_verification(
        timestamp_id="SIM-FRESHNESS-RFC3161",
        subject_hash=signature.signature_hash,
        authority="SIM-TRUSTED-TIMESTAMP-AUTHORITY",
        standard="RFC3161",
        token_hash=sha(b"SIMULATED FRESHNESS RFC3161 TOKEN"),
        serial_number="SIM-FRESHNESS-TSA-SERIAL",
        provider_request_id="SIM-TSA-FRESHNESS-VERIFY",
        verification_receipt_hash=sha(b"SIMULATED FRESHNESS TSA RESPONSE"),
        timestamped_at="2026-09-22T16:47:30Z",
        verified_at=verified_at,
        verified_by_adapter="sim-rfc3161-freshness-adapter",
        provider_verified=True,
    )


def object_lock_receipts(retention, *, checked_at: str):
    return tuple(
        record_object_lock_verification(
            source_id=item.source_id,
            role=item.role,
            source_hash=item.source_hash,
            provider="SIM-OBJECT-STORE",
            object_version_id=f"SIM-FRESHNESS-VERSION-{index}",
            retention_control_id=item.retention_control_id,
            retention_mode=item.retention_mode,
            retain_until=item.retain_until,
            legal_hold_status="OFF",
            checked_at=checked_at,
            provider_request_id=f"SIM-FRESHNESS-LOCK-{index}",
            provider_response_hash=item.provider_attestation_hash,
            verified_by_adapter="sim-object-lock-freshness-adapter",
            provider_verified=True,
        )
        for index, item in enumerate(retention.entries, start=1)
    )


def build_with_times(*, signature_verified_at: str, timestamp_verified_at: str, lock_checked_at: str):
    bundle, ledger, packet, retention, completeness, build, public = build_custody_chain()
    signature = signature_for(public, verified_at=signature_verified_at)
    timestamp = timestamp_for(signature, verified_at=timestamp_verified_at)
    receipts = object_lock_receipts(retention, checked_at=lock_checked_at)
    return (
        bundle,
        ledger,
        packet,
        retention,
        completeness,
        build,
        public,
        signature,
        timestamp,
        receipts,
    )


class SevenFigureReadinessFreshnessTests(unittest.TestCase):
    def _assert_stale_rejected(
        self,
        *,
        signature_verified_at: str,
        timestamp_verified_at: str,
        lock_checked_at: str,
    ):
        (
            bundle,
            ledger,
            packet,
            retention,
            completeness,
            build,
            public,
            signature,
            timestamp,
            receipts,
        ) = build_with_times(
            signature_verified_at=signature_verified_at,
            timestamp_verified_at=timestamp_verified_at,
            lock_checked_at=lock_checked_at,
        )
        with self.assertRaises(ValueError):
            build_seven_figure_readiness(
                bundle,
                packet,
                retention,
                completeness,
                build,
                public,
                signature,
                timestamp,
                receipts,
                journal_head_hash=ledger.journal.head_hash,
                evaluated_at="2026-09-23T17:00:00Z",
                evaluated_by="sim-freshness-controller",
            )

    def test_stale_kms_verification_is_rejected(self):
        self._assert_stale_rejected(
            signature_verified_at="2026-09-22T16:47:00Z",
            timestamp_verified_at="2026-09-23T16:59:00Z",
            lock_checked_at="2026-09-23T16:59:00Z",
        )

    def test_stale_tsa_verification_is_rejected(self):
        self._assert_stale_rejected(
            signature_verified_at="2026-09-23T16:58:00Z",
            timestamp_verified_at="2026-09-22T16:48:00Z",
            lock_checked_at="2026-09-23T16:59:00Z",
        )

    def test_stale_object_lock_verification_is_rejected(self):
        self._assert_stale_rejected(
            signature_verified_at="2026-09-23T16:58:00Z",
            timestamp_verified_at="2026-09-23T16:59:00Z",
            lock_checked_at="2026-09-22T16:46:00Z",
        )


if __name__ == "__main__":
    unittest.main()
