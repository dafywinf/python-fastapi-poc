# Other Recommendations

This document captures additional recommendations beyond tooling, linting, and testing. These are mostly about making the repository cleaner as a learning project and clearer as a reference implementation.

## Goal

The repo already has enough structure and enough tooling to be useful. The next level of improvement is not just more checks. It is clarity:
- clarity of purpose
- clarity of architecture
- clarity of conventions
- clarity of what the project is trying to teach

## 1. Define the teaching goal of the repository

Right now the project is trying to do several things at once:
- demonstrate FastAPI patterns
- demonstrate Vue patterns
- show testing
- show observability
- act like a realistic full-stack app

That is useful, but it also creates ambiguity.

I would add a short document that answers:
- Is this repo meant to model production-ready patterns?
- Is it meant to model pragmatic small-app patterns?
- Which parts are intentionally simplified?
- Which parts should be treated as best-practice examples?
- Which parts are still transitional or experimental?

This helps prevent readers from copying accidental patterns as if they were intentional standards.

## 2. Add architecture conventions

Short conventions docs would make this repo much stronger as a teaching tool.

Good topics:
- when to use local component state
- when to use Pinia
- where server-state logic belongs
- when to create a composable
- when to create a reusable component
- how API modules should be structured
- where validation belongs
- how backend services should handle side effects

These do not need to be long. Short, explicit rules are enough.

## 3. Add ADRs for important decisions

Use a lightweight Architecture Decision Record pattern for major choices.

Good candidates:
- sync FastAPI + sync SQLAlchemy
- current auth token strategy
- Redis-backed OAuth state handling
- PrimeVue adoption
- Pinia usage
- Vue Query adoption

This makes the repo better for learning because it explains not only what the code is, but why the structure exists.

## 4. Add a design-system or UI-usage guide

If PrimeVue is adopted, the repo should still define its own usage rules.

Recommended topics:
- approved component patterns
- spacing and layout tokens
- typography rules
- status semantics
- dialog behavior
- button hierarchy
- table behavior

Without this, a UI library can still devolve into inconsistent page-by-page usage.

## 5. Generate frontend API types from the backend

The frontend currently maintains its own types for backend payloads.

This is fine at small scale, but it creates drift risk in a repo that is supposed to model good full-stack practice.

Recommended direction:
- generate types from FastAPI OpenAPI output
- or add a documented step for synchronizing API contracts

This is especially useful if the repo continues to grow in both backend and frontend scope.

## 6. Add seeded demo data and stable fixtures

A learning repo gets much better when the app can be run with predictable data.

Recommended additions:
- seed routines
- seed sequences
- seed execution history
- documented local demo accounts or auth flows

Benefits:
- easier local review
- better test repeatability
- better screenshots and examples
- better DX for new readers

## 7. Add a golden-path developer workflow doc

The repo would benefit from a short "how to work in this codebase" guide.

Recommended topics:
- how to start the stack
- how to run checks
- how to add a backend endpoint
- how to add a frontend screen
- how to add tests
- how to decide where new code belongs

This improves both onboarding and consistency.

## 8. Improve dependency boundaries in the frontend

The frontend currently mixes several concerns inside views.

I would make the project boundaries more explicit:
- primitive UI components
- domain-specific components
- composables
- stores
- API clients
- route-level pages

Even before a large refactor, documenting these layers would help.

## 9. Add a staged refactor roadmap

The project is at the point where improvement should be sequenced deliberately.

A roadmap would help prevent:
- partial migrations
- duplicated old/new patterns
- mixed conventions
- cleanup work that never gets finished

Good roadmap sections:
- backend invariant fixes
- frontend state cleanup
- shared API client
- PrimeVue migration
- form validation cleanup
- test harness cleanup

## 10. Add a "known weaknesses" section

This is especially useful in an educational repo.

Examples:
- current frontend duplication
- underuse of Pinia
- transitional CSS approach
- backend scheduler invariants still need tightening

This keeps the repo honest and makes it much more useful for learners.

## Suggested highest-value non-tooling additions

If I were prioritizing, I would do these first:

1. architecture conventions doc
2. ADRs for major technology and architecture choices
3. design-system or UI-usage guide
4. generated or synchronized API contract types
5. staged refactor roadmap

## Bottom line

The repo does not mainly need more tools. It needs stronger explicit standards.

That means:
- clearer intent
- clearer conventions
- clearer architectural boundaries
- clearer migration plans

Those changes would make the project much more valuable as a long-term learning resource.
