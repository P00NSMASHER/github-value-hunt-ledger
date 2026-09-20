"""Unsigned in-toto/DSSE-shaped release attestation payload.

The envelope is intentionally unsigned. It creates a deterministic payload that
can later be signed by an approved external signing identity/key.
"""
from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

from freight.release_provenance import build_release_provenance, _canonical_hash
from freight.sbom import build_cyclonedx_sbom


PREDICATE_TYPE = "https://freight-recovery.local/attestation/v1"
PAYLOAD_TYPE = "application/vnd.in-toto+json"


def build_statement(root: Path) -> dict:
    provenance = build_release_provenance(root)
    sbom = build_cyclonedx_sbom(root)
    sbom_hash = _canonical_hash(sbom)
    return {
        "_type": "https://in-toto.io/Statement/v1",
        "subject": [
            {
                "name": "Freight Recovery control provenance",
                "digest": {"sha256": provenance["provenance_hash"]},
            },
            {
                "name": "Freight Recovery CycloneDX SBOM",
                "digest": {"sha256": sbom_hash},
            },
        ],
        "predicateType": PREDICATE_TYPE,
        "predicate": {
            "provenance": provenance,
            "sbom_sha256": sbom_hash,
            "claim_boundary": "Unsigned deterministic application-level attestation payload; no external signer/timestamp/certification is claimed.",
        },
    }


def build_unsigned_dsse(root: Path) -> dict:
    statement = build_statement(root)
    payload = json.dumps(
        statement,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
    ).encode()
    return {
        "payloadType": PAYLOAD_TYPE,
        "payload": base64.b64encode(payload).decode("ascii"),
        "signatures": [],
    }


def verify_unsigned_dsse(root: Path, envelope: dict) -> None:
    if envelope.get("payloadType") != PAYLOAD_TYPE:
        raise ValueError("unexpected DSSE payload type")
    if envelope.get("signatures") != []:
        raise ValueError("repository-generated envelope must remain unsigned")
    raw = base64.b64decode(envelope.get("payload", ""), validate=True)
    actual = json.loads(raw.decode("utf-8"))
    expected = build_statement(root)
    if actual != expected:
        raise ValueError("attestation payload does not match current checkout")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--verify")
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    if args.verify:
        envelope = json.loads(Path(args.verify).read_text(encoding="utf-8"))
        verify_unsigned_dsse(root, envelope)
        print("OK unsigned DSSE payload verified")
        return
    print(json.dumps(build_unsigned_dsse(root), indent=2, sort_keys=True))


if __name__ == "__main__":
    main()
