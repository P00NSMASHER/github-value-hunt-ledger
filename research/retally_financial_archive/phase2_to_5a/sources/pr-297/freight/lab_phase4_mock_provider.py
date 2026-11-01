"""Crash/retry/concurrency proof for mock provider events in isolated SQLite.

NOT the hosted Floot Postgres implementation, bank remittance or custody.
Every submitted event must be externally authenticated before a real adapter uses it.
"""
from __future__ import annotations
from contextlib import closing
from dataclasses import dataclass
from datetime import datetime,timezone
from hashlib import sha256
import json
from pathlib import Path
import re
import sqlite3
import uuid

SHA=re.compile(r"[0-9a-f]{64}\Z")
TRANSITIONS={
    "AUTHORIZED":{"SUBMITTED"},
    "SUBMITTED":{"ACCEPTED","FAILED","OUTCOME_UNKNOWN"},
    "ACCEPTED":{"SETTLED","FAILED","OUTCOME_UNKNOWN"},
    "SETTLED":{"REVERSED"},
    "FAILED":set(),"REVERSED":set(),"OUTCOME_UNKNOWN":set(),
}


def _utc(value: str) -> str:
    if not isinstance(value,str):
        raise ValueError("INVALID_EVENT_TIME")
    try:
        d=datetime.fromisoformat(value.replace("Z","+00:00"))
        if d.tzinfo is None or d.utcoffset() is None:raise ValueError()
    except ValueError as exc:
        raise ValueError("INVALID_EVENT_TIME") from exc
    return d.astimezone(timezone.utc).isoformat(timespec="microseconds").replace("+00:00","Z")


def _str(name:str,value:str)->str:
    if type(value) is not str or not value or any(ord(x)<32 for x in value):
        raise ValueError("INVALID_"+name.upper())
    return value


def _hash(record:dict)->str:
    return sha256(json.dumps(record,sort_keys=True,separators=(",",":")).encode()).hexdigest()


@dataclass(frozen=True)
class MockCallback:
    tenant: str
    instruction: str
    state: str
    provider: str
    provider_reference: str
    amount_cents: int
    source_sha256: str
    actor_id: str
    occurred_at: str


@dataclass(frozen=True)
class CallbackResult:
    event_id: str
    event_hash: str
    state: str
    replay: bool
    scope: str="ISOLATED_MOCK_PROVIDER_ONLY"


class MockProviderLedger:
    def __init__(self,path: str|Path):
        self.path=str(path)
        Path(self.path).parent.mkdir(parents=True,exist_ok=True)
        with closing(self._connect()) as con,con:
            con.execute("PRAGMA journal_mode=WAL")
            con.executescript("""
            CREATE TABLE IF NOT EXISTS callbacks(
                tenant TEXT NOT NULL,instruction TEXT NOT NULL,
                event_id TEXT NOT NULL,sequence INTEGER NOT NULL,
                state TEXT NOT NULL,provider TEXT NOT NULL,
                provider_reference TEXT NOT NULL,amount_cents INTEGER NOT NULL,
                source_sha256 TEXT NOT NULL,actor_id TEXT NOT NULL,
                occurred_at TEXT NOT NULL,previous_hash TEXT,event_hash TEXT NOT NULL,
                PRIMARY KEY(tenant,instruction,event_id),
                UNIQUE(tenant,instruction,provider,provider_reference),
                UNIQUE(tenant,instruction,sequence),
                UNIQUE(tenant,instruction,event_hash)
            );
            CREATE TRIGGER IF NOT EXISTS no_cb_edit BEFORE UPDATE ON callbacks
              BEGIN SELECT RAISE(ABORT,'mock callback immutable'); END;
            CREATE TRIGGER IF NOT EXISTS no_cb_remove BEFORE DELETE ON callbacks
              BEGIN SELECT RAISE(ABORT,'mock callback immutable'); END;
            """)
    def _connect(self):
        con=sqlite3.connect(self.path,timeout=10,isolation_level=None)
        con.row_factory=sqlite3.Row
        con.execute("PRAGMA busy_timeout=10000")
        return con

    def submit(self,event:MockCallback,*,instruction_authorized:bool)->CallbackResult:
        for name in ("tenant","instruction","provider","provider_reference","actor_id"):
            _str(name,getattr(event,name))
        if event.state not in TRANSITIONS:
            raise ValueError("INVALID_PROVIDER_STATE")
        if type(event.amount_cents) is not int or not 0<event.amount_cents<=2**63-1:
            raise ValueError("INVALID_AMOUNT_CENTS")
        if type(event.source_sha256) is not str or not SHA.fullmatch(event.source_sha256):
            raise ValueError("INVALID_SOURCE_DIGEST")
        if type(instruction_authorized) is not bool:
            raise ValueError("INVALID_AUTHORIZATION_FLAG")
        utc=_utc(event.occurred_at)
        with closing(self._connect()) as con:
            try:
                con.execute("BEGIN IMMEDIATE")
                # Lookup before transition is what makes a retry after later state
                # idempotent; the table uniqueness prevents concurrent duplicate effects.
                old=con.execute("""SELECT * FROM callbacks WHERE tenant=? AND instruction=?
                            AND provider=? AND provider_reference=?""",
                            (event.tenant,event.instruction,event.provider,event.provider_reference)).fetchone()
                if old is not None:
                    if (old["state"],old["amount_cents"],old["source_sha256"],
                        old["actor_id"],old["occurred_at"])!=(
                         event.state,event.amount_cents,event.source_sha256,event.actor_id,utc):
                        raise ValueError("CONFLICTING_PROVIDER_REPLAY")
                    result=CallbackResult(old["event_id"],old["event_hash"],old["state"],True)
                    con.commit()
                    return result
                last=con.execute("""SELECT * FROM callbacks WHERE tenant=? AND instruction=?
                          ORDER BY sequence DESC LIMIT 1""",
                          (event.tenant,event.instruction)).fetchone()
                prior=last["state"] if last else "AUTHORIZED"
                if not instruction_authorized:
                    raise ValueError("BUYER_AUTHORIZATION_NOT_VERIFIED")
                if event.state not in TRANSITIONS[prior]:
                    raise ValueError("INVALID_PROVIDER_TRANSITION")
                if last is not None and utc<last["occurred_at"]:
                    raise ValueError("PROVIDER_TIME_REGRESSION")
                sequence=(last["sequence"]+1) if last else 1
                previous=last["event_hash"] if last else None
                data={"tenant":event.tenant,"instruction":event.instruction,
                    "sequence":sequence,"state":event.state,
                    "provider":event.provider,"provider_reference":event.provider_reference,
                    "amount_cents":event.amount_cents,"source_sha256":event.source_sha256,
                    "actor_id":event.actor_id,"occurred_at":utc,"previous_hash":previous}
                event_hash=_hash(data)
                event_id="mock_"+uuid.uuid4().hex
                con.execute("""INSERT INTO callbacks VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""",
                    (event.tenant,event.instruction,event_id,sequence,event.state,
                     event.provider,event.provider_reference,event.amount_cents,
                     event.source_sha256,event.actor_id,utc,previous,event_hash))
                con.commit()
                return CallbackResult(event_id,event_hash,event.state,False)
            except BaseException:
                con.rollback()
                raise

    def verify(self,tenant:str,instruction:str)->tuple[str,...]:
        with closing(self._connect()) as con:
            rows=con.execute("""SELECT * FROM callbacks WHERE tenant=? AND instruction=?
                    ORDER BY sequence""",(tenant,instruction)).fetchall()
        previous=None
        prev_state="AUTHORIZED"
        prev_time=None
        digest_list=[]
        for n,row in enumerate(rows,1):
            body={k:row[k] for k in ("tenant","instruction","sequence","state",
                   "provider","provider_reference","amount_cents","source_sha256",
                   "actor_id","occurred_at","previous_hash")}
            if row["sequence"]!=n or row["previous_hash"]!=previous:
                raise ValueError("MOCK_CHAIN_BROKEN")
            if row["state"] not in TRANSITIONS[prev_state]:
                raise ValueError("MOCK_STATE_CHAIN_BROKEN")
            if prev_time is not None and row["occurred_at"]<prev_time:
                raise ValueError("MOCK_TIME_CHAIN_BROKEN")
            if _hash(body)!=row["event_hash"]:
                raise ValueError("MOCK_EVENT_HASH_BROKEN")
            previous=row["event_hash"]
            prev_state=row["state"]
            prev_time=row["occurred_at"]
            digest_list.append(previous)
        return tuple(digest_list)
