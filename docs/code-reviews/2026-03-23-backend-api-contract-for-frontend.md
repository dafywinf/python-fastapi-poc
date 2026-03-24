# Backend API Contract for Frontend Work

This document captures the actual backend API surface that a new frontend in this repository should build against.

This is based on the current backend route and schema code, not on aspirational design.

For the target frontend scope described in the neighboring spec docs, `sequences` are intentionally out of scope even if the backend still exposes those endpoints.

## Base assumptions

- Backend runs on `http://localhost:8000` in local development unless configured otherwise.
- Frontend should use relative URLs in dev when proxied, or a configurable backend base URL if needed.
- JWT Bearer auth is required for all write operations and some user endpoints.

## Auth model

### Password token login

Endpoint:
- `POST /auth/token`

Condition:
- only available when backend setting `ENABLE_PASSWORD_AUTH=true`

Request:
- content type: `application/x-www-form-urlencoded`
- fields:
  - `username`
  - `password`

Response on success:

```json
{
  "access_token": "jwt-string",
  "token_type": "bearer"
}
```

Failure:
- `401` with `detail`

Notes:
- frontend should not assume this endpoint always exists in production
- login screen may need to feature-detect or be environment-driven

### Google OAuth start

Endpoint:
- `GET /auth/google/login`

Behavior:
- redirects browser to Google

Frontend handling:
- this is a browser navigation, not an XHR/fetch request

### Google OAuth callback

Endpoint:
- `GET /auth/google/callback`

Backend behavior:
- validates state
- exchanges auth code
- upserts user
- redirects to frontend callback page

Redirect target shape:
- `${FRONTEND_URL}/auth/callback#token=<jwt>`

Frontend requirement:
- parse token from URL fragment
- immediately clear fragment from browser history/address bar
- persist token
- redirect user into app

## Users

### List users

- `GET /users/`
- auth: Bearer required

Response:

```ts
type UserResponse = {
  id: number
  email: string
  name: string
  picture: string | null
  created_at: string
}
```

### Current user

- `GET /users/me`
- auth: Bearer required

Response:
- `UserResponse`

Failures:
- `401` if not authenticated
- `404` if token is valid but no matching user row exists

## Routines

### Routine response shape

```ts
type ActionResponse = {
  id: number
  routine_id: number
  position: number
  action_type: string
  config: Record<string, unknown>
}

type RoutineResponse = {
  id: number
  name: string
  description: string | null
  schedule_type: string
  schedule_config: Record<string, unknown> | null
  is_active: boolean
  created_at: string
  actions: ActionResponse[]
}
```

### List routines

- `GET /routines/`
- auth: public

Response:
- `RoutineResponse[]`

### Get routine

- `GET /routines/{routine_id}`
- auth: public

Response:
- `RoutineResponse`

Failure:
- `404`

### Create routine

- `POST /routines/`
- auth: Bearer required

Request body:

```ts
type RoutineCreate =
  | {
      name: string
      description?: string | null
      schedule_type: "manual"
      schedule_config?: null
      is_active?: boolean
    }
  | {
      name: string
      description?: string | null
      schedule_type: "cron"
      schedule_config: { cron: string }
      is_active?: boolean
    }
  | {
      name: string
      description?: string | null
      schedule_type: "interval"
      schedule_config: { seconds: number }
      is_active?: boolean
    }
```

Validation notes:
- manual routines must use `schedule_config = null`
- cron routines require `schedule_config.cron`
- interval routines require `schedule_config.seconds`

### Update routine

- `PUT /routines/{routine_id}`
- auth: Bearer required

Request body:

```ts
type RoutineUpdate = {
  name?: string | null
  description?: string | null
  schedule_type?: "cron" | "interval" | "manual"
  schedule_config?: Record<string, unknown> | null
  is_active?: boolean
}
```

Important note:
- backend currently does not validate `RoutineUpdate` as strictly as `RoutineCreate`
- frontend should still validate this carefully to avoid invalid payloads

### Delete routine

- `DELETE /routines/{routine_id}`
- auth: Bearer required

Response:
- `204`

## Actions

### List actions for routine

- `GET /routines/{routine_id}/actions`
- auth: public

Response:
- `ActionResponse[]`

### Create action

- `POST /routines/{routine_id}/actions`
- auth: Bearer required

Request body:

```ts
type ActionCreate = {
  action_type: "sleep" | "echo"
  config: Record<string, unknown>
  position?: number
}
```

Action config conventions in current backend:
- `sleep` expects `config.seconds`
- `echo` expects `config.message`

Important note:
- backend appends automatically when `position` is omitted
- backend documentation implies insert-at-position behavior, but implementation is not a true insert-with-shift
- frontend should avoid assuming full insert semantics unless backend is fixed

### Update action

- `PUT /actions/{action_id}`
- auth: Bearer required

Request body:

```ts
type ActionUpdate = {
  action_type?: "sleep" | "echo"
  config?: Record<string, unknown>
  position?: number
}
```

Behavior:
- `position` triggers a swap with the action already at that position
- if no action exists at the target position, backend returns `422`

### Delete action

- `DELETE /actions/{action_id}`
- auth: Bearer required

Response:
- `204`

Behavior:
- backend compacts remaining action positions after deletion

## Routine execution

### Run now

- `POST /routines/{routine_id}/run`
- auth: Bearer required

Response:

```ts
type RunResponse = {
  execution_id: number
}
```

Status:
- `202`

Failure:
- `409` if routine is already running

### Active executions

- `GET /executions/active`
- auth: public

Response:

```ts
type ExecutionResponse = {
  id: number
  routine_id: number
  routine_name: string
  status: string
  triggered_by: string
  started_at: string
  completed_at: string | null
}
```

### Execution history

- `GET /executions/history`
- auth: public

Query params:
- `limit?: number` default `10`
- `routine_id?: number`

Response:
- `ExecutionResponse[]`

## Health and observability

### Health

- `GET /health`
- auth: public

Response:

```json
{
  "status": "ok"
}
```

### Metrics

- `GET /metrics`
- auth: public

Frontend note:
- not needed for normal product UI

## Auth summary by endpoint group

### Public reads

- `GET /health`
- `GET /routines/`
- `GET /routines/{id}`
- `GET /routines/{id}/actions`
- `GET /executions/active`
- `GET /executions/history`
- `GET /auth/google/login` as browser redirect start
- `GET /auth/google/callback` as OAuth redirect target

### Authenticated only

- `POST /auth/token`
- `GET /users/`
- `GET /users/me`
- all routine writes
- action writes
- run-now execution trigger

## Frontend implementation notes

For a new frontend:
- validate routine payloads on the client more strictly than the backend currently enforces
- treat action creation `position` carefully because backend semantics are weaker than the docs imply
- model public-read/authenticated-write behavior consistently in the UI
- support both password login and Google OAuth callback handling

## Source of truth

This document is a convenience summary.

The true source of truth remains:
- [backend/routes.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/routes.py)
- [backend/user_routes.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/user_routes.py)
- [backend/routine_routes.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/routine_routes.py)
- [backend/auth_routes.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/auth_routes.py)
- [backend/schemas.py](/Users/dafywinf/Development/git-hub/python-fastapi-poc/backend/schemas.py)
