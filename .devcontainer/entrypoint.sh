#!/bin/bash

# -- Resolve target UID/GID ---------------------------------------------------
# Priority:
#   1. DEVCONTAINER_UID/GID env vars (firewalled mode — explicit)
#   2. Workspace directory owner (IDE started as root without explicit UID)
#   3. Current UID (normal mode — --user already set the UID)

target_uid="${DEVCONTAINER_UID:-$(id -u)}"
target_gid="${DEVCONTAINER_GID:-$(id -g)}"

# If running as root without explicit UID, infer from workspace owner.
# Handles IDEs like Zed that ignore remoteUser and start as root.
if [[ "$(id -u)" = "0" ]] && [[ -z "${DEVCONTAINER_UID:-}" ]]; then
    workspace="${DEVCONTAINER_WORKSPACE:-$(pwd)}"
    if [[ -d "$workspace" ]]; then
        target_uid="$(stat -c '%u' "$workspace")"
        target_gid="$(stat -c '%g' "$workspace")"
    fi
fi

# -- Inject passwd entry for the target UID ------------------------------------
if ! getent passwd "$target_uid" >/dev/null 2>&1; then
    echo "dev:x:${target_uid}:${target_gid}:dev:${HOME}:/bin/bash" >> /etc/passwd
fi

# -- Firewall (firewalled mode only) -------------------------------------------
# Requires: root, NET_ADMIN capability, DEVCONTAINER_FIREWALL=1
if [[ "${DEVCONTAINER_FIREWALL:-}" = "1" ]] && [[ "$(id -u)" = "0" ]]; then
    /usr/local/bin/firewall.sh
    # Snapshot allowed IPs before privilege drop (ipset needs NET_ADMIN to list)
    ipset list allowed-domains | grep -E '^[0-9]' > /tmp/firewall-allowed-ips.txt 2>/dev/null || true
fi

# -- Drop privileges if running as root with a non-root target ----------------
# Use the username (not uid:gid) so gosu loads supplemental groups from /etc/group,
# which includes the docker group added above via usermod.
if [[ "$(id -u)" = "0" ]] && [[ "${target_uid}" != "0" ]]; then
    target_user="$(getent passwd "$target_uid" | cut -d: -f1)"
    exec gosu "${target_user:-${target_uid}:${target_gid}}" "$@"
fi

# -- Validate Poetry venv location ---------------------------------------------
# Inside the devcontainer POETRY_VIRTUALENVS_IN_PROJECT must be false (or unset).
# If it's true, Poetry puts the venv in .venv/ — but .venv/ is not created inside
# the container (it lives on the host bind mount). Every `just` recipe will fail.
if [[ "${POETRY_VIRTUALENVS_IN_PROJECT:-false}" = "true" ]]; then
    echo "WARNING: POETRY_VIRTUALENVS_IN_PROJECT=true inside the devcontainer." >&2
    echo "         Poetry will look for .venv/ which does not exist here." >&2
    echo "         Set POETRY_VIRTUALENVS_IN_PROJECT=false or unset it." >&2
fi

exec "$@"
