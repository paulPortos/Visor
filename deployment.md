# Deployment Guide

Deploy Visor as a Python web service and a static frontend, backed by PostgreSQL and Redis. The steps below apply to managed platforms, virtual machines, or container-based infrastructure.

## 1. Provision services

| Component | Requirement |
| --- | --- |
| Backend | Python runtime compatible with `server/requirements.txt`, with HTTP and WebSocket support |
| Frontend | Node.js build environment and static hosting |
| Database | PostgreSQL reachable from the backend |
| Channel layer | Redis reachable from all backend instances |
| Public endpoints | HTTPS for the frontend and backend, with WSS support for WebSockets |

The examples use `app.example.com` for the frontend and `api.example.com` for the backend. Replace these with your deployment's hostnames. Allow backend outbound connections to GitHub, Google Gemini, and any enabled email service.

## 2. Configure the backend

Set the following environment variables on the backend service. Use the database provider's PostgreSQL connection URL and TLS requirements.

```dotenv
DJANGO_SECRET_KEY=<generated-secret>
DJANGO_DEBUG=False
DJANGO_ALLOWED_HOSTS=api.example.com
FRONTEND_URL=https://app.example.com
CORS_ALLOWED_ORIGINS=https://app.example.com

DATABASE_URL=postgresql://<user>:<password>@<host>:5432/<database>
DATABASE_SSL_REQUIRE=True
REDIS_URL=redis://<host>:6379/0

GITHUB_CLIENT_ID=<oauth-client-id>
GITHUB_CLIENT_SECRET=<oauth-client-secret>
GITHUB_CALLBACK_URL=https://api.example.com/auth/github/callback/
GITHUB_TOKEN_ENCRYPTION_KEY=<generated-fernet-key>

GEMINI_API_KEY=<google-api-key>
GOOGLE_API_KEY=<google-api-key>
```

`GEMINI_API_KEY` is used by the Senior Dev and Project Manager agents; `GOOGLE_API_KEY` is used by Scrum Live. Both may use the same credential if it has access to the required models. Configure `SR_DEV_AGENT_MODEL` and `PROJECT_MANAGER_AGENT_MODEL` for models available to your account; Scrum Live currently sets its model in `server/scrum/consumers.py`.

Set `DATABASE_SSL_REQUIRE` according to your database's TLS policy. Use the Redis connection URL supplied by your service, including authentication and `rediss://` when TLS is required. Redis provides a shared channel layer across backend processes.

After installing the backend dependencies, generate the two application keys:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store secrets in your hosting environment's secret manager. Keep both keys stable across releases; existing encrypted GitHub tokens depend on the Fernet key. Optional email, GitHub App, and agent settings are listed in [server/env.example](server/env.example).

## 3. Deploy the backend

Set the service working directory to `server/` and install dependencies:

```bash
pip install -r requirements.txt
```

Run database migrations once per release, before starting the new application version:

```bash
python manage.py migrate --noinput
python manage.py check
```

Start the ASGI application with Daphne:

```bash
python -m daphne -b 0.0.0.0 -p "$PORT" config.asgi:application
```

Set `PORT` to the listening port assigned by your host. On a virtual machine, configure a process manager to keep Daphne running. Configure the host's ingress or reverse proxy to terminate HTTPS, forward HTTP and WebSocket traffic to Daphne, and allow long-lived WebSocket connections.

Use `/api/v1/health/` as the service health check. It returns `204 No Content` and does not check database or external-service connectivity.

## 4. Configure GitHub OAuth

Create or update your GitHub OAuth application with:

| Setting | Value |
| --- | --- |
| Homepage URL | `https://app.example.com` |
| Authorization callback URL | `https://api.example.com/auth/github/callback/` |

The callback must match `GITHUB_CALLBACK_URL`. Login starts at the backend's `/auth/github/login/` endpoint and redirects to the frontend's `/login` route after authentication.

## 5. Deploy the frontend

Set the build working directory to `client/` and configure these build-time variables:

```dotenv
VITE_API_BASE_URL=https://api.example.com
VITE_API_VERSION=v1
VITE_WS_BASE_URL=
```

Leave `VITE_WS_BASE_URL` blank to derive the WebSocket URL from the API URL, or set it explicitly when WebSockets use a separate endpoint. Only public configuration belongs in `VITE_` variables.

Install and build:

```bash
npm ci
npm run build
```

Publish `client/dist/` as the static site root. Configure the host to serve `index.html` for application routes such as `/login`, `/home`, and `/projects/1`, while serving static assets normally. Rebuild the frontend whenever its environment variables change.

## 6. Verify the deployment

```bash
curl -I https://api.example.com/api/v1/health/
# Expected: 204

curl -i https://api.example.com/api/v1/projects/
# Expected without authentication: 401
```

Open the frontend and verify GitHub login, repository import, a Senior Dev session, and Scrum Live audio and WebSocket communication. Refresh a nested frontend route to confirm routing works. Check backend logs for database, Redis, or AI-provider errors.

For subsequent releases, back up PostgreSQL before schema changes, apply migrations once, deploy the backend, and publish the rebuilt frontend. Update OAuth, allowed-host, and CORS settings whenever public domains change.
