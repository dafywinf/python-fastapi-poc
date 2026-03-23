# Codex Review Archive

This directory now holds the review and recommendation documents that still make
sense as long-term archive material.

The temporary `frontend-codex/` comparison phase is over and that directory has
been removed from the repo. The implementation-bridge docs that only existed to
compare against that temporary frontend have been trimmed from this archive.

## Keep These

### [01-claude-review-brief.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/01-claude-review-brief.md)

Full external-review prompt.

Use for:
- broad architecture review
- deep learning-pattern critique
- detailed backend and frontend assessment

### [02-claude-review-brief-short.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/02-claude-review-brief-short.md)

Shorter external-review prompt.

Use for:
- quick follow-up reviews
- chat contexts with tighter prompt budgets

### [03-claude-review-brief-pr-style.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/03-claude-review-brief-pr-style.md)

Findings-first PR-style review prompt.

Use for:
- severity-ordered critiques
- bug and regression hunting
- stricter review passes

### [05-codex-review-findings.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/05-codex-review-findings.md)

Original baseline critique of the repo.

Use for:
- understanding the starting point
- comparing old weaknesses to the current codebase

### [06-recommended-frontend-stack.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/06-recommended-frontend-stack.md)

General frontend stack recommendations.

Use for:
- understanding why the repo moved toward Pinia, PrimeVue, stronger testing, and shared abstractions

### [07-recommended-linting-and-quality-gates.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/07-recommended-linting-and-quality-gates.md)

General tooling and quality-gate recommendations.

Use for:
- linting and formatting standards
- CI and local quality-bar decisions

### [08-other-recommendations.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/08-other-recommendations.md)

Broader repo-positioning and standards notes.

Use for:
- teaching-value improvements
- repo conventions
- longer-term cleanup ideas

### [11-backend-api-contract-for-frontend.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/11-backend-api-contract-for-frontend.md)

Frontend-facing summary of the backend API surface.

Use for:
- grounding frontend work in the actual backend contract
- checking route and payload assumptions

### [20-final-compare-and-contrast.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/20-final-compare-and-contrast.md)

Final implementation-side compare-and-contrast after the cleanup work landed.

Use for:
- checking what changed from the original critique
- reviewing whether the repo now qualifies as gold-standard

## Suggested Default

If you want one prompt for an external reviewer, start with:
[03-claude-review-brief-pr-style.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/03-claude-review-brief-pr-style.md)

If you want the “before vs now” pair, use:
1. [05-codex-review-findings.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/05-codex-review-findings.md)
2. [20-final-compare-and-contrast.md](/Users/dafywinf/Development/git-hub/python-fastapi-poc/docs/codex-reviews/20-final-compare-and-contrast.md)

## Removed

The following docs were trimmed because they only made sense while
`frontend-codex/` existed as a temporary comparison app:

- the replacement-frontend spec
- the portable implementation brief
- the “before/after” implementation bridge docs for TanStack Query, fat views,
  Pinia auth, PrimeVue, forms, shared API client, testing, and main-frontend catch-up
