"""RETALLY M54: one-way local journal checkpoint-mode downgrade fence.

Local M52 review journals have two modes:
  0: legacy LOCAL_ONLY (no independent checkpoint)
  54: CHECKPOINT_REQUIRED for EVERY FUTURE journal write

On the FIRST valid M53 checkpointed review, the caller pins mode 54 via
SQLite PRAGMA user_version within the SAME BEGIN IMMEDIATE transaction as
the request+nonce inserts. A later M52 legacy-only operation against that
specific journal is denied even if it has fresh valid M51 signatures.

This is LOCAL downgrade resistance and improves safety against ordinary
path confusion and mixed-version clients. A privileged actor who can
rewrite the same SQLite file header and all rows (or create new journals)
can still reset mode; only an independently held latest signed M53 anchor
can detect that full rollback. No external signer or legal permission.
"""
from __future__ import annotations

import sqlite3

SCOPE="RETALLY_M54_ONE_WAY_LOCAL_CHECKPOINT_MODE"
LOCAL_ONLY=0
CHECKPOINT_REQUIRED=54
MODES=frozenset((LOCAL_ONLY,CHECKPOINT_REQUIRED))


def mode(conn:sqlite3.Connection)->int:
    """Read the exact persistent header in the caller's SQLite revision."""
    try:
        row=conn.execute("PRAGMA user_version").fetchone()
    except sqlite3.DatabaseError as exc:
        raise ValueError("M54_REPLAY_MODE_HEADER_UNREADABLE") from exc
    if (not isinstance(row,tuple) or len(row)!=1
        or type(row[0]) is not int or row[0] not in MODES):
        raise ValueError("M54_REPLAY_UNKNOWN_CHECKPOINT_MODE")
    return row[0]


def require_safe_mode(conn:sqlite3.Connection,*,has_signed_checkpoint:bool)->int:
    """Check BEFORE inserts while holding the same BEGIN IMMEDIATE lock."""
    current=mode(conn)
    if current==CHECKPOINT_REQUIRED and has_signed_checkpoint is not True:
        raise ValueError("M54_REPLAY_CHECKPOINT_REQUIRED_LOCAL_DOWNGRADE")
    return current


def advance_mode(conn:sqlite3.Connection,*,verified_checkpoint:bool)->int:
    """One-way transition, caller owns write transaction and verified proof.

    The PRAGMA change is journaled by SQLite and rolls back with staged
    review/nonces if any subsequent transaction check fails.
    """
    if verified_checkpoint is not True:
        raise ValueError("M54_REPLAY_UNVERIFIED_SECURITY_MODE_ELEVATION")
    before=mode(conn)
    if before==LOCAL_ONLY:
        conn.execute(f"PRAGMA user_version={CHECKPOINT_REQUIRED}")
    after=mode(conn)
    if after!=CHECKPOINT_REQUIRED:
        raise ValueError("M54_REPLAY_MODE_ELEVATION_NOT_PERSISTED")
    return after
