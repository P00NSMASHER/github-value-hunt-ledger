#!/usr/bin/env bash
# Prepare SIMULATED staging only on an approved Oracle Always Free ARM64 host.
# Never create a paid resource, start a service, expose a tunnel, or process customers.
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
actual_sha=$(git rev-parse --verify HEAD)
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

release_dir="/opt/retally/releases/$actual_sha"
workspace_dir="/var/lib/retally/synthetic-preview"
unit_path="/etc/systemd/system/retally-synthetic.service"

# Refuse existing state or services BEFORE package installation or pointer changes.
if [[ -e "$release_dir" || -L "$release_dir" ]]; then
  echo 'This source release is already staged; refusing overwrite.' >&2
  exit 6
fi
if [[ -e "$workspace_dir" || -L "$workspace_dir" ]]; then
  echo 'A staging workspace already exists; no private state will be touched.' >&2
  exit 7
fi
if [[ -e "$unit_path" || -L "$unit_path" ]] ||
   systemctl is-active --quiet retally-synthetic.service ||
   systemctl is-enabled --quiet retally-synthetic.service; then
  echo 'An existing service must be reviewed separately before a fresh install.' >&2
  exit 8
fi

# Ubuntu 24.04; only free OS packages. Never upgrade OCI or provision paid resources.
sudo apt-get update
sudo DEBIAN_FRONTEND=noninteractive apt-get install -y python3 python3-venv git ca-certificates
if ! id retally >/dev/null 2>&1; then
  sudo useradd --system --no-create-home --shell /usr/sbin/nologin retally
fi
sudo install -d -m 0755 /opt/retally /opt/retally/releases
sudo install -d -o retally -g retally -m 0700 /var/lib/retally

# Only exact committed Git objects are staged. No copying ignored local secrets.
staging=$(sudo mktemp -d -p /opt/retally/releases ".staging-$actual_sha.XXXXXXXX")
candidate_link=''
cleanup() {
  if [[ -n "$candidate_link" ]]; then sudo rm -f -- "$candidate_link"; fi
  if [[ -n "$staging" ]]; then sudo rm -rf -- "$staging"; fi
}
trap cleanup EXIT
git archive --format=tar "$actual_sha" |
  sudo tar -xf - -C "$staging" --no-same-owner --no-same-permissions
sudo chown -R root:root "$staging"
sudo chmod 0755 "$staging"
sudo test -f "$staging/recoveryworks/workbench_server.py"
sudo test -f "$staging/deployment/oracle-always-free/retally-synthetic.service"

# Seed and verify against staged code, not through /opt/retally/current.
if [[ -e "$workspace_dir" || -L "$workspace_dir" ]]; then
  echo 'Concurrent staging workspace detected; refusing overwrite.' >&2
  exit 7
fi
sudo -u retally -- sh -c 'cd "$1" && PYTHONDONTWRITEBYTECODE=1 python3 -m recoveryworks.seven_branch_simulation --workspace "$2" --exercise >/dev/null' retally-staging "$staging" "$workspace_dir"
sudo -u retally -- sh -c 'cd "$1" && PYTHONDONTWRITEBYTECODE=1 python3 -m recoveryworks.workbench_health --workspace "$2" >/dev/null' retally-health "$staging" "$workspace_dir"

if [[ -e "$release_dir" || -L "$release_dir" ]]; then
  echo 'Concurrent release destination detected; refusing overwrite.' >&2
  exit 6
fi
sudo mv -T -- "$staging" "$release_dir"
staging=''
sudo install -m 0644 "$release_dir/deployment/oracle-always-free/retally-synthetic.service" "$unit_path"
sudo systemctl daemon-reload
if systemctl is-active --quiet retally-synthetic.service ||
   systemctl is-enabled --quiet retally-synthetic.service; then
  echo 'Unexpected active or enabled service; refusing promotion.' >&2
  exit 8
fi

# Switch atomically ONLY after synthetic tests and systemd reload succeed.
candidate_link="/opt/retally/.current-$actual_sha-$$"
sudo ln -s "$release_dir" "$candidate_link"
sudo mv -Tf -- "$candidate_link" /opt/retally/current
candidate_link=''
echo 'SIMULATION staged; service NOT started, NOT enabled; no customer records installed.'
echo 'Independent code approval, host acceptance, Access policy and sealed-backup restore remain required.'
