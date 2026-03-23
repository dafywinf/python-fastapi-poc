# Recommended Frontend Stack

This document recommends a stronger frontend implementation and testing stack for this repository if the goal is to turn it into a better Vue.js learning-pattern project.

## Goal

The current frontend is readable and test-covered, but it relies too heavily on:
- page-local state
- duplicated API logic
- repeated CSS and hand-built UI primitives
- view-level orchestration for fetch/mutate/dialog flows

The stack below is intended to improve:
- architecture
- maintainability
- testing quality
- consistency
- instructional value

## Recommended Core Stack

### UI component system

Use:
- PrimeVue

Why:
- replaces repeated custom buttons, dialogs, tables, inputs, selects, and feedback components
- reduces CSS duplication
- gives the app a clearer component system
- lets the project focus more on domain behavior than rebuilding generic UI primitives

Recommended first components:
- `Button`
- `Dialog`
- `ConfirmDialog`
- `DataTable`
- `InputText`
- `Textarea`
- `Checkbox`
- `Select`
- `Toast`

## State and data architecture

### App state

Use:
- Pinia

Why:
- the repo already installs it
- auth state should live in a real store, not a module-level composable ref
- shared UI/application state is easier to reason about in stores

Recommended first store:
- `auth` store

Optional later stores:
- UI preferences
- filter state that is genuinely app-wide

### Server state

Use:
- `@tanstack/vue-query`

Why:
- removes a lot of repetitive fetch/loading/error/refetch logic
- gives better patterns for query caching and mutation invalidation
- improves CRUD and polling flows
- is a better long-term teaching pattern than ad hoc per-view `ref` state for server data

Recommended first use cases:
- sequences list/detail
- routines list/detail
- execution history
- active executions polling

## Validation and forms

Use:
- `zod`
- `vee-validate`

Why:
- adds schema-driven validation on the frontend
- makes forms more declarative and testable
- creates better parity with backend validation concepts

Recommended first forms:
- sequence create/edit
- routine create/edit
- action create/edit

## Networking layer

### Shared API client

Use:
- one shared `api/client.ts`

Why:
- centralizes token injection
- centralizes JSON parsing
- centralizes error handling
- centralizes `204` handling and request defaults

The current duplication in resource-specific API files is one of the clearest structural weaknesses in the frontend.

Recommended pattern:
- `client.ts` handles transport concerns
- resource files like `sequences.ts` and `routines.ts` only describe endpoints and payload types

## Testing stack

### Unit and component testing

Keep:
- Vitest
- Vue Test Utils

Why:
- already appropriate for Vue 3
- fast and effective for component behavior testing

Recommended improvements:
- eliminate router warnings from tests
- test through user-visible behavior
- reduce mocking at the module boundary when integration-style component tests are more useful

### API mocking

Use:
- MSW (`msw`)

Why:
- better than repeatedly mocking API modules by hand
- makes tests behave more like the real app
- supports both unit/component tests and browser/E2E scenarios

Recommended first use:
- replace direct API-module mocks in component tests where practical

### End-to-end testing

Keep:
- Playwright

Why:
- already the right choice
- strong fit for real user flows and auth/navigation testing

Recommended improvements:
- add stable fixtures and seeding helpers
- improve test isolation
- cover authenticated flows more systematically

### Accessibility testing

Use:
- `vitest-axe`
- `@axe-core/playwright`

Why:
- helps the repo teach accessible UI patterns
- catches regressions early once PrimeVue components are introduced

Recommended first use:
- core pages
- dialogs
- forms
- tables

### Visual regression testing

Optional:
- Playwright screenshot assertions

Why:
- useful after a PrimeVue migration
- helps catch UI regressions in shared components and layout changes

This is lower priority than the rest.

## Styling and theming

Use:
- PrimeVue theming
- CSS variables for app tokens

Why:
- prevents further page-local style drift
- helps define a consistent design language
- keeps custom styling lightweight and intentional

Recommended token categories:
- colors
- spacing
- typography
- border radius
- elevation
- status colors

## Suggested final stack

If I were upgrading this repo for best-practice implementation and testing, I would choose:

- PrimeVue
- Pinia
- `@tanstack/vue-query`
- `zod`
- `vee-validate`
- shared `api/client.ts`
- Vitest
- Vue Test Utils
- MSW
- Playwright
- `vitest-axe`
- `@axe-core/playwright`

## Priority order

### Phase 1

- Introduce shared `api/client.ts`
- Convert auth to a Pinia store
- Clean up auth-aware UI behavior

### Phase 2

- Introduce PrimeVue for repeated primitives
- Remove duplicated page-level CSS
- Standardize dialogs, buttons, inputs, and tables

### Phase 3

- Introduce Vue Query for server state
- Refactor views to use query/mutation hooks instead of manual request orchestration

### Phase 4

- Add `zod` and `vee-validate`
- Refactor forms to schema-driven validation

### Phase 5

- Introduce MSW
- Improve component tests to rely less on direct API-module mocks
- Add accessibility checks

## Bottom line

The most important additions are not "more tools", but the right missing layers:
- a real state architecture
- a shared transport layer
- a real component system
- better form validation
- better test realism

PrimeVue is a good choice here, but it should be paired with Pinia, a shared API client, and better data-flow/testing patterns. Otherwise the repo will still carry the same architectural duplication underneath a nicer UI layer.
