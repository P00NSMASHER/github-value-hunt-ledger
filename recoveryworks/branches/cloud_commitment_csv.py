"""CSV loaders for reviewed cloud commitment authority and allocations."""
from __future__ import annotations
import csv, hashlib
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from .cloud_commitment import CloudCommitmentAuthority, CommitmentAllocation


def _rate_to_micros(value: str, *, row_number: int) -> int:
    try: amount=Decimal(value)
    except InvalidOperation as exc: raise ValueError(f"row {row_number}: Committed_Unit_Rate must be numeric") from exc
    if amount<0: raise ValueError(f"row {row_number}: Committed_Unit_Rate must be non-negative")
    return int((amount*1_000_000).quantize(Decimal("1"),rounding=ROUND_HALF_UP))


def load_cloud_commitment_authorities_csv(path: str | Path, *, verified: bool=False) -> tuple[CloudCommitmentAuthority,...]:
    source=Path(path); raw=source.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    try: text=raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc: raise ValueError(f"{source} must be UTF-8 CSV") from exc
    reader=csv.DictReader(text.splitlines())
    required={"Counterparty","Account_ID","Service_ID","Effective_From","Effective_To","Commitment_Type","Committed_Unit_Rate"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("cloud commitment CSV missing required columns")
    result=[]
    for row_number,row in enumerate(reader,start=2):
        result.append(CloudCommitmentAuthority(
            counterparty_id=(row.get("Counterparty") or "").strip(),
            account_id=(row.get("Account_ID") or "").strip() or None,
            service_id=(row.get("Service_ID") or "").strip(),
            effective_from=(row.get("Effective_From") or "").strip(),
            effective_to=(row.get("Effective_To") or "").strip() or None,
            commitment_type=(row.get("Commitment_Type") or "").strip(),
            committed_unit_rate_micros=_rate_to_micros((row.get("Committed_Unit_Rate") or "").strip(),row_number=row_number),
            source_hash=digest, source_locator=f"file://{source.name}#row={row_number}", verified=verified,
            metadata={"source_file":source.name,"row_number":row_number},
        ))
    return tuple(result)


def load_cloud_commitment_allocations_csv(path: str | Path, *, verified: bool=False) -> tuple[CommitmentAllocation,...]:
    source=Path(path); raw=source.read_bytes(); digest=hashlib.sha256(raw).hexdigest()
    try: text=raw.decode("utf-8-sig")
    except UnicodeDecodeError as exc: raise ValueError(f"{source} must be UTF-8 CSV") from exc
    reader=csv.DictReader(text.splitlines())
    required={"Charge_ID","Allocation_ID","Entitled_Units"}
    if not reader.fieldnames or not required.issubset(reader.fieldnames):
        raise ValueError("cloud commitment allocation CSV missing required columns")
    result=[]; seen=set()
    for row_number,row in enumerate(reader,start=2):
        charge_id=(row.get("Charge_ID") or "").strip(); allocation_id=(row.get("Allocation_ID") or "").strip()
        if not charge_id or not allocation_id: raise ValueError(f"row {row_number}: Charge_ID and Allocation_ID are required")
        key=(charge_id,allocation_id)
        if key in seen: raise ValueError(f"row {row_number}: duplicate commitment allocation identity")
        seen.add(key)
        result.append(CommitmentAllocation(
            charge_id=charge_id, entitled_units=(row.get("Entitled_Units") or "").strip(),
            source_hash=digest, source_locator=f"file://{source.name}#row={row_number}", verified=verified,
            metadata={"source_file":source.name,"row_number":row_number,"allocation_id":allocation_id},
        ))
    return tuple(result)
