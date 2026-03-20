# Google OAuth2 Setup Guide

This guide walks through creating a Google OAuth2 application, configuring the required
environment variables, and verifying the login flow end-to-end.

---

## 1. Create a Google Cloud Project

1. Go to [Google Cloud Console](https://console.cloud.google.com/).
2. Click **Select a project** → **New Project**.
3. Give the project a name (e.g. `fastapi-poc`) and click **Create**.

---

## 2. Enable the Google+ API (People API)

1. In the left menu, go to **APIs & Services → Library**.
2. Search for **"Google People API"** and click **Enable**.

---

## 3. Configure the OAuth Consent Screen

1. Go to **APIs & Services → OAuth consent screen**.
2. Select **External** and click **Create**.
3. Fill in the required fields:
   - **App name** — e.g. `FastAPI POC`
   - **User support email** — your Google account email
   - **Developer contact information** — same email
4. Click **Save and Continue** through the Scopes and Test Users steps (no changes needed for local dev).
5. Click **Back to Dashboard**.

> **Note:** While in **Testing** status, only the email addresses added as Test Users can log in.
> Add your own Google account under **OAuth consent screen → Test users**.

---

## 4. Create OAuth2 Credentials

1. Go to **APIs & Services → Credentials**.
2. Click **Create Credentials → OAuth client ID**.
3. Set **Application type** to **Web application**.
4. Under **Authorised redirect URIs**, add:
   ```
   http://localhost:8000/auth/google/callback
   ```
5. Click **Create**.
6. Copy the **Client ID** and **Client Secret** — you will need them in the next step.

---

## 5. Configure Environment Variables

Edit (or create) the `.env` file in the project root. Copy `.env.example` as a starting point:

```bash
cp .env.example .env
```

Then fill in your credentials:

```env
# Required — copy from Google Cloud Console → Credentials
GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-client-secret>

# URLs — leave as-is for local development
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000

# Enable POST /auth/token for local development (needed to run E2E tests).
# Set false in production — Google OAuth is the intended auth method.
ENABLE_PASSWORD_AUTH=true
```

The other required variables are already in `.env.example`.

---

## 6. Start the Stack

```bash
just platform-up   # Start PostgreSQL (and optionally Prometheus/Loki/Grafana)
just bootstrap     # Apply Alembic migrations (creates the users table)
just dev-up        # Start backend (:8000) + frontend (:5173)
```

---

## 7. Verify the Login Flow

1. Open `http://localhost:5173` in a browser.
2. Click **Sign in with Google** in the navigation bar (or visit `/login`).
3. You are redirected to Google's consent screen.
4. Approve the consent → Google redirects to `http://localhost:8000/auth/google/callback`.
5. The backend exchanges the code, upserts your user record, and redirects to
   `http://localhost:5173/auth/callback?token=<jwt>`.
6. The SPA stores the token in `localStorage` and navigates to `/sequences`.
7. Your email should now appear in the navigation bar.

---

## Architecture Notes

### In-memory CSRF state store

The `state` parameter (CSRF protection) is stored in a Python dictionary in memory.
This means the application **must run as a single worker process** — the default
for `just backend-dev` (`uvicorn --workers 1`).

If you scale to multiple workers, the state verification will fail intermittently
because different workers will not share the dictionary. For multi-worker deployments
the state store would need to be moved to Redis or another shared store.

### JWT passed as a query parameter

After a successful OAuth callback, the backend redirects the browser to
`/auth/callback?token=<jwt>`. The SPA reads the token from the query string and
stores it in `localStorage`. This is a deliberate POC simplification — in production
you would set an `HttpOnly` cookie instead to prevent the token from being readable
by JavaScript.

### Vite proxy requirement

When running the Vite dev server, the `/auth` route **must** be proxied to the
FastAPI backend with no `bypass` function. A bypass would serve the SPA shell for
browser navigations (like OAuth redirects), preventing the backend from ever
receiving the request. The `vite.config.ts` proxy is already configured correctly —
do not add an HTML bypass to the `/auth` rule.

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Clicking "Sign in with Google" does nothing | `GOOGLE_CLIENT_ID` is empty | Set `GOOGLE_CLIENT_ID` in `.env` and restart the backend |
| `redirect_uri_mismatch` error on Google | Redirect URI not registered | Add `http://localhost:8000/auth/google/callback` to Authorised redirect URIs in Google Cloud Console |
| `access_denied` — "This app is in testing mode" | Your account is not a test user | Add your Google account under **OAuth consent screen → Test users** |
| `502 Bad Gateway` after callback | Backend can't reach Google's token endpoint | Check network / firewall; ensure Docker and the backend can reach the internet |
| Login succeeds but user email doesn't appear in navbar | Token not stored | Check browser DevTools → Application → Local Storage for `access_token` key |
