import base64
import json
from pathlib import Path

import pytest

from freight.release_attestation import (
    PAYLOAD_TYPE,
    build_statement,
    build_unsigned_dsse,
    verify_unsigned_dsse,
)


ROOT = Path(__file__).resolve().parents[1]


def test_unsigned_dsse_is_deterministic_and_contains_no_fake_signature():
    a = build_unsigned_dsse(ROOT)
    b = build_unsigned_dsse(ROOT)
    assert a == b
    assert a["payloadType"] == PAYLOAD_TYPE
    assert a["signatures"] == []
    verify_unsigned_dsse(ROOT, a)


def test_dsse_payload_contains_provenance_and_sbom_subjects():
    envelope = build_unsigned_dsse(ROOT)
    statement = json.loads(base64.b64decode(envelope["payload"]).decode())
    assert statement["_type"] == "https://in-toto.io/Statement/v1"
    assert len(statement["subject"]) == 2
    assert "Unsigned" in statement["predicate"]["claim_boundary"]


def test_fake_signature_is_rejected_by_repository_verifier():
    envelope = build_unsigned_dsse(ROOT)
    envelope["signatures"] = [{"keyid": "fake", "sig": "fake"}]
    with pytest.raises(ValueError, match="must remain unsigned"):
        verify_unsigned_dsse(ROOT, envelope)
