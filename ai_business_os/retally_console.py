"""Start only the synthetic owner UI on loopback; no production gateway or worker."""

import argparse
from getpass import getpass
import hashlib
import os
from pathlib import Path
import secrets

from ai_business_os.runtime_service import build_server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    parser.add_argument("--port", default=8684, type=int)
    args = parser.parse_args()
    desk = (args.workspace / "desk.sqlite").resolve(strict=True)
    if desk.parent.stat().st_mode & 0o077:
        parser.error("workspace must be private (0700)")
    password = getpass("Choose a temporary operator access code (12+ characters): ")
    if len(password) < 12:
        parser.error("access code is too short")
    os.environ.update(
        AIBOS_UI_ACCESS_SHA256=hashlib.sha256(password.encode()).hexdigest(),
        AIBOS_UI_SESSION_SECRET=secrets.token_urlsafe(48),
        AIBOS_UI_PRINCIPAL="Pilot owner",
        AIBOS_RETALLY_SYNTHETIC_DESK=str(desk),
        PORT=str(args.port),
    )
    with build_server(pilot_only=True) as server:
        print(f"Private synthetic desk available at http://127.0.0.1:{server.server_port}/", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
