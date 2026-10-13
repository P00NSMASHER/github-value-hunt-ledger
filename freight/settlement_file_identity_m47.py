"""RETALLY M47: noncreating, identity-bound SQLite file paths.

Protect current SettlementStore sessions against accidental deletion, atomic
replacement, and symlink/file-type substitution of the database they opened.

This is a local file-continuity check (device + inode), NOT a MAC/signature,
identity proof of external funds, hostile-kernel defense, or a guarantee
against in-place edits. Existing M44-M46 semantics remain mandatory.
"""
from __future__ import annotations

import os
from pathlib import Path
import stat

SCOPE = "RETALLY_M47_SQLITE_FILE_PATH_CONTINUITY_CURRENT_SESSION_ONLY"


def _fail(code: str) -> None:
    # Keep paths, tenant names, invoice IDs and file content out of errors.
    raise RuntimeError("M47_SQLITE_" + code)


def identity(path: str | Path) -> tuple[int, int]:
    """Observe only a real direct file path (never a symlink or missing file)."""
    try:
        entry = os.lstat(path)
    except FileNotFoundError:
        _fail("SOURCE_FILE_MISSING")
    except OSError:
        _fail("SOURCE_FILE_UNREADABLE")
    if stat.S_ISLNK(entry.st_mode):
        _fail("SOURCE_SYMLINK_REJECTED")
    if not stat.S_ISREG(entry.st_mode):
        _fail("SOURCE_NOT_REGULAR_FILE")
    if type(entry.st_dev) is not int or type(entry.st_ino) is not int:
        _fail("SOURCE_IDENTITY_NOT_AVAILABLE")
    return (entry.st_dev, entry.st_ino)


def assert_identity(path: str | Path, pinned: tuple[int, int]) -> tuple[int, int]:
    current = identity(path)
    if current != pinned:
        _fail("SOURCE_FILE_REPLACED")
    return current


def create_exclusive_empty(path: str | Path) -> None:
    """First creation ONLY; existing file, orphan WAL or symlinks fail closed."""
    path = Path(path)
    # A missing main file with existing WAL/SHM can be a deleted database,
    # not a genuinely new safe workspace. Never replace it by accident.
    for suffix in ("-wal", "-shm", "-journal"):
        if os.path.lexists(str(path) + suffix):
            _fail("ORPHANED_SQLITE_SIDECAR")
    flags = os.O_CREAT | os.O_EXCL | os.O_RDWR
    flags |= getattr(os, "O_NOFOLLOW", 0)
    try:
        fd = os.open(path, flags, 0o600)
    except FileExistsError:
        _fail("CREATE_PATH_ALREADY_PRESENT")
    except OSError:
        _fail("SOURCE_CREATE_FAILED")
    else:
        os.close(fd)
