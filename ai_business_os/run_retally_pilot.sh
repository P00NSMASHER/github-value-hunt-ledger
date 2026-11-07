#!/usr/bin/env bash
# Linux private acceptance; no credentials or production services required.
set -eu
umask 077
repo=$(cd "$(dirname "$0")/.." && pwd)
work=${1:?Supply a NEW private workspace outside the repository}
cache=${RETALLY_PILOT_CACHE:-"${XDG_CACHE_HOME:-$HOME/.cache}/retally-pilot"}
mkdir -p "$cache"
cache=$(cd "$cache" && pwd)
case "$cache/" in "$repo/"*) echo "Keep private dependencies outside the checkout" >&2; exit 2;; esac
if ! go version | grep -q 'go version go1\.'; then
  echo "A genuine Go 1.25+ toolchain is required to build GopherCRM." >&2; exit 1
fi
pin_checkout() {
  path=$1 url=$2 pin=$3
  if [ ! -d "$path/.git" ]; then git clone --quiet --no-checkout --depth=1 "$url" "$path"; fi
  [ "$(git -C "$path" remote get-url origin)" = "$url" ] || exit 2
  [ -z "$(git -C "$path" status --porcelain --untracked-files=no)" ] || {
    # New no-checkout clones report all tracked files deleted. Accept only an empty working tree.
    [ -z "$(find "$path" -mindepth 1 -maxdepth 1 ! -name .git -print -quit)" ] || exit 2
  }
  if ! git -C "$path" cat-file -e "$pin^{commit}" 2>/dev/null; then git -C "$path" fetch --quiet --depth=1 origin "$pin"; fi
  git -C "$path" -c advice.detachedHead=false checkout --quiet --detach "$pin"
  [ "$(git -C "$path" rev-parse HEAD)" = "$pin" ]
}
pin_checkout "$cache/gopher" https://github.com/florinel-chis/GopherCRM.git ae53d6dbb251e33484207756cc9699bd316834a7
pin_checkout "$cache/capturebrief" https://github.com/P00NSMASHER/capturebrief.git 01520d46a90cd0b07fad1850a2873cb30374bfce
(cd "$cache/gopher" && go build -o "$cache/gopher-server" ./cmd && go build -o "$cache/create-admin" ./cmd/create-admin)
if [ ! -x "$cache/venv/bin/python" ]; then python3 -m venv "$cache/venv"; fi
"$cache/venv/bin/python" -m pip -q install 'pypdf==6.10.0'
args=()
if [ -n "${RETALLY_SOURCE_PDF:-}" ]; then args+=(--source-pdf "$RETALLY_SOURCE_PDF"); fi
cd "$repo"
exec "$cache/venv/bin/python" -m ai_business_os.retally_pilot --workspace "$work" \
 --gopher "$cache/gopher-server" --admin "$cache/create-admin" --capturebrief "$cache/capturebrief" "${args[@]}"
