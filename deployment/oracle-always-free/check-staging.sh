#!/usr/bin/env bash
# Read-only synthetic health checks. Run only after the service is explicitly started.
set -euo pipefail
if [[ $(uname -m) != 'aarch64' ]]; then
  echo 'Not the expected A1 Arm64 staging host.' >&2
  exit 2
fi
if ! systemctl is-active --quiet retally-synthetic.service; then
  echo 'Synthetic systemd service is not active.' >&2
  exit 2
fi
if ! ss -ltnH | awk '{print $4}' | grep -qx '127.0.0.1:18765'; then
  echo 'Expected a loopback-only listener on 18765.' >&2
  exit 2
fi
if ss -ltnH | awk '{print $4}' | grep -Eq '^(0\.0\.0\.0|\*|\[::\]|::):18765$'; then
  echo 'Unsafe non-loopback listener found.' >&2
  exit 2
fi
base=http://127.0.0.1:18765
get_code() { curl --noproxy '*' --silent --output /dev/null --write-out '%{http_code}' --max-time 5 "$@"; }
[[ "$(get_code "$base/")" == '200' ]] || { echo 'Synthetic index not healthy.' >&2; exit 2; }
[[ "$(get_code "$base/api/state")" == '403' ]] || { echo 'API unexpectedly accessible without token.' >&2; exit 2; }
[[ "$(get_code -H 'Host: attacker.invalid' "$base/")" == '403' ]] || { echo 'Unapproved host accepted.' >&2; exit 2; }
[[ "$(get_code "$base/credentials.json")" == '404' ]] || { echo 'Credential filename unexpectedly served.' >&2; exit 2; }
cd /opt/retally/current
sudo -u retally python3 -m recoveryworks.workbench_health --workspace /var/lib/retally/synthetic-preview >/dev/null
echo 'PASS synthetic loopback, host controls, API isolation, hash-chain, backup and restore.'
echo 'NOT a signoff for real customer data, device authorization or off-device recovery.'
