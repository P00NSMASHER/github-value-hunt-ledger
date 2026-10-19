"""Bounded, noninteractive original-document retrieval for RETALLY research.

Only exact pinned, publicly viewable HTTPS documents. No login, messaging,
FOIA submission, purchasing, carrier contact, or customer-data collection.
Source bytes remain in RAM or in a user-selected PRIVATE local folder. On CI
all source bytes are discarded after inspection, without artifact upload.

An authorized download is NOT, by itself, proof of controlling carrier rates,
bank-cleared settlement, an adjudicated invoice error, or RETALLY recovery.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlsplit, unquote
from urllib.request import Request, build_opener, HTTPRedirectHandler

MAX_PDF_BYTES = 30 * 1024 * 1024
ALLOWED_HOSTS = frozenset((
    "ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net",
    "document.epiq11.com",
    "www.cbca.gov",
))
SOURCE_REGISTRY = {
    "globaltranz-original-broker-bills": {
        "url": "https://ec-p-cus-ewf-ecb-sync-fnc.azurewebsites.net/api/GetImage/10247",
        "role": "ORIGINAL_BROKER_ISSUED_INVOICES_WITH_CLAIM_10002",
        "private_third_party_content": True,
        "required": True,
    },
    "court-globaltranz-final-order-623": {
        "url": "https://document.epiq11.com/document/getdocumentsbydocket/?docketId=1227468&projectCode=MCX&docketNumber=623&source=DM",
        "role": "NONCASH_LIABILITY_TRANSFER_COURT_ORDER",
        "private_third_party_content": True,
        "required": False,
    },
    "court-globaltranz-objection-593": {
        "url": "https://document.epiq11.com/document/getdocumentsbydocket/?docketId=1216147&projectCode=MCX&docketNumber=593&source=DM",
        "role": "CLAIM_LIABILITY_TRANSFER_OBJECTION",
        "private_third_party_content": True,
        "required": False,
    },
    "cbca-aare-6578-adjudication": {
        "url": "https://www.cbca.gov/files/decisions/2020/SULLIVAN_08-06-20_6578-RATE__AARE_LOGISTICS%2C_LLC%20%28Decision%29.pdf",
        "role": "FINAL_APPEAL_OVERTURNED_FREIGHT_OVERCHARGE",
        "private_third_party_content": False,
        "required": False,
    },
    "cbca-arpin-6729-adjudication": {
        "url": "https://www.cbca.gov/files/decisions/2020/KULLBERG_08-13-20_6729-RATE__ARPIN_GROUP%2C_INC.%20%28Decision%29.pdf",
        "role": "FINAL_APPEAL_REJECTED_CARRIER_CHALLENGE",
        "private_third_party_content": False,
        "required": False,
    },
}


class AcquisitionHold(ValueError):
    pass


def normalize_https_url(url: str) -> tuple[str, str, str]:
    if not isinstance(url, str) or len(url) > 1200 or "\\" in url:
        raise AcquisitionHold("UNSAFE_SOURCE_URL")
    try:
        p = urlsplit(url)
        port = p.port
    except ValueError as exc:
        raise AcquisitionHold("UNSAFE_SOURCE_URL") from exc
    if (p.scheme != "https" or p.hostname not in ALLOWED_HOSTS
            or p.username is not None or p.password is not None
            or port not in (None, 443) or p.fragment
            or any(ord(c) < 32 for c in url)):
        raise AcquisitionHold("UNSAFE_SOURCE_URL")
    if ".." in unquote(p.path).split("/"):
        raise AcquisitionHold("UNSAFE_SOURCE_URL")
    return p.hostname, unquote(p.path), p.query


class _SameDocumentRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if normalize_https_url(req.full_url) != normalize_https_url(newurl):
            raise AcquisitionHold("CROSS_SOURCE_REDIRECT_BLOCKED")
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def validate_pdf(payload: bytes) -> None:
    if not isinstance(payload, bytes) or not 100 < len(payload) <= MAX_PDF_BYTES:
        raise AcquisitionHold("EMPTY_OR_OVERSIZED_PDF")
    if not payload.startswith(b"%PDF-"):
        raise AcquisitionHold("NOT_AN_ORIGINAL_PDF")
    if b"%%EOF" not in payload[-8192:]:
        raise AcquisitionHold("TRUNCATED_PDF_END")


def fetch_pinned_pdf(key: str, *, retrieve=None) -> bytes:
    if key not in SOURCE_REGISTRY:
        raise AcquisitionHold("UNREGISTERED_SOURCE")
    url = SOURCE_REGISTRY[key]["url"]
    normalize_https_url(url)
    if retrieve is None:
        opener = build_opener(_SameDocumentRedirect())
        def retrieve(url):
            return opener.open(Request(url, headers={
                "User-Agent": "RETALLY-OriginalRecordsReview/1.0 (authorized read-only)",
                "Accept": "application/pdf,application/octet-stream",
            }), timeout=25)
    try:
        with retrieve(url) as r:
            if r.status != 200 or normalize_https_url(r.geturl()) != normalize_https_url(url):
                raise AcquisitionHold("UNEXPECTED_HTTP_OR_FINAL_URL")
            payload = r.read(MAX_PDF_BYTES + 1)
    except AcquisitionHold:
        raise
    except Exception as exc:
        # Avoid serializing remote error bodies, credentials, or legal identities.
        raise AcquisitionHold("ORIGINAL_SOURCE_UNAVAILABLE") from exc
    validate_pdf(payload)
    return payload


def private_destination(dest: str) -> Path:
    if not isinstance(dest, str) or not dest.strip():
        raise AcquisitionHold("PRIVATE_DIRECTORY_REQUIRED")
    target = Path(dest).expanduser().resolve()
    repo_root = Path(__file__).resolve().parents[2]
    # Even private carrier invoice PDFs must never be written inside Git checkout.
    if target == repo_root or repo_root in target.parents:
        raise AcquisitionHold("NO_ORIGINAL_DOCUMENT_BYTES_IN_GIT")
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    if target.is_symlink() or not target.is_dir():
        raise AcquisitionHold("UNSAFE_OUTPUT_DIRECTORY")
    try:
        os.chmod(target, 0o700)
    except OSError:
        pass
    return target



def case_text_signals(source_id: str, pages: list[str]) -> dict:
    """Verify key terms share ONE page, not merely the same PDF or search snippet.

    This is source-text corroboration only, not admissibility or final recovery.
    Never return raw extracted PDF content or third-party invoice references.
    """
    normalized = [" ".join(p.split()).casefold() for p in pages]
    if source_id in ("court-globaltranz-final-order-623", "court-globaltranz-objection-593"):
        wanted = ("globaltranz", "10002", "25,954.47", "1,496.52", "24,457.95", "artivo")
        matches = [i + 1 for i, page in enumerate(normalized) if all(t in page for t in wanted)]
        return {
            "court_claim_liability_transfer_page_coincident": bool(matches),
            "matching_source_pages": matches[:3],
            "reported_transfer_is_recovery": False,
        }
    if source_id == "globaltranz-original-broker-bills":
        has_invoice_page = any(
            "globaltranz" in page and "invoice" in page and "carrier:" in page
            for page in normalized
        )
        return {
            "original_broker_invoice_page_identified": has_invoice_page,
            "original_underlying_carrier_invoice_verified": False,
        }
    if source_id == "cbca-aare-6578-adjudication":
        return {"independent_board_granted_aare_claim": any(
            "aare" in page and "claim is granted" in page for page in normalized
        ), "refund_bank_clearing_verified": False}
    if source_id == "cbca-arpin-6729-adjudication":
        return {"independent_board_denied_arpin_claim": any(
            "claim is denied" in page for page in normalized
        ), "offset_bank_clearing_verified": False}
    return {}


def inspect_pdf_text(source_id: str, payload: bytes) -> dict:
    """Use existing local poppler if installed; never log raw legal/finance text."""
    if not shutil.which("pdftotext"):
        return {"source_text_status": "TEXT_EXTRACTOR_MISSING"}
    try:
        proc = subprocess.run(
            ["pdftotext", "-layout", "-enc", "UTF-8", "-", "-"],
            input=payload, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            timeout=25, check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return {"source_text_status": "TEXT_EXTRACTION_UNAVAILABLE"}
    if proc.returncode != 0 or not proc.stdout or len(proc.stdout) > 12_000_000:
        return {"source_text_status": "TEXT_EXTRACTION_UNAVAILABLE"}
    pages = proc.stdout.decode("utf-8", errors="replace").split("\f")
    if pages and not pages[-1].strip():
        pages.pop()
    return {
        "source_text_status": "TEXT_EXTRACTED_NO_SOURCE_TEXT_LOGGED",
        "extracted_page_count": len(pages),
        "source_signals": case_text_signals(source_id, pages),
    }


def inspect_sources(*, retrieve=None, dest: str | None = None) -> dict:
    path = private_destination(dest) if dest else None
    checked: list[dict] = []
    downloaded = 0
    for key, data in SOURCE_REGISTRY.items():
        record = {"source_id": key, "source_url": data["url"],
                  "role": data["role"], "required": data["required"],
                  "contains_third_party_documents": data["private_third_party_content"]}
        try:
            payload = fetch_pinned_pdf(key, retrieve=retrieve)
            record.update(state="DOWNLOADED_ORIGINAL_PDF_BYTES",
                          size_bytes=len(payload),
                          sha256=hashlib.sha256(payload).hexdigest())
            record.update(inspect_pdf_text(key, payload))
            downloaded += 1
            if path:
                out = path / (key + ".pdf")
                flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
                fd = os.open(out, flags, 0o600)
                with os.fdopen(fd, "wb") as f:
                    f.write(payload)
                record["local_private_filename"] = out.name
                record["stored_private_only"] = True
            else:
                record["stored_private_only"] = False
        except AcquisitionHold as exc:
            record.update(state="SOURCE_RETRIEVAL_HOLD", hold_code=str(exc))
        checked.append(record)
    return {
        "scope": "AUTHORIZED_SOURCE_DOWNLOAD_AND_PROVENANCE_ONLY",
        "sources": checked,
        "retrieved_document_count": downloaded,
        "raw_bytes_in_public_repository": False,
        "sources_are_not_customer_validation": True,
        "original_underlying_carrier_invoice_verified": False,
        "bank_clearing_verified": False,
        "final_rate_terms_verified": False,
        "independent_invoice_error_verified": False,
        "executed_recovery_clearing_verified": False,
        "freight_recovery_case_complete": False,
        "verified_retally_recovered_cents": 0,
    }


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--live", action="store_true", help="Explicitly allow public official PDF downloads.")
    p.add_argument("--private-dir", help="Retain originals in private directory outside Git checkout (0600).")
    args = p.parse_args()
    if not args.live:
        raise SystemExit("No public network access without --live.")
    report = inspect_sources(dest=args.private_dir)
    # Only references and hashes; never invoice rows, bank details or PDF bytes.
    print(json.dumps(report, sort_keys=True, indent=2))
    if not any(x["state"] == "DOWNLOADED_ORIGINAL_PDF_BYTES" and x["required"]
               for x in report["sources"]):
        raise SystemExit(2)


if __name__ == "__main__":
    main()
