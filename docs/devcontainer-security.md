# Devcontainer Architecture

## Purpose

The devcontainer exists **primarily as an isolation environment for Claude Code**
running in autonomous or semi-autonomous mode. It gives Claude a sandboxed Linux
shell with the full development toolchain — Python, Poetry, Node, just, zsh — while
keeping it separated from the host filesystem and network.

This is the key design principle: **the container is for Claude, not for Docker.**

---

## What the devcontainer can do

| Capability | Available | Notes |
|---|---|---|
| Lint + type check | ✓ | `just backend-check` |
| Unit tests | ✓ | `just backend-test-fast` — no DB needed |
| Frontend lint + build | ✓ | `just frontend-check` |
| Frontend Vitest unit tests | ✓ | `just frontend-test` |
| Code editing, git, Claude Code | ✓ | Full toolchain available |
| Integration tests | ✗ | Requires Docker — see below |
| Performance tests | ✗ | Requires Docker (testcontainers) |
| Observability E2E | ✗ | Requires full Docker Compose stack |
| Playwright E2E | ✗ | Requires backend + frontend running on host |
| `just backend-test` | ✗ | Will fail — no Docker socket |
| `just ci` | ✗ | Will fail — includes integration + e2e |
| Any `docker` command | ✗ | Docker CLI is not installed |

---

## Why Docker is not available inside the container

Docker support was deliberately removed after a sustained attempt to make it work.
The approach tried was **Docker-outside-of-Docker (DooD)** via a Tecnativa socket
proxy sidecar. The problems encountered, in order:

1. **PermissionError on the Docker socket.** The `entrypoint.sh` gosu privilege
   drop runs after the firewall, but the socket GID remapping was operating on
   `/var/run/docker.sock` which is absent inside the container (only the proxy
   sidecar mounts it). The devcontainer user never had socket access.

2. **Testcontainers wait strategy blocked.** `PostgresContainer._connect()` uses
   `ExecWaitStrategy` which calls `docker exec psql` inside the started container.
   The proxy was configured with `EXEC=0` (security boundary). This caused a 403
   on every connection attempt. A `LogMessageWaitStrategy` subclass fixed this, but
   surfaced the next problem.

3. **Network topology.** Testcontainers starts the PostgreSQL container on the host
   daemon. The connection URL resolves to `localhost:PORT` — but inside the
   devcontainer, `localhost` is the container itself, not the host.
   `TESTCONTAINERS_HOST_OVERRIDE=host.docker.internal` was set, but `host.docker.internal`
   is not reliably available in all Docker Desktop configurations and failed in the
   `--firewall` network mode.

4. **Firewall incompatibility.** In `--firewall` mode, iptables rules block all
   outbound traffic except the allowlist. The Docker daemon and testcontainers
   communicate over loopback, but the proxy's TCP endpoint
   (`tcp://docker-socket-proxy:2375`) was on the Docker bridge network — not
   loopback — and was blocked.

The cumulative complexity of maintaining this plumbing outweighed the benefit.
The test pyramid already draws a clean boundary: logic is tested cheaply with unit
tests (no Docker needed), and DB-touching code is tested on the host where Docker
is native and reliable.

---

## Test pyramid and the container boundary

```
                     ┌──────────────────────────────────┐
                     │  Playwright E2E  (host only)      │
                     ├──────────────────────────────────┤
                     │  Backend obs. E2E  (host only)    │
                     ├──────────────────────────────────┤
                     │  Backend perf  (host only)        │
                     ├──────────────────────────────────┤
                     │  Backend integration  (host only) │
  CONTAINER CEILING →├──────────────────────────────────┤
                     │  Frontend Vitest  ✓ container     │
                     ├──────────────────────────────────┤
                     │  Backend unit  ✓ container        │
                     ├──────────────────────────────────┤
                     │  Lint & type check  ✓ container   │
                     │  (ruff, basedpyright, eslint)     │
                     └──────────────────────────────────┘
```

Everything at or below the **container ceiling** runs inside the devcontainer.
Everything above it requires Docker and must run on the host.

---

## What Claude should do inside the container

When `DEVCONTAINER=true` is set (injected by `devcontainer.json`):

- Run `just container-ci` — the single command that runs everything safe in the container:
  lint, type check, unit tests, frontend check, and frontend unit tests
- Write code, commit, push — full git access is available
- **Never** attempt `docker`, `docker compose`, `just backend-test`,
  `just backend-perf`, `just backend-e2e`, `just frontend-e2e`, or `just ci`
- If a test failure needs the integration suite, **stop and tell the user** to
  run `just backend-test` from a host terminal

---

## Security hardening

| Mechanism | Detail |
|---|---|
| Non-root user | Runs as `dev` (UID 1000) via gosu privilege drop |
| UID/GID injection | entrypoint.sh remaps to host user's UID so file ownership is correct |
| Optional egress firewall | `--firewall` mode enables iptables allowlist via `firewall.sh` |
| Supply-chain pinning | Python base image pinned to SHA256; all tools pinned to exact versions with checksums |
| npm safety | `NPM_CONFIG_IGNORE_SCRIPTS=true`, `NPM_CONFIG_MINIMUM_RELEASE_AGE=1440` |
| Poetry venv guard | entrypoint.sh warns if `POETRY_VIRTUALENVS_IN_PROJECT=true` is set (breaks just recipes) |

---

## Files

| File | Role |
|---|---|
| `.devcontainer/Dockerfile` | Image definition: Python 3.12, Node 22, Poetry, just, zsh, Claude Code |
| `.devcontainer/devcontainer.json` | IDE config: mounts, env vars, extensions, port forwarding |
| `.devcontainer/docker-compose.yml` | Compose wrapper: workspace bind mount, sleep-infinity command |
| `.devcontainer/entrypoint.sh` | UID/GID injection, Poetry venv validation, optional firewall, gosu privilege drop |
| `.devcontainer/firewall.sh` | iptables egress filter (firewalled mode only) |
| `.devcontainer/firewall-allowlist.txt` | Allowed outbound domains for autonomous mode |
| `.devcontainer/.dockerignore` | Scopes build context to `.devcontainer/` files only |
