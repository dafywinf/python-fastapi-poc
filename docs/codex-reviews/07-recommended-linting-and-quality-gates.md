# Recommended Linting and Quality Gates

This document recommends improvements to linting, formatting, type-checking, and testing quality gates for this repository.

## Goal

The current project already has a reasonable baseline:
- `ruff`
- `basedpyright`
- `eslint`
- `vitest`
- `playwright`

That is a solid starting point. The main opportunity now is not adding random tools, but tightening the feedback loops so the frontend and UI layer are held to the same standard as the backend.

## Current strengths

### Backend

The backend quality setup is already fairly strong:
- `ruff` is fast and pragmatic
- `basedpyright` in strict mode is a good choice
- pytest coverage is broad enough to support iterative cleanup

I would keep the Python side largely as-is.

### Frontend

The frontend already has:
- ESLint
- TypeScript
- Vitest
- Playwright

That is enough to build on, but not yet enough to keep the UI layer consistently clean as the project grows.

## Recommended additions

### 1. Add Prettier for frontend formatting

Use:
- `prettier`
- `eslint-config-prettier`

Why:
- creates a clearer formatting boundary for Vue, TypeScript, JSON, and Markdown
- reduces formatting noise in PRs
- brings the frontend closer to the "one obvious style" experience that `ruff format` provides on the backend

Recommended scope:
- `frontend/src`
- config files
- test files

## 2. Add Stylelint if custom CSS remains significant

Use:
- `stylelint`
- `stylelint-config-standard`
- `stylelint-config-recommended-vue`

Why:
- catches invalid CSS and inconsistent patterns
- helps keep view-scoped CSS from drifting
- useful if the repo continues to maintain custom CSS during or after PrimeVue migration

This is especially relevant because the current frontend contains a lot of repeated hand-written CSS.

## 3. Tighten TypeScript settings

Why:
- the frontend architecture currently relies on a lot of informal local state and request handling
- stricter TS settings improve confidence at those boundaries

Recommended direction:
- make `tsc --noEmit` or equivalent type-check a first-class CI step
- prefer strict compiler options where not already enabled
- avoid papering over nullable or unknown response shapes

Good targets:
- API response handling
- route params
- form state
- auth state

## 4. Treat frontend test warnings as quality issues

Current issue:
- Vitest passes, but Vue Router warnings appear during component tests

Why it matters:
- warning-filled test output lowers signal quality
- example repos should teach clean test harnesses, not normalized noise

Recommendation:
- fix the router test setup so these warnings disappear
- do not allow known warnings to linger in normal test output

## 5. Add accessibility linting and checks

Use:
- `eslint-plugin-vuejs-accessibility`
- `vitest-axe`
- `@axe-core/playwright`

Why:
- improves the instructional quality of the UI
- catches common accessibility issues in templates, dialogs, and forms
- gives better coverage once shared UI components are introduced

## 6. Add pre-commit quality gates

Use:
- `husky`
- `lint-staged`

Why:
- catches simple issues before they reach CI
- reduces noisy back-and-forth on formatting/lint failures

Recommended pre-commit scope:
- frontend lint on changed frontend files
- prettier on changed text/code files
- backend `ruff check` on changed Python files

Keep hooks fast. Do not overload pre-commit with the full test suite.

## 7. Improve CI job structure

Why:
- one monolithic quality command becomes harder to reason about as the stack grows

Recommended job split:
- backend lint/format/typecheck
- backend tests
- frontend lint/format/typecheck
- frontend unit/component tests
- frontend E2E tests
- optional accessibility job

This makes failures easier to interpret and keeps the quality pipeline easier to maintain.

## 8. Consider coverage thresholds for critical frontend code

Why:
- not for chasing percentages
- useful for protecting fragile areas as architecture gets cleaned up

Recommended scope:
- auth store/composable
- shared API client
- core CRUD composables
- critical UI flows

Use coverage thresholds narrowly and intentionally, not as a repo-wide vanity gate.

## Suggested final quality stack

### Keep

- `ruff`
- `basedpyright`
- `eslint`
- `vitest`
- `playwright`

### Add

- `prettier`
- `eslint-config-prettier`
- `stylelint`
- `eslint-plugin-vuejs-accessibility`
- `vitest-axe`
- `@axe-core/playwright`
- `husky`
- `lint-staged`

## Suggested priority order

### Phase 1

- Add `prettier`
- Clean frontend test warnings
- Make frontend type-checking more explicit in CI

### Phase 2

- Add `stylelint`
- Add pre-commit hooks with `husky` and `lint-staged`

### Phase 3

- Add accessibility linting and automated a11y checks
- Add targeted coverage thresholds for critical frontend modules

## Bottom line

The repo does not need a huge number of new quality tools. It needs a more disciplined frontend quality layer.

If I were choosing the highest-value improvements, I would do these first:
1. `prettier`
2. warning-free frontend tests
3. stricter frontend type-checking
4. `stylelint`
5. `husky` + `lint-staged`

That would make the project noticeably cleaner without turning the toolchain into noise.
