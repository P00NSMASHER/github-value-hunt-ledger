#!/usr/bin/env bash
# Prepares only a SIMULATED staging installation on an already approved OCI Linux VM.
# Does not provision cloud resources, start services, open firewall ports or move money.
set -euo pipefail

if [[ $# -ne 1 || ! "$1" =~ ^[a-f0-9]{40}$ ]]; then
  echo 'Usage: bash deployment/oracle-always-free/install-staging.sh <EXACT_GIT_SHA>' >&2
  exit 64
fi
if [[ $(id -u) -eq 0 ]]; then
  echo 'Run as a regular authorized Ubuntu account with sudo, not as root.' >&2
  exit 1
fi
if [[ $(uname -m) != 'aarch64' ]]; then
  echo 'Expected OCI Always Free Ampere A1 ARM64 host; refusing other architectures.' >&2
  exit 2
fi
repo_root=$(git rev-parse --show-toplevel)
cd "$repo_root"
actual_sha=$(git rev-parse HEAD)
if [[ "$actual_sha" != "$1" ]]; then
  echo 'Git HEAD is not the exact user-supplied revision.' >&2
  exit 3
fi
if [[ -n "$(git status --porcelain)" ]]; then
  echo 'Source checkout has uncommitted changes; refusing staging install.' >&2
  exit 4
fi
if [[ ! -f recoveryworks/workbench_server.py ||
      ! -f deployment/oracle-always-free/retally-synthetic.service ]]; then
  echo 'Missing required reviewed workbench/deployment files.' >&2
  exit 5
fi

# Ubuntu 24.04; only free OS packages. Never upgrade OCI tenancy or provision paid cloud resources.
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv git rsync curl ca-certificates
if ! id retally >/dev/null 2>&1; then
  sudo useradd --system --no-create-home --shell /usr/sbin/nologin retally
fi
release_dir="/opt/retally/releases/$actual_sha"
if [[ -e "$release_dir" ]]; then
  echo 'This exact source release is already staged; will not replace it.' >&2
  exit 6
fi
sudo install -d -m 0755 /opt/retally /opt/retally/releases
sudo install -d -m 0755 "$release_dir"
sudo rsync -a --exclude='.git' --exclude='__pycache__' --exclude='.pytest_cache' ./ "$release_dir/"
sudo chown -R root:root "$release_dir"
sudo ln -sfn "$release_dir" /opt/retally/current
sudo install -d -o retally -g retally -m 0700 /var/lib/retally
if [[ -e /var/lib/retally/synthetic-preview ]]; then
  echo 'A staging workspace already exists. Refusing to modify existing private state.' >&2
  exit 7
fi
sudo -u retally sh -c 'cd /opt/retally/current && python3 -m recoveryworks.seven_branch_simulation --workspace /var/lib/retally/synthetic-preview --exercise >/dev/null'
sudo install -m 0644 deployment/oracle-always-free/retally-synthetic.service /etc/systemd/system/retally-synthetic.service
sudo systemctl daemon-reload

# Intentional release hold: do NOT enable or start the service, Tunnel or public DNS.
echo 'SIMULATION staged; service NOT started, NOT enabled; no customer records installed.'
echo 'Independent code approval, host acceptance, Access policy and sealed-backup restore remain required.'
