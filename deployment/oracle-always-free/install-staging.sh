#!/usr/bin/env bash
# Prepare SIMULATED staging only on an attested OCI Always Free A1 or E2 Micro host.
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
# A1 is the default. x86-64 must be explicitly requested and independently
# checked against OCI instance metadata to allow only the fixed Always Free Micro.
micro_host=0
if [[ $(uname -m) != 'aarch64' ]]; then
  if [[ $(uname -m) != 'x86_64' || ${RETALLY_MICRO_HOST:-} != 1 ]]; then
    echo 'Only reviewed OCI A1 or explicitly attested Always Free E2 Micro hosts are supported.' >&2
    exit 2
  fi
  micro_host=1
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
      ! -f deployment/oracle-always-free/retally-synthetic.service ||
      ! -f deployment/oracle-always-free/verify_oci_host.py ||
      ( "$micro_host" == 1 && ! -f deployment/oracle-always-free/retally-micro-memory.conf ) ]]; then
  echo 'Missing required reviewed workbench/deployment files.' >&2
  exit 5
fi

# Authenticate the CURRENT OCI VM against non-proxied v2 IMDS before
# installing packages, modifying services, or allocating persistent storage.
if [[ "$micro_host" == 1 ]]; then
  python3 deployment/oracle-always-free/verify_oci_host.py --micro
else
  python3 deployment/oracle-always-free/verify_oci_host.py --a1
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
   [[ -e /etc/systemd/system/retally-synthetic.service.d/oci-micro-memory.conf ]] ||
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
if [[ "$micro_host" == 1 ]]; then
  # Leave RAM for the 1 GiB guest OS. Synthetic service remains DISABLED.
  sudo install -d -m 0755 /etc/systemd/system/retally-synthetic.service.d
  sudo install -m 0644 "$release_dir/deployment/oracle-always-free/retally-micro-memory.conf" \
    /etc/systemd/system/retally-synthetic.service.d/oci-micro-memory.conf
fi
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
