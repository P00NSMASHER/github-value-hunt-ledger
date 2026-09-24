"""CSV loader for reviewed CloudRecovery discount authorities."""
from __future__ import annotations
import csv, hashlib
from pathlib import Path
from .cloud_discount import CloudDiscountAuthority, DiscountAppliesTo


def load_cloud_discount_authorities_csv(path: str | Path, *, verified: bool=False) -> tuple[CloudDiscountAuthority,...]:
    source=Path(path); raw=source.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    try: text=raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc: raise ValueError(f"{source} must be UTF-8 CSV") from exc
    reader=csv.DictReader(text.splitlines())
    required={"Counterparty","Account_ID","Service_ID","Effective_From","Effective_To","Discount_BPS","Applies_To"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("cloud discount CSV missing required columns")
    result=[]
    for row_number,row in enumerate(reader,start=2):
        try: bps=int((row.get("Discount_BPS") or "").strip())
        except ValueError as exc: raise ValueError(f"row {row_number}: Discount_BPS must be integer") from exc
        try: applies=DiscountAppliesTo((row.get("Applies_To") or "").strip().upper())
        except ValueError as exc: raise ValueError(f"row {row_number}: Applies_To must be VARIABLE or ALL") from exc
        result.append(CloudDiscountAuthority(
            counterparty_id=(row.get("Counterparty") or "").strip(),
            account_id=(row.get("Account_ID") or "").strip() or None,
            service_id=(row.get("Service_ID") or "").strip(),
            effective_from=(row.get("Effective_From") or "").strip(),
            effective_to=(row.get("Effective_To") or "").strip() or None,
            discount_bps=bps, applies_to=applies, source_hash=digest,
            source_locator=f"file://{source.name}#row={row_number}", verified=verified,
            metadata={"source_file":source.name,"row_number":row_number},
        ))
    return tuple(result)
