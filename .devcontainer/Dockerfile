# renovate: datasource=docker depName=python
FROM python:3.12-bookworm@sha256:b06e8541b66390dbe26e635448bfa51b6dd15cdc4d79c5dfd9cacdac8ec5ab91

ARG TZ
ENV TZ="${TZ}"

# No WORKDIR — project mounted at host-native absolute path
# for git worktree compatibility (.git file contains absolute paths)

# -- Environment (set before all tool installs) --------------------------------
ENV HOME=/tmp/home
ENV PATH="${HOME}/.local/bin:${PATH}"

# Convention for tooling that checks devcontainer context
ENV DEVCONTAINER=true
ENV EDITOR=nano
ENV VISUAL=nano
ENV HISTFILE=/commandhistory/.zsh_history

# Block postinstall scripts and require 24h package age for supply-chain safety.
# Claude Code runs `npm install` for MCP servers at runtime.
ENV NPM_CONFIG_IGNORE_SCRIPTS=true
ENV NPM_CONFIG_MINIMUM_RELEASE_AGE=1440

# gh config dir — set before running gh so the build-time version check writes
# here (root-owned 0600 files); we clean up and recreate as 1777 afterwards.
ENV GH_CONFIG_DIR=/tmp/gh-config

# -- System packages -----------------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends \
        curl ca-certificates gnupg \
        git openssh-client \
        iptables ipset iproute2 dnsutils \
        less procps fzf zsh man-db unzip jq nano \
        aggregate \
    && rm -rf /var/lib/apt/lists/*

# -- Node.js 22 ----------------------------------------------------------------
# renovate: datasource=node-version depName=node
ARG NODE_MAJOR="22"
RUN curl -fsSL https://deb.nodesource.com/setup_${NODE_MAJOR}.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

# -- gosu (privilege drop — used by entrypoint in IDE + firewalled modes) ------
# renovate: datasource=github-releases depName=tianon/gosu
ARG GOSU_VERSION="1.17"
RUN arch="$(dpkg --print-architecture)" \
    && curl -fsSL "https://github.com/tianon/gosu/releases/download/${GOSU_VERSION}/gosu-${arch}" \
        -o /usr/local/bin/gosu \
    && chmod +x /usr/local/bin/gosu \
    && gosu --version

# -- gh CLI (GitHub forge) -----------------------------------------------------
# renovate: datasource=github-releases depName=cli/cli extractVersion=^v(?<version>.*)$
ARG GH_VERSION="2.88.1"
# `gh --version` creates $GH_CONFIG_DIR owned by root with 0600 files.
# Remove it and recreate as world-writable so non-root users can either:
#   - bind-mount their host config at runtime, or
#   - let gh create a fresh config on first use
RUN arch="$(dpkg --print-architecture)" \
    && curl -fsSL "https://github.com/cli/cli/releases/download/v${GH_VERSION}/gh_${GH_VERSION}_linux_${arch}.deb" \
        -o /tmp/gh.deb \
    && dpkg -i /tmp/gh.deb \
    && rm /tmp/gh.deb \
    && gh --version \
    && rm -rf /tmp/gh-config \
    && mkdir -m 1777 /tmp/gh-config

# -- git-delta (enhanced diff viewer) -----------------------------------------
# renovate: datasource=github-releases depName=dandavison/delta extractVersion=^(?<version>.*)$
ARG GIT_DELTA_VERSION="0.18.2"
RUN arch="$(dpkg --print-architecture)" \
    && curl -fsSL "https://github.com/dandavison/delta/releases/download/${GIT_DELTA_VERSION}/git-delta_${GIT_DELTA_VERSION}_${arch}.deb" \
        -o /tmp/delta.deb \
    && dpkg -i /tmp/delta.deb \
    && rm /tmp/delta.deb \
    && delta --version

# -- just (task runner) --------------------------------------------------------
# renovate: datasource=github-releases depName=casey/just extractVersion=^(?<version>.*)$
ARG JUST_VERSION="1.40.0"
RUN arch="$(dpkg --print-architecture)" \
    && case "$arch" in \
         amd64) just_arch="x86_64-unknown-linux-musl" ;; \
         arm64) just_arch="aarch64-unknown-linux-musl" ;; \
         *) echo "Unsupported arch: $arch" && exit 1 ;; \
       esac \
    && curl -fsSL "https://github.com/casey/just/releases/download/${JUST_VERSION}/just-${JUST_VERSION}-${just_arch}.tar.gz" \
        | tar -xz -C /usr/local/bin just \
    && just --version

# -- Poetry --------------------------------------------------------------------
# renovate: datasource=pypi depName=poetry
ARG POETRY_VERSION="1.8.5"
RUN pip install --no-cache-dir poetry==${POETRY_VERSION}

# -- zsh-in-docker (Powerline10k theme + fzf keybindings) ---------------------
# renovate: datasource=github-releases depName=deluan/zsh-in-docker extractVersion=^v(?<version>.*)$
ARG ZSH_IN_DOCKER_VERSION="1.2.0"
RUN sh -c "$(curl -fsSL https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \
    -p git \
    -p fzf \
    -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
    -a "source /usr/share/doc/fzf/examples/completion.zsh" \
    -a "export PROMPT_COMMAND='history -a' && export HISTFILE=/commandhistory/.zsh_history" \
    -a "echo '\033[1;33m[DEVCONTAINER] No Docker. Run: just container-ci (lint + type check + unit tests)\033[0m'" \
    -a "echo '\033[1;31m[DEVCONTAINER] Never run: just backend-test | just ci | just backend-perf | just backend-e2e | just frontend-e2e | docker\033[0m'" \
    -x

# -- Claude Code (native binary, auto-updates) ---------------------------------
# HOME is set above so the installer places the binary at $HOME/.local/bin/claude
RUN curl -fsSL https://claude.ai/install.sh | bash \
    && claude --version

# -- Codex CLI -----------------------------------------------------------------
RUN npm install -g @openai/codex

# -- ccstatusline (pre-installed so UserPromptSubmit hook doesn't hit npm CDN) -
RUN npm install -g ccstatusline

# -- Firewall ------------------------------------------------------------------
COPY firewall.sh /usr/local/bin/firewall.sh
RUN chmod +x /usr/local/bin/firewall.sh

COPY firewall-allowlist.txt /usr/local/share/firewall-allowlist.txt

# firewall-list — inspect allowed IPs (reads snapshot taken before privilege drop)
RUN printf '#!/bin/bash\ncat /tmp/firewall-allowed-ips.txt 2>/dev/null || echo "Firewall not active"\n' \
        > /usr/local/bin/firewall-list \
    && chmod +x /usr/local/bin/firewall-list

# -- Git and SSH ---------------------------------------------------------------
# Wildcard — mount path unknown at build time
RUN git config --system safe.directory '*'

# Populate known hosts (no interactive prompt)
# Include github.com — Claude Code distribution uses GitHub
RUN mkdir -p /etc/ssh \
    && ssh-keyscan -t ecdsa,rsa,ed25519 github.com >> /etc/ssh/ssh_known_hosts 2>/dev/null

# -- Non-root user (for remoteUser + updateRemoteUserUID) ----------------------
# IDEs that support the devcontainer spec remap this UID to match the host.
# IDEs that don't (Zed) rely on the entrypoint to detect and drop to the
# workspace owner UID via gosu.
RUN groupadd --gid 1000 dev \
 && useradd --uid 1000 --gid 1000 --no-create-home --home-dir /tmp/home --shell /usr/bin/zsh dev

# -- Permissions ---------------------------------------------------------------
# Sticky bit — shared temp dirs writable by any UID
# /etc/passwd + /etc/group writable so entrypoint can inject user/group entries
RUN chmod -R 1777 /tmp/home \
    && chmod 0666 /etc/passwd /etc/group

# -- Persistent history dir (volume-mountable) ---------------------------------
RUN mkdir /commandhistory \
    && touch /commandhistory/.bash_history \
    && touch /commandhistory/.zsh_history \
    && chmod 1777 /commandhistory

# -- Entrypoint ----------------------------------------------------------------
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh
ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["zsh"]
