# Google OAuth2 Setup Guide

This guide covers the current Google OAuth2 flow used by the routines app.

## 1. Create a Google Cloud project

1. Open <https://console.cloud.google.com/>.
2. Create or select a project.
3. Enable the Google People API.

## 2. Configure the OAuth consent screen

1. Go to `APIs & Services -> OAuth consent screen`.
2. Choose `External`.
3. Fill in the required fields.
4. While the app is in testing mode, add your own Google account as a test user.

## 3. Create OAuth client credentials

1. Go to `APIs & Services -> Credentials`.
2. Create an `OAuth client ID`.
3. Choose `Web application`.
4. Add this redirect URI:

```text
http://localhost:8000/auth/google/callback
```

5. Copy the client ID and client secret.

## 4. Configure `.env`

Start from the example file:

```bash
cp .env.example .env
```

Set at least:

```env
GOOGLE_CLIENT_ID=<your-client-id>.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=<your-client-secret>
FRONTEND_URL=http://localhost:5173
BACKEND_URL=http://localhost:8000
ENABLE_PASSWORD_AUTH=true
```

`ENABLE_PASSWORD_AUTH=true` is recommended for local development because the
Playwright suite and scripted testing use `POST /auth/token`.

## 5. Start the stack

```bash
just platform-up
just bootstrap
just dev-up
```

## 6. Verify the flow

1. Open `http://localhost:5173`.
2. Click `Sign in with Google`.
3. Approve the consent screen.
4. Google redirects to `http://localhost:8000/auth/google/callback`.
5. The backend exchanges the code, upserts the user row, creates a JWT, and redirects to:

```text
http://localhost:5173/auth/callback#token=<jwt>
```

6. The SPA stores the token and redirects to `/routines`.
7. You should now see authenticated UI controls and be able to open `/users`.

## Important Notes

### Token transport uses the URL fragment

The token is returned in the URL fragment, not the query string:

```text
/auth/callback#token=<jwt>
```

That keeps it out of server access logs and out of the request sent back to the
backend.

### `/users` is authenticated

The users page is no longer public. You must be signed in to access it.

### `/auth` must stay proxied to the backend

In Vite development mode, `/auth` browser navigations must hit the backend, not
the SPA shell. Do not add an HTML bypass for `/auth` in `vite.config.ts`.

### CSRF state is in-memory

The Google OAuth `state` store currently lives in backend memory. That means the
backend should run as a single worker unless the state store is moved to shared
infrastructure.

## Troubleshooting

| Symptom | Likely cause | Fix |
|---------|--------------|-----|
| Sign-in button returns an app error immediately | Missing Google credentials | Set `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`, then restart the backend |
| `redirect_uri_mismatch` on Google | Wrong redirect URI in Google Cloud | Add `http://localhost:8000/auth/google/callback` exactly |
| `access_denied` on callback | Account not listed as a test user | Add your Google account to the OAuth consent screen test users |
| Redirect succeeds but app is still logged out | Token fragment not stored | Check `localStorage` for `access_token` in browser devtools |
| `/users` redirects to `/login` | Not authenticated | Complete Google sign-in or inject a dev token via `POST /auth/token` |
