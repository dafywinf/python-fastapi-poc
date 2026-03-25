# Git Workflow & Conventions

## Starting New Work

When asked to start a new feature or work on a task, follow this sequence:

1. `git checkout main`
2. `git pull origin main`
3. `git checkout -b type/short-description`

Never work directly on `main`.

## Branch Naming

- **Convention:** `type/short-description` (e.g., `feat/user-auth`, `fix/login-bug`)
- **Allowed Types:** `feat`, `fix`, `refactor`, `docs`, `chore`

## Conventional Commits

- **Format:** `type(scope): description`
- **Rule:** Use lowercase for the type and description. No period at the end.
- **Types:**
  - `feat`: A new feature
  - `fix`: A bug fix
  - `docs`: Documentation only changes
  - `refactor`: A code change that neither fixes a bug nor adds a feature
  - `test`: Adding missing tests or correcting existing tests
  - `chore`: Updating build tasks, package manager configs, etc.

## Commit Message Rules

- **Never** include a `Co-Authored-By` trailer in any commit message.

## Workflow Rules

- Before pushing, always run `just ci` on the **host** (not inside the devcontainer) to ensure all tests pass — testcontainers requires Docker which is only available on the host.
- Use atomic commits (one logical change per commit).
- Always include an Allure report decorator in test files.
- **Before raising a PR, squash commits into a single logical commit.**
  ```bash
  git rebase -i origin/main
  ```
  Mark all commits except the first as `squash` (or `s`), then write a single conventional commit message summarising the change.

## Mandatory Pre-Push / Pre-PR Gate

Before pushing or raising a PR you **must** boot the full solution and verify all service logs are clean. Steps in order:

1. **Start the platform** — `just platform-up`
2. **Start backend + frontend** — `just dev-up` (backgrounds both; confirms healthy)
3. **Check all logs** for errors or warnings:
   - Run `just dev-logs` and scan for errors or Vue warnings
   - Docker: `docker compose logs --tail=20` — confirm no container restart loops or unhealthy states
5. **Open the UI** at `http://localhost:5173` and manually verify the page loads and the sequence table renders
6. **Run the full CI gate** — `just ci`
7. Only after all of the above pass: push and raise the PR.
