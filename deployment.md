# Deployment Guide

Visor runs as four services: a React frontend served by Nginx, a Django ASGI backend, PostgreSQL, and Redis. Docker Compose builds and starts the complete system.

## 1. Configure the application

Install Docker with Compose v2.24 or newer. From the repository root:

```bash
cp .env.example .env
```

Set these credentials in the root `.env`:

| Variable | Purpose |
| --- | --- |
| `GITHUB_CLIENT_ID` | GitHub OAuth application client ID |
| `GITHUB_CLIENT_SECRET` | GitHub OAuth application client secret |
| `GEMINI_API_KEY` | Senior Dev and Project Manager agents |
| `GOOGLE_API_KEY` | Scrum Live; defaults to `GEMINI_API_KEY` when blank |

Configure the GitHub OAuth application's homepage as `http://localhost:3000` and callback as `http://localhost:3000/auth/github/callback/`.

Leave `DJANGO_SECRET_KEY` and `GITHUB_TOKEN_ENCRYPTION_KEY` blank to generate persistent keys on first startup. When restoring an existing database, supply the original keys. Optional model and runtime settings are listed in [.env.example](.env.example) and [server/env.example](server/env.example).

Compose reads the root `.env`. The native development files `server/.env` and `client/.env.local` are excluded from Docker images.

## 2. Start the system

```bash
docker compose up --build -d --wait
```

Open **http://localhost:3000**.

| Service | Function |
| --- | --- |
| `frontend` | Builds the client and serves it through Nginx |
| `backend` | Runs migrations, then serves Django HTTP and WebSockets through Daphne |
| `postgres` | Stores application data in a persistent volume |
| `redis` | Provides the shared Channels layer with persistent Redis storage |

Startup waits for PostgreSQL and Redis to become healthy before starting the backend, then waits for the backend before starting the frontend. Nginx forwards `/api/`, `/auth/`, and `/ws/` to the backend. Database and Redis ports remain internal to the Compose network.

The frontend uses the browser's origin for API and WebSocket connections. Changing the public hostname or port does not require rebuilding frontend URLs.

## 3. Verify and operate

```bash
docker compose ps
curl -I http://localhost:3000/api/v1/health/
# Expected: 204

curl -i http://localhost:3000/api/v1/projects/
# Expected without authentication: 401

docker compose logs -f backend
```

Verify GitHub login, repository import, a Senior Dev session, and Scrum Live. Refresh a nested route such as `/home` to check frontend routing. The HTTP health endpoint checks application availability; it does not verify external integrations.

Apply code or configuration updates with:

```bash
docker compose up --build -d --wait
```

Stop the system while preserving its volumes:

```bash
docker compose down
```

PostgreSQL data, Redis data, and generated keys live in the `postgres_data`, `redis_data`, and `backend_state` volumes. Back up PostgreSQL and its application keys together before schema changes. Removing volumes deletes their data; `docker compose down -v` also removes generated keys.

## 4. Deploy on a server

Use the same Compose setup on a Docker host. Set these root `.env` values for your deployment:

```dotenv
APP_BIND_ADDRESS=0.0.0.0
APP_PORT=3000
PUBLIC_URL=https://app.example.com
DJANGO_ALLOWED_HOSTS=app.example.com,localhost,127.0.0.1,backend
POSTGRES_PASSWORD=<strong-database-password>
```

Place an HTTPS reverse proxy or load balancer in front of the frontend port, with support for WebSocket upgrades and long-lived connections. Update the GitHub OAuth homepage and callback to match `PUBLIC_URL`; the callback path remains `/auth/github/callback/`. `PUBLIC_URL` must not have a trailing slash. Changing `APP_PORT` locally updates the default URLs automatically.

The Dockerfiles can also be built as separate images for another container platform:

```bash
docker build -t visor-backend ./server
docker build -t visor-frontend ./client
```

On another orchestrator, configure Nginx's backend address and DNS resolver in [client/nginx.conf](client/nginx.conf), supply equivalent backend environment variables, and connect PostgreSQL and Redis. Attach persistent storage at `/var/lib/visor` for generated keys, or supply stable keys through the platform's secret manager. Run migrations once per release before starting multiple backend instances.

[Compose startup dependencies](https://docs.docker.com/compose/how-tos/startup-order/) and [Nginx WebSocket proxying](https://nginx.org/en/docs/http/websocket.html) describe the service readiness and proxy configuration used here.
