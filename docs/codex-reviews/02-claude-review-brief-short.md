# Short Review Brief for Claude Code

Review this repo as a learning-pattern project for Vue.js and FastAPI. Treat it as a reference implementation that should teach best practices, not just a working demo.

Focus on:
1. Whether the backend architecture teaches good patterns.
2. Whether the frontend architecture teaches good patterns.
3. Where the code is acceptable for a small app but weak as a best-practices example.
4. Whether moving the frontend to PrimeVue is justified.

## Key concerns to investigate

### Backend

- `RoutineCreate` validates schedule invariants, but `RoutineUpdate` does not.
- Routine updates appear to commit invalid state before scheduler re-registration.
- Assess whether scheduler integration and side-effect handling are robust enough for a reference app.
- Assess whether the sync FastAPI + sync SQLAlchemy architecture is coherent and well demonstrated.

Relevant files:
[backend/schemas.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/schemas.py#L91)
[backend/routine_services.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/routine_services.py#L43)
[backend/scheduler.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/scheduler.py#L21)
[backend/main.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/main.py#L65)

### Frontend architecture

- Too much local view state and too little real use of Pinia.
- Auth state currently lives in a module-level ref backed by `localStorage`.
- API request logic is duplicated across modules.
- Views are too large and combine UI, data fetching, mutation orchestration, and modal state.
- Auth-aware UI behavior is inconsistent across views.

Relevant files:
[frontend/src/main.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/main.ts)
[frontend/src/composables/useAuth.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/composables/useAuth.ts#L34)
[frontend/src/api/sequences.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/api/sequences.ts#L3)
[frontend/src/api/routines.ts](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/api/routines.ts#L11)
[frontend/src/views/SequenceListView.vue](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/views/SequenceListView.vue)
[frontend/src/views/SequenceDetailView.vue](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/views/SequenceDetailView.vue)
[frontend/src/views/RoutinesView.vue](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/views/RoutinesView.vue)
[frontend/src/views/ExecutionHistoryView.vue](/Users/dafywinf/Development/git-hub/python-fastapi-poc/frontend/src/views/ExecutionHistoryView.vue)

### CSS and duplication

- There is too much repeated hand-written CSS for buttons, tables, dialogs, forms, badges, and layout.
- There is repeated view-local logic for loading, error handling, modal control, and CRUD flows.
- Assess whether this code is teaching poor frontend habits even if it is readable.

### PrimeVue

Assess whether PrimeVue is the right next step.

Specifically answer:
1. Is PrimeVue justified here?
2. Which repeated UI pieces should migrate first?
3. Which parts should stay custom and domain-specific?
4. Would PrimeVue solve only styling duplication, or also improve maintainability?
5. What architectural cleanup must happen alongside PrimeVue migration so the app does not keep the same duplicated logic underneath?

## Output format

Give me:
1. Prioritized findings with severity and file references.
2. Backend architecture critique as a learning example.
3. Frontend architecture critique as a learning example.
4. A focused section on CSS duplication and repeated frontend patterns.
5. A focused section on whether PrimeVue migration is justified.
6. A refactor roadmap in priority order.
7. A final judgment:
- good reference app
- useful but flawed learning app
- working demo with weak best-practices value

My bias is that the frontend is the weakest part:
- too much duplicated CSS
- too much repeated page logic
- weak state architecture
- not enough component-system thinking
- probably ready for PrimeVue plus stronger shared abstractions

Challenge that view if the evidence says otherwise.
