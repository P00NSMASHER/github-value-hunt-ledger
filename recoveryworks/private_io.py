"""Cross-platform, fail-closed writes for sensitive local artifacts."""
from __future__ import annotations

from contextlib import contextmanager
from functools import lru_cache
import os
from pathlib import Path
import re
import stat
import subprocess
import tempfile
import time
from typing import Iterator


_SID_RE = re.compile(r"S-\d-\d+(?:-\d+)+")
_SYSTEM_SID = "S-1-5-18"


@lru_cache(maxsize=1)
def _windows_user_sid() -> str:
    result = subprocess.run(
        ["whoami.exe", "/user", "/fo", "csv", "/nh"],
        check=False,
        capture_output=True,
        text=True,
        timeout=5,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )
    match = _SID_RE.search(result.stdout)
    if result.returncode != 0 or match is None:
        raise PermissionError("unable to resolve the current Windows user SID")
    return match.group(0)


_WINDOWS_ACL_SET = r"""
$ErrorActionPreference = 'Stop'
$file = $env:RETALLY_PRIVATE_FILE
$user = New-Object System.Security.Principal.SecurityIdentifier($env:RETALLY_PRIVATE_USER_SID)
$system = New-Object System.Security.Principal.SecurityIdentifier('S-1-5-18')
$acl = Get-Acl -LiteralPath $file
$acl.SetAccessRuleProtection($true, $false)
foreach ($entry in @($acl.Access)) {
    [void]$acl.RemoveAccessRuleSpecific($entry)
}
$allow = [System.Security.AccessControl.AccessControlType]::Allow
$full = [System.Security.AccessControl.FileSystemRights]::FullControl
$acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($user, $full, $allow)))
$acl.AddAccessRule((New-Object System.Security.AccessControl.FileSystemAccessRule($system, $full, $allow)))
Set-Acl -LiteralPath $file -AclObject $acl
"""

_WINDOWS_ACL_VERIFY = r"""
$ErrorActionPreference = 'Stop'
$file = $env:RETALLY_PRIVATE_FILE
$acl = Get-Acl -LiteralPath $file
if (-not $acl.AreAccessRulesProtected) { exit 2 }
$entries = @($acl.Access)
if ($entries.Count -ne 2) { exit 3 }
$expected = @{
    $env:RETALLY_PRIVATE_USER_SID = $true
    'S-1-5-18' = $true
}
foreach ($entry in $entries) {
    $sid = $entry.IdentityReference.Translate([System.Security.Principal.SecurityIdentifier]).Value
    if (-not $expected.ContainsKey($sid) -or $entry.IsInherited -or
        $entry.AccessControlType -ne [System.Security.AccessControl.AccessControlType]::Allow -or
        $entry.FileSystemRights -ne [System.Security.AccessControl.FileSystemRights]::FullControl) {
        exit 4
    }
    $expected.Remove($sid)
}
if ($expected.Count -ne 0) { exit 5 }
"""


def _windows_acl_process(path: Path, script: str):
    """Use Windows access-control APIs; paths never enter executable script text."""
    env = os.environ.copy()
    env["RETALLY_PRIVATE_FILE"] = str(path)
    env["RETALLY_PRIVATE_USER_SID"] = _windows_user_sid()
    return subprocess.run(
        ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", script],
        check=False,
        capture_output=True,
        text=True,
        timeout=20,
        env=env,
        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
    )


def _restrict_private_permissions(path: Path) -> None:
    """Permit only the current Windows user and SYSTEM, removing other explicit ACEs."""
    if os.name != "nt":
        os.chmod(path, 0o600)
        if os.stat(path).st_mode & 0o777 != 0o600:
            raise PermissionError(f"private mode was not applied to {path}")
        return

    try:
        result = _windows_acl_process(path, _WINDOWS_ACL_SET)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise PermissionError(f"unable to apply private Windows ACL to {path}") from exc
    if result.returncode != 0:
        raise PermissionError(
            f"unable to apply private Windows ACL to {path}: "
            + (result.stderr or result.stdout).strip()[:300]
        )
    if not private_permissions_verified(path):
        raise PermissionError(f"private Windows ACL verification failed for {path}")


def private_permissions_verified(path: Path) -> bool:
    """Independently verify exact protected trustee SIDs, rights, and inheritance."""
    if os.name != "nt":
        return path.is_file() and os.stat(path).st_mode & 0o777 == 0o600
    if not path.is_file():
        return False
    try:
        return _windows_acl_process(path, _WINDOWS_ACL_VERIFY).returncode == 0
    except (OSError, subprocess.TimeoutExpired, PermissionError):
        return False


def atomic_private_write(path: Path, raw: bytes) -> None:
    """Write bytes atomically without ever leaving an inherited-access temp file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_name = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=str(path.parent),
    )
    tmp_path = Path(tmp_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(fd, 0o600)
        else:
            _restrict_private_permissions(tmp_path)

        handle = os.fdopen(fd, "wb")
        fd = -1
        with handle:
            handle.write(raw)
            handle.flush()
            os.fsync(handle.fileno())

        _restrict_private_permissions(tmp_path)
        os.replace(tmp_path, path)
        _restrict_private_permissions(path)
        if not private_permissions_verified(path):
            raise PermissionError(f"private permissions could not be verified for {path}")
    finally:
        if fd >= 0:
            os.close(fd)
        if tmp_path.exists():
            tmp_path.unlink()


@contextmanager
def private_file_lock(path: Path, *, timeout_seconds: float = 10.0) -> Iterator[None]:
    """Hold a cross-process exclusive lock in a private sidecar file."""
    if timeout_seconds <= 0:
        raise ValueError("timeout_seconds must be positive")
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.is_symlink():
        raise PermissionError(f"private lock path cannot be a symbolic link: {path}")
    flags = os.O_RDWR | os.O_CREAT
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(path, flags, 0o600)
    handle = None
    acquired = False
    try:
        handle = os.fdopen(fd, "r+b", buffering=0)
        fd = -1
        if not stat.S_ISREG(os.fstat(handle.fileno()).st_mode):
            raise PermissionError(f"private lock path must be a regular file: {path}")
        if os.fstat(handle.fileno()).st_size == 0:
            handle.write(b"\0")
            handle.flush()
            os.fsync(handle.fileno())
        _restrict_private_permissions(path)
        if not private_permissions_verified(path):
            raise PermissionError(f"private lock permissions could not be verified for {path}")

        deadline = time.monotonic() + timeout_seconds
        while True:
            try:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                acquired = True
                break
            except OSError as exc:
                if time.monotonic() >= deadline:
                    raise TimeoutError(f"timed out acquiring private file lock: {path}") from exc
                time.sleep(0.05)
        yield
    finally:
        try:
            if acquired and handle is not None:
                handle.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        finally:
            if handle is not None:
                handle.close()
            elif fd >= 0:
                os.close(fd)
