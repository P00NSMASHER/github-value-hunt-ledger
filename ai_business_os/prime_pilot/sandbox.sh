#!/bin/bash
# Only used with the synthetic worktree created by pilot.mjs.
set -eu
root=$(realpath "$1")
work=$(realpath "$2")
here=$(cd "$(dirname "$0")" && pwd)
pin=e311d6495124cf0bdc629c813fc97a39a9a3054d
[[ $(git -C "$root" rev-parse HEAD) == "$pin" ]]
git -C "$root" diff --quiet HEAD --
[[ $(git -C "$work" rev-parse HEAD) == 75b32959e630c606fd20086b08d59dc30b645905 ]]
[[ -z $(git -C "$work" status --porcelain) ]]
mounts=()
for path in LICENSE package.json prime-agent.sh node_modules packages/{agent,ai,tui,coding-agent}/{package.json,dist}; do
    mounts+=(--ro-bind "$root/$path" "/prime/$path")
done
# A fresh network namespace has no routes. Keep the host home, Docker socket, /etc, and
# ambient environment outside. All app state expires with the PID namespace and tmpfs.
exec unshare --map-current-user --net bwrap --unshare-user --disable-userns --unshare-pid \
    --unshare-ipc --unshare-uts --cap-drop ALL --die-with-parent --new-session --clearenv \
    --ro-bind /usr/bin /usr/bin --symlink usr/bin /bin --ro-bind /usr/lib /usr/lib \
    --ro-bind /lib /lib --ro-bind /lib64 /lib64 --dev /dev --proc /proc \
    --size 134217728 --tmpfs /tmp --dir /tmp/home --perms 0700 --dir /tmp/home/sessions \
    --ro-bind "$(command -v node)" /node-bin/node "${mounts[@]}" --ro-bind "$work" /work \
    --ro-bind "$here/replay-provider.ts" /fixture/provider.ts --ro-bind "$here/replay.patch" /fixture/replay.patch \
    --chdir /work --setenv HOME /tmp/home --setenv PATH /node-bin:/usr/bin:/bin --setenv PI_OFFLINE 1 \
    --setenv PRIME_AGENT_INTERNAL_LEGACY_OWNED_WORKER_FRONTEND 1 --setenv TMPDIR /tmp \
    --setenv NODE_OPTIONS '--max-old-space-size=384 --disable-wasm-trap-handler' \
    -- /usr/bin/prlimit --cpu=20 --fsize=8388608 --nproc=128 --nofile=128 --as=8589934592 -- \
    /prime/prime-agent.sh --dist --mode rpc --session-dir /tmp/home/sessions --offline --no-tools \
    --no-skills --no-extensions --no-context-files --no-prompt-templates \
    --extension /fixture/provider.ts --model retally-replay/faux-1
