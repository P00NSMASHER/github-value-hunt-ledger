"""Boot a persistent synthetic GopherCRM SQLite service on loopback (Linux/POSIX)."""

import argparse
import ctypes
import errno
from datetime import datetime, timedelta, timezone
import http.client
import json
import os
from pathlib import Path
import pty
import secrets
import select
import signal
import socket
import sqlite3
import subprocess
import sys
import time
from urllib.parse import urlsplit


def write_private(path, data):
    tmp = path.with_suffix(".tmp")
    with os.fdopen(os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600), "w", encoding="utf-8") as stream:
        json.dump(data, stream)
        stream.flush()
        os.fsync(stream.fileno())
    tmp.replace(path)


def create_admin(binary, state, env, password):
    # The upstream interactive command takes its password through the terminal.
    # No password is placed in argv, the global environment, or a log.
    master, slave = pty.openpty()
    proc = subprocess.Popen([binary, "-email", "bootstrap@example.invalid", "-name", "Pilot Bootstrap"],
                            stdin=slave, stdout=slave, stderr=slave, cwd=state, env=env)
    os.close(slave)
    try:
        for expected in (b"Enter admin password:", b"Confirm password:"):
            output = b""
            deadline = time.monotonic() + 30
            while expected not in output:
                if not select.select([master], [], [], max(0, deadline - time.monotonic()))[0]:
                    raise RuntimeError("create-admin prompt timed out")
                output = (output + os.read(master, 8192))[-65536:]
            os.write(master, password.encode() + b"\n")
        if proc.wait(timeout=10):
            raise RuntimeError("create-admin failed")
    finally:
        os.close(master)
        if proc.poll() is None:
            proc.kill()
            proc.wait()


def api(port, path, body=None, token=None, expected=200, method=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=3)
    try:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["Authorization"] = token
        conn.request(method or ("GET" if body is None else "POST"), "/api/v1" + path,
                     None if body is None else json.dumps(body), headers)
        response = conn.getresponse()
        if response.status != expected:
            raise RuntimeError(f"pilot {path} returned {response.status}")
        return json.load(response).get("data")
    finally:
        conn.close()


def rotate_restored_key(root_crm_dir, config):
    """Rotate only the dedicated restored synthetic sales key. Keep replacement bytes private."""
    state = Path(root_crm_dir).resolve(strict=True)
    current, pending = state / "client.json", state / "client.next.json"
    if (state.stat().st_uid != os.getuid() or state.stat().st_mode & 0o077 or pending.exists()
            or current.is_symlink() or json.loads(current.read_text()) != config):
        raise ValueError("unexpected private restore state or pending rotation")
    url = urlsplit(config["base_url"])
    if (url.port is None or config["base_url"] != f"http://127.0.0.1:{url.port}"
            or not config["api_key"].startswith("gcrm_")):
        raise ValueError("unexpected pilot API binding")
    old = "ApiKey " + config["api_key"]
    me = api(url.port, "/users/me", token=old)
    if (me["role"] != "sales" or me["email"] != "sales@example.invalid"
            or me["id"] != config["owner_id"] or me["is_active"] is not True):
        raise ValueError("rotation restricted to active fixture sales owner")
    keys = api(url.port, "/api-keys", token=old)
    prefix = config["api_key"][5:13]
    matches = [k for k in keys if k["prefix"] == prefix and k["user_id"] == me["id"] and k["is_active"]]
    if len(matches) != 1 or matches[0]["name"] != "RETALLY synthetic worker":
        raise ValueError("restore key identity is ambiguous")
    expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
    minted = api(url.port, "/api-keys", {"name": matches[0]["name"], "expires_at": expires}, old, 201)
    rotated = dict(config, api_key=minted["key"])
    replacement = "ApiKey " + rotated["api_key"]
    if replacement == old or api(url.port, "/users/me", token=replacement)["id"] != me["id"]:
        raise ValueError("replacement key verification failed")
    write_private(pending, rotated)
    api(url.port, f"/api-keys/{matches[0]['id']}", token=replacement, method="DELETE")
    api(url.port, "/users/me", token=old, expected=401)
    if api(url.port, "/users/me", token=replacement)["id"] != me["id"]:
        raise ValueError("post-revocation identity verification failed")
    pending.replace(current)
    return rotated


def block_server_egress():
    """Linux libseccomp. Gopher serves accepted TCP sockets via read/write."""
    lib = ctypes.CDLL("libseccomp.so.2")
    lib.seccomp_init.argtypes = [ctypes.c_uint32]
    lib.seccomp_init.restype = ctypes.c_void_p
    lib.seccomp_rule_add.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int, ctypes.c_uint]
    lib.seccomp_load.argtypes = lib.seccomp_release.argtypes = [ctypes.c_void_p]
    context = lib.seccomp_init(0x7fff0000)  # SCMP_ACT_ALLOW
    if not context:
        raise RuntimeError("cannot create egress filter")
    try:
        deny = 0x00050000 | errno.EPERM  # SCMP_ACT_ERRNO
        for name in ("connect", "sendto", "sendmsg", "sendmmsg", "io_uring_setup"):
            number = lib.seccomp_syscall_resolve_name(name.encode())
            if number < 0 or lib.seccomp_rule_add(context, deny, number, 0) != 0:
                raise RuntimeError("cannot restrict " + name)
        if lib.seccomp_load(context) != 0:
            raise RuntimeError("cannot load egress filter")
    finally:
        lib.seccomp_release(context)
    with socket.socket() as check:
        if check.connect_ex(("127.0.0.1", 9)) != errno.EPERM:
            raise RuntimeError("outbound connect policy failed its probe")


def run(args):
    os.umask(0o077)
    state = Path(args.state).resolve()
    state.mkdir(mode=0o700, parents=True, exist_ok=True)
    if state.stat().st_mode & 0o077 or state.stat().st_uid != os.getuid():
        raise RuntimeError("use a private state directory owned by this user")
    # Avoid authenticating against a different process already occupying the port.
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", args.port))
    keys_path = state / "server.json"
    client_path = state / "client.json"
    login_path = state / "login.json"
    db_path = state / "gopher.sqlite"
    fresh = not keys_path.exists()
    if fresh:
        if any(state.iterdir()):
            raise RuntimeError("new pilot requires an empty state directory")
        write_private(keys_path, {"jwt": secrets.token_hex(32), "keys": secrets.token_hex(32)})
    keys = json.loads(keys_path.read_text())
    env = {"PATH": "/usr/bin:/bin", "HOME": str(state), "DB_DRIVER": "sqlite", "DB_PATH": str(db_path),
           "SERVER_HOST": "127.0.0.1", "SERVER_PORT": str(args.port), "SERVER_MODE": "production",
           "JWT_SECRET": keys["jwt"], "API_KEY_SECRET": keys["keys"], "AUTOMATION_ENABLED": "false",
           "AEO_SCHEDULE_ENABLED": "false", "SMTP_HOST": "", "LOG_LEVEL": "warn", "GIN_MODE": "release",
           "CORS_ALLOWED_ORIGINS": "http://127.0.0.1:19824"}
    if fresh:
        bootstrap_pass = secrets.token_urlsafe(30) + "Aa1!"
        create_admin(str(Path(args.admin_binary).resolve()), state, env, bootstrap_pass)
        # Dedicated synthetic database: no pre-existing application data may reside here.
        # In the pin external_id is indexed but not unique and invisible after reassignment.
        # Local uniqueness on reserved import IDs and our task titles also covers soft deletion.
        with sqlite3.connect(db_path) as db:
            db.execute("CREATE UNIQUE INDEX retally_pilot_lead_identity ON leads(external_id) "
                       "WHERE external_id GLOB 'retally:synthetic:*'")
            db.execute("CREATE UNIQUE INDEX retally_pilot_task_identity ON tasks(title) "
                       "WHERE title GLOB 'Qualify inquiry [[]RETALLY-*'")
    elif not (db_path.exists() and login_path.exists() and client_path.exists()):
        raise RuntimeError("incomplete pilot state; use a fresh private directory for new acceptance")
    log = (state / "server.log").open("ab")
    server = subprocess.Popen([str(Path(args.binary).resolve())], cwd=state, env=env,
                              stdin=subprocess.DEVNULL, stdout=log, stderr=log, preexec_fn=block_server_egress)
    def stop(*_):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, stop)
    try:
        for _ in range(100):
            if server.poll() is not None:
                raise RuntimeError("GopherCRM exited; inspect private server.log")
            try:
                registration = api(args.port, "/auth/registration")
                break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError("GopherCRM startup timed out")
        if registration != {"enabled": False}:
            raise RuntimeError("public registration must be disabled")
        if fresh:
            token = api(args.port, "/auth/login", {"email": "bootstrap@example.invalid",
                                                   "password": bootstrap_pass})["token"]
            login = {"email": "sales@example.invalid", "password": secrets.token_urlsafe(30) + "Aa1!"}
            user = api(args.port, "/users", dict(login, first_name="Synthetic", last_name="Owner", role="sales"),
                       "Bearer " + token, 201)
            bearer = api(args.port, "/auth/login", login)["token"]
            expires = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            key = api(args.port, "/api-keys", {"name": "RETALLY synthetic worker", "expires_at": expires},
                      "Bearer " + bearer, 201)["key"]
            write_private(login_path, login)
            write_private(client_path, {"base_url": f"http://127.0.0.1:{args.port}", "api_key": key,
                                        "owner_id": user["id"]})
        client = json.loads(client_path.read_text())
        me = api(args.port, "/users/me", token="ApiKey " + client["api_key"])
        if client["base_url"] != f"http://127.0.0.1:{args.port}" or me["role"] != "sales" or me["id"] != client["owner_id"]:
            raise RuntimeError("incorrect pilot binding")
        print(f"Private sales pilot ready at {client['base_url']}; credentials in {client_path}", flush=True)
        return server.wait()
    except KeyboardInterrupt:
        return 0
    finally:
        if server.poll() is None:
            server.terminate()
            try:
                server.wait(timeout=10)
            except subprocess.TimeoutExpired:
                server.kill()
                server.wait()
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--binary", required=True)
    parser.add_argument("--admin-binary", required=True)
    parser.add_argument("--state", required=True)
    parser.add_argument("--port", type=int, default=19823)
    sys.exit(run(parser.parse_args()))
