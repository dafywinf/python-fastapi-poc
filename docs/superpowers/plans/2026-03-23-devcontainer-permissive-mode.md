# Tool-Belt: Python FastAPI Devcontainer Template with Claude Permissive Mode

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add `devcontainer-templates/python-fastapi/` directly to the tool-belt repo — a standalone, zero-host-dependency devcontainer template that bakes the full Claude alias set (including `cx` permissive mode) into the image, then self-validates by having Claude inside the container complete a TDD feedback loop with no permission prompts.

**Architecture:** Three phases, two actors, all work in the tool-belt repo.
- **Phase 1 (host):** Build the template files in `tool-belt/devcontainer-templates/python-fastapi/`. `claude.zsh` comes from `tool-belt/oh-my-zsh/custom/claude.zsh` (the canonical source) with one adaptation: `css` is removed because it references a host-only path.
- **Phase 2 (container — Claude in permissive mode):** Open `devcontainer-templates/python-fastapi/` as a devcontainer, run `cx` with a TDD task on the bundled scaffold, observe autonomous completion with zero permission prompts. This is the feedback loop that proves the template works.
- **Phase 3 (this repo — later):** Copy the proven `.devcontainer/` from tool-belt into `python-fastapi-poc`, remove the old `claude.zsh` host mount, rebuild.

**Tech Stack:** Docker devcontainer, Claude Code (`--dangerously-skip-permissions`), node:20 base image, Python 3.12 (apt), Poetry, FastAPI, pytest, iptables/ipset firewall, Oh-my-zsh.

---

## Why tool-belt first, not here

The `python-fastapi-poc` devcontainer is coupled to the full business stack (PostgreSQL, Redis, testcontainers, Alembic). Validating permissive mode patterns there means re-deriving them for every future project. The tool-belt approach:

- Proves the pattern once on a minimal, dependency-free scaffold
- The template lives in one canonical place; projects copy `.devcontainer/` and adapt
- Firewall, alias set, and Dockerfile patterns are tested in isolation
- Future stacks (`node-ts`, `go`, `generic-claude-agent`) follow the same structure

---

## Directory structure to create (in tool-belt)

```
tool-belt/
└── devcontainer-templates/
    └── python-fastapi/
        ├── .devcontainer/
        │   ├── devcontainer.json      # No claude.zsh bind mount — baked into image
        │   ├── Dockerfile             # node:20 + Python 3.12 + Poetry + Claude Code
        │   ├── init-firewall.sh       # Anthropic + GitHub + PyPI + npm
        │   └── claude.zsh             # Full alias set, container-safe (css excluded)
        ├── scaffold/
        │   ├── main.py                # FastAPI app — /health only
        │   ├── pyproject.toml         # fastapi, uvicorn, pytest, httpx, ruff
        │   └── tests/
        │       ├── __init__.py
        │       └── test_health.py     # Baseline: GET /health returns {"status":"ok"}
        ├── CLAUDE.md                  # FastAPI stub referencing tool-belt standards
        └── README.md                  # How to copy this template into a new project
```

---

## File Map

| Action | Path in tool-belt repo |
|--------|------------------------|
| Create | `devcontainer-templates/python-fastapi/.devcontainer/devcontainer.json` |
| Create | `devcontainer-templates/python-fastapi/.devcontainer/Dockerfile` |
| Create | `devcontainer-templates/python-fastapi/.devcontainer/init-firewall.sh` |
| Create | `devcontainer-templates/python-fastapi/.devcontainer/claude.zsh` |
| Create | `devcontainer-templates/python-fastapi/scaffold/main.py` |
| Create | `devcontainer-templates/python-fastapi/scaffold/pyproject.toml` |
| Create | `devcontainer-templates/python-fastapi/scaffold/tests/__init__.py` |
| Create | `devcontainer-templates/python-fastapi/scaffold/tests/test_health.py` |
| Create | `devcontainer-templates/python-fastapi/CLAUDE.md` |
| Create | `devcontainer-templates/python-fastapi/README.md` |

---

## Phase 1: Host — Build the Template in tool-belt

> **Working directory:** `~/Development/git-hub/tool-belt`

### Task 1: Create the container-safe `claude.zsh`

**Source:** `tool-belt/oh-my-zsh/custom/claude.zsh` — the canonical version.
**One change:** Remove the `css` function. It runs `bash ~/Development/git-hub/tool-belt/scripts/claude-standards-sync.sh` — a host-only path that does not exist inside the container. All other aliases (`cc`, `cx`, `cv`, `h`, `cdi`, `ct`, `ghv`, `ghcp`, `mcpi`, `ch`) are kept as-is.

- [ ] **Step 1: Create `.devcontainer/claude.zsh`**

```zsh
# Claude Code shell config — baked into the devcontainer image.
# Sourced automatically by Oh-my-zsh (all *.zsh in custom/ are loaded).
#
# Container-safe copy of tool-belt/oh-my-zsh/custom/claude.zsh.
# Excluded: css() — references host-only path ~/Development/git-hub/tool-belt/
# To keep in sync: edit the source file then re-copy this section.

echo "📂 Configuring Claude : $0  [ch for help]"

# --- Help ---
ch() {
  echo -e "\e[1;34m--------------------------------------------------\e[0m"
  echo -e "\e[1;32m       CLAUDE CUSTOM COMMANDS MENU                \e[0m"
  echo -e "\e[1;34m--------------------------------------------------\e[0m"
  echo -e "\e[1;33mcc\e[0m  : Launch standard Claude"
  echo -e "\e[1;33mh\e[0m   : Launch Claude with Haiku model (Fast)"
  echo -e "\e[1;33mcx\e[0m  : Launch Claude & skip all permissions"
  echo -e "\e[1;33mcv\e[0m  : Launch Claude in Voice-Optimized mode"
  echo -e "\e[1;33mcdi\e[0m : Launch Claude with local diagram context"
  echo -e "\e[1;33mct\e[0m  : Launch Claude in Teleport mode"
  echo -e "\e[1;34m--------------------------------------------------\e[0m"
}

# --- Core aliases ---
alias cc="claude"
alias h="claude --model haiku"
alias cx="claude --dangerously-skip-permissions"
alias cv="claude --dangerously-skip-permissions --append-system-prompt 'Voice mode: stay concise, skip preambles, and use spoken-style language.'"
alias ct="claude --teleport"

# --- Tools ---
alias ghv="gh repo view --web"
alias ghcp='GH_PAGER="" gh repo view --json name,owner --jq "\"https://github.com/\" + .owner.login"'
alias mcpi="bunx @modelcontextprotocol/inspector@latest"

# --- Diagram context launcher ---
unalias cdi 2>/dev/null
cdi() {
  local docs="./ai/diagrams/**/*.md"
  if ls $docs >/dev/null 2>&1; then
    claude --append-system-prompt "$(cat $docs)"
  else
    echo "No diagrams found. Starting standard Claude..."
    claude
  fi
}
```

### Task 2: Create the Dockerfile

Uses `node:20` as base (Claude Code requires node; Python 3.12 and Poetry added via apt/pip). Pattern mirrors the proven approach in `python-fastapi-poc/.devcontainer/Dockerfile`.

- [ ] **Step 2: Create `.devcontainer/Dockerfile`**

```dockerfile
FROM node:20

ARG TZ=UTC
ENV TZ="$TZ"

ARG CLAUDE_CODE_VERSION=latest
ARG ZSH_IN_DOCKER_VERSION=1.2.0

# System packages: dev tools + iptables/ipset for firewall + Python 3.12
RUN apt-get update && apt-get install -y --no-install-recommends \
  less git procps sudo fzf zsh man-db unzip gnupg2 \
  gh iptables ipset iproute2 dnsutils aggregate jq nano vim \
  python3 python3-pip python3-venv python3-dev \
  && apt-get clean && rm -rf /var/lib/apt/lists/*

# Poetry — installed system-wide so the node user can invoke it
RUN pip3 install --no-cache-dir poetry==1.8.5

# npm global dir — writable by node user
RUN mkdir -p /usr/local/share/npm-global && \
  chown -R node:node /usr/local/share

ENV DEVCONTAINER=true

RUN mkdir -p /workspace /home/node/.claude && \
  chown -R node:node /workspace /home/node/.claude

WORKDIR /workspace

USER node

ENV NPM_CONFIG_PREFIX=/usr/local/share/npm-global
ENV PATH=$PATH:/usr/local/share/npm-global/bin
ENV SHELL=/bin/zsh
ENV EDITOR=nano

# Oh-my-zsh with Powerlevel10k theme
RUN sh -c "$(wget -O- https://github.com/deluan/zsh-in-docker/releases/download/v${ZSH_IN_DOCKER_VERSION}/zsh-in-docker.sh)" -- \
  -p git \
  -p fzf \
  -a "source /usr/share/doc/fzf/examples/key-bindings.zsh" \
  -a "source /usr/share/doc/fzf/examples/completion.zsh" \
  -x

# Claude Code
RUN npm install -g @anthropic-ai/claude-code@${CLAUDE_CODE_VERSION}

# Bake project-controlled Claude aliases — no host bind-mount dependency.
# COPY uses build context (.devcontainer/), so the file must live there.
COPY --chown=node:node claude.zsh /home/node/.oh-my-zsh/custom/claude.zsh

# Firewall
COPY init-firewall.sh /usr/local/bin/
USER root
RUN chmod +x /usr/local/bin/init-firewall.sh && \
  echo "node ALL=(root) NOPASSWD: /usr/local/bin/init-firewall.sh" > /etc/sudoers.d/node-firewall && \
  chmod 0440 /etc/sudoers.d/node-firewall
USER node
```

### Task 3: Create `devcontainer.json`

No `claude.zsh` bind mount — it is baked into the image. Only `~/.claude` (the auth token and global settings) is mounted from the host.

- [ ] **Step 3: Create `.devcontainer/devcontainer.json`**

```json
{
  "name": "Python FastAPI + Claude",
  "build": {
    "dockerfile": "Dockerfile",
    "args": {
      "TZ": "${localEnv:TZ:UTC}",
      "CLAUDE_CODE_VERSION": "latest"
    }
  },
  "remoteUser": "node",
  "workspaceFolder": "/workspace",
  "workspaceMount": "source=${localWorkspaceFolder},target=/workspace,type=bind,consistency=delegated",
  "mounts": [
    "source=${localEnv:HOME}/.claude,target=/home/node/.claude,type=bind,consistency=cached"
  ],
  "containerEnv": {
    "NODE_OPTIONS": "--max-old-space-size=4096",
    "CLAUDE_CONFIG_DIR": "/home/node/.claude",
    "POWERLEVEL9K_DISABLE_GITSTATUS": "true"
  },
  "postStartCommand": "sudo /usr/local/bin/init-firewall.sh",
  "customizations": {
    "vscode": {
      "extensions": [
        "anthropic.claude-code",
        "ms-python.python",
        "ms-python.vscode-pylance",
        "charliermarsh.ruff"
      ],
      "settings": {
        "python.defaultInterpreterPath": "/workspace/.venv/bin/python",
        "editor.formatOnSave": true,
        "[python]": {
          "editor.defaultFormatter": "charliermarsh.ruff"
        },
        "terminal.integrated.defaultProfile.linux": "zsh"
      }
    }
  }
}
```

### Task 4: Create `init-firewall.sh`

Extends the pattern from `python-fastapi-poc/.devcontainer/init-firewall.sh` with PyPI outbound added for `poetry install`.

- [ ] **Step 4: Create `.devcontainer/init-firewall.sh`**

```bash
#!/bin/bash
# Restrictive outbound firewall for the Python FastAPI devcontainer.
#
# Allowed outbound:
#   DNS (53), SSH (22), GitHub, Anthropic API,
#   PyPI (pypi.org + files.pythonhosted.org), npm registry, VS Code marketplace
#
# Inbound: established/related only.

set -euo pipefail

log() { echo "[firewall] $*"; }
die() { echo "[firewall] ERROR: $*" >&2; exit 1; }

iptables -F; iptables -X; iptables -t nat -F; iptables -t nat -X
ipset destroy 2>/dev/null || true

resolve_to_set() {
  local set_name="$1" host="$2"
  dig +short "$host" A | grep -E '^[0-9]+\.' | while read -r ip; do
    ipset add "$set_name" "$ip" 2>/dev/null || true
  done
}

ipset create allowed_hosts hash:net

# GitHub
log "Fetching GitHub CIDRs..."
curl -sf https://api.github.com/meta \
  | jq -r '.web[], .api[], .git[]' \
  | while read -r cidr; do ipset add allowed_hosts "$cidr" 2>/dev/null || true; done

# Anthropic
resolve_to_set allowed_hosts api.anthropic.com
resolve_to_set allowed_hosts statsig.anthropic.com

# PyPI
resolve_to_set allowed_hosts pypi.org
resolve_to_set allowed_hosts files.pythonhosted.org

# npm
resolve_to_set allowed_hosts registry.npmjs.org

# VS Code
resolve_to_set allowed_hosts marketplace.visualstudio.com
resolve_to_set allowed_hosts vscode.blob.core.windows.net

HOST_GW=$(ip route | awk '/default/ {print $3; exit}')

# Inbound
iptables -A INPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
iptables -A INPUT -i lo -j ACCEPT
[ -n "$HOST_GW" ] && iptables -A INPUT -s "$HOST_GW" -p udp --sport 53 -j ACCEPT
iptables -A INPUT -j DROP

# Outbound
iptables -A OUTPUT -o lo -j ACCEPT
iptables -A OUTPUT -m state --state ESTABLISHED,RELATED -j ACCEPT
[ -n "$HOST_GW" ] && iptables -A OUTPUT -d "$HOST_GW" -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -d 8.8.8.8    -p udp --dport 53 -j ACCEPT
iptables -A OUTPUT -p tcp --dport 22  -j ACCEPT
iptables -A OUTPUT -p tcp --dport 443 -m set --match-set allowed_hosts dst -j ACCEPT
iptables -A OUTPUT -j DROP

log "Verifying firewall..."
curl -sf --max-time 5 https://api.github.com/zen > /dev/null \
  && log "GitHub: OK" || die "GitHub blocked — check firewall rules"
curl -sf --max-time 5 https://pypi.org/pypi/fastapi/json > /dev/null \
  && log "PyPI: OK"   || log "PyPI: WARNING"
log "Firewall active."
```

- [ ] **Step 4b: Make executable**

```bash
chmod +x devcontainer-templates/python-fastapi/.devcontainer/init-firewall.sh
```

### Task 5: Create the minimal scaffold

No database, no auth — just enough for the Phase 2 validation loop.

- [ ] **Step 5.1: Create `scaffold/pyproject.toml`**

```toml
[tool.poetry]
name = "scaffold"
version = "0.1.0"
description = "Minimal FastAPI scaffold for devcontainer template validation"
authors = []

[tool.poetry.dependencies]
python = "^3.12"
fastapi = "^0.115"
uvicorn = {extras = ["standard"], version = "^0.32"}

[tool.poetry.group.dev.dependencies]
pytest = "^8.3"
httpx = "^0.28"
ruff = "^0.8"

[tool.ruff]
line-length = 88

[tool.pytest.ini_options]
testpaths = ["tests"]

[build-system]
requires = ["poetry-core"]
build-backend = "poetry.core.masonry.api"
```

- [ ] **Step 5.2: Create `scaffold/main.py`**

```python
"""Minimal FastAPI scaffold for devcontainer template validation."""

from fastapi import FastAPI

app = FastAPI(title="Scaffold", version="0.1.0")


@app.get("/health")
def health_check() -> dict[str, str]:
    """Return service liveness status.

    Returns:
        A dict with a status key.
    """
    return {"status": "ok"}
```

- [ ] **Step 5.3: Create `scaffold/tests/__init__.py`** (empty)

- [ ] **Step 5.4: Create `scaffold/tests/test_health.py`**

```python
"""Baseline test — must pass before the Phase 2 validation task begins."""

import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_health_returns_ok(client: TestClient) -> None:
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
```

### Task 6: Create `CLAUDE.md`

- [ ] **Step 6: Create `CLAUDE.md`**

```markdown
# Project Instructions

## Global Standards

@.claude/standards/GIT_STANDARDS.md
@.claude/standards/PYTHON_STANDARDS.md

## Tech Stack

- **Framework:** FastAPI (sync — use `def` not `async def`)
- **Python:** 3.12
- **Dependencies:** Poetry with in-project `.venv`
- **Linter:** Ruff (88 chars)

## Notes

This is the minimal validation scaffold for the python-fastapi devcontainer
template. Extend when copying into a real project.
```

### Task 7: Create `README.md`

- [ ] **Step 7: Create `README.md`**

```markdown
# Python FastAPI Devcontainer Template

Standalone devcontainer for Python FastAPI projects with Claude Code in permissive mode.

## What's included

- `node:20` base + Python 3.12 + Poetry
- Full Claude alias set baked in — no host bind-mount dependency
  - `cx` = `claude --dangerously-skip-permissions` (permissive mode)
  - `cc`, `cv`, `h`, `cdi`, `ct`, `ch` — see `ch` for the full menu
- Restrictive outbound firewall: Anthropic + GitHub + PyPI + npm only
- Minimal FastAPI scaffold in `scaffold/` for self-validation

## Usage in a new project

1. Copy `.devcontainer/` into your project root
2. Open in VS Code → "Reopen in Container"
3. Run `cx` to launch Claude in permissive mode

## Validation

To verify the template works (Phase 2 of the plan):
1. Open this directory itself as a devcontainer
2. Follow the Phase 2 prompt in `docs/superpowers/plans/2026-03-23-devcontainer-permissive-mode.md`
```

### Task 8: Commit

- [ ] **Step 8: Commit in tool-belt**

```bash
cd ~/Development/git-hub/tool-belt

git add devcontainer-templates/

git commit -m "feat(devcontainer): add python-fastapi template with claude permissive mode

Add devcontainer-templates/python-fastapi/ — a standalone, self-validating
devcontainer template for Python FastAPI projects.

Includes: claude.zsh baked into image (full alias set, container-safe),
node:20 Dockerfile + Python 3.12 + Poetry, init-firewall.sh (Anthropic +
GitHub + PyPI + npm), minimal FastAPI scaffold for permissive-mode validation."
```

---

## Phase 2: Validate — Claude Inside the Container

> **Working directory:** `tool-belt/devcontainer-templates/python-fastapi/` opened as a devcontainer in VS Code.
> **Actor:** Claude Code running via `cx` (permissive mode).

### Step 2.1: Confirm aliases loaded

```zsh
type cx
# Expected: cx is an alias for "claude --dangerously-skip-permissions"
ch
# Expected: shows the full Claude command menu
```

### Step 2.2: Confirm firewall is selective

```zsh
# Should succeed (allowed)
curl -sf https://pypi.org/pypi/fastapi/json | jq '.info.name'
# Expected: "fastapi"

# Should fail (blocked)
curl -sf https://example.com
# Expected: connection refused or timeout
```

### Step 2.3: Run the permissive-mode TDD prompt

Open a terminal and run `cx`. Hand it the following task:

```
The workspace is at /workspace. The scaffold app is in /workspace/scaffold/.

1. Install scaffold dependencies:
   cd /workspace/scaffold && poetry install

2. Confirm the baseline test passes:
   poetry run pytest -v
   Expected: 1 test passes (test_health_returns_ok)

3. Create a git worktree:
   git worktree add /workspace/.worktrees/validate-permissive -b feat/validate-permissive main

4. TDD: add uptime_seconds to the GET /health response.
   Working inside the worktree's scaffold/:

   a. Write a failing test in tests/test_health.py:
      def test_health_includes_uptime(client):
          body = client.get("/health").json()
          assert "uptime_seconds" in body
          assert isinstance(body["uptime_seconds"], float)

   b. Run it — confirm it fails.

   c. Implement in main.py:
      - Add APP_START_TIME = time.time() at module level
      - Return {"status": "ok", "uptime_seconds": time.time() - APP_START_TIME}
      - Update return type annotation to dict[str, str | float]

   d. Run both tests — both must pass.

5. Run: poetry run ruff check . && poetry run pytest -v

6. Commit from inside the worktree:
   git add scaffold/main.py scaffold/tests/test_health.py
   git commit -m "feat(scaffold): add uptime_seconds to health response"
```

### Step 2.4: Observe the feedback loop

What a working permissive-mode Claude will do autonomously — no "Allow tool?" at any point:

- [ ] `poetry install` completes
- [ ] Baseline (1 test) passes
- [ ] Worktree created
- [ ] Failing test written and confirmed red
- [ ] Implementation: `APP_START_TIME = time.time()` at module level; handler returns it
- [ ] Both tests pass
- [ ] `ruff check .` clean
- [ ] Conventional commit made

---

## Phase 3: Apply to `python-fastapi-poc` (after Phase 2 passes)

Once the template is proven in isolation:

- [ ] Copy `.devcontainer/` from `tool-belt/devcontainer-templates/python-fastapi/` into `python-fastapi-poc/`
- [ ] Remove the `claude.zsh` bind mount from the existing `devcontainer.json` (it is now baked)
- [ ] Extend `init-firewall.sh` with project-specific outbound if needed (e.g. Loki, Sentry)
- [ ] Rebuild the devcontainer
- [ ] Run `type cx` inside — confirm alias active
- [ ] Run `cx -p "what is 2+2"` — confirm no permission prompts

---

## Success Criteria

| Check | Expected |
|-------|----------|
| `type cx` in container | `cx is an alias for "claude --dangerously-skip-permissions"` |
| `ch` shows menu | All aliases listed |
| `curl https://pypi.org/...` | HTTP 200 |
| `curl https://example.com` | Blocked |
| Baseline scaffold test | 1 PASS |
| Phase 2 Claude session | Zero permission prompts, all steps complete |
| Git log after Phase 2 | Shows `feat(scaffold)` commit |
