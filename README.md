# ImageTools

A self-hosted toolbox for converting, resizing, compressing and touching up images and short videos — no third-party upload, no file ever written to disk. The server holds your images in memory for the length of a request, then forgets them.

Run it on your own server, behind your own sign-in: only the people you grant access to can use it.

## What's inside

**Convert** — swap formats (JPEG, PNG, WebP, AVIF…) without losing resolution.

**Adjust** — resize by pixels or percentage, crop visually or by coordinates, rotate and flip.

**Compress** — shrink file size while keeping dimensions intact.

**Retouch** — add a text or image watermark with position and opacity control; a free-form generator for captions, memes and doodles on top of a photo.

**Workshop** — chain several operations into one pipeline instead of re-uploading between steps.

**Video** — crop, convert and compress clips for TikTok, Reels, Shorts, Instagram or YouTube, with ready-made aspect-ratio presets.

**PWA icon kit** — generate a manifest, Android/iOS icons, favicon and iOS splash screens in one pass.

A few tools are still being built: local blur/pixelation, auto quality enhancement, animated GIFs, AI upscaling, background removal, face restoration and auto face/plate blurring. See [`roadmap.md`](roadmap.md) for what's planned and why some things were deliberately left out.

## Stack

FastAPI + Pillow + ffmpeg on the backend, Nuxt 4 + Nuxt UI on the frontend, shipped as two Docker images (`api`, and `web` = static files + Caddy) behind the server's Caddy, with sign-in delegated to a self-hosted OAuth server.

## Running it locally

Backend only, with reload:

```bash
cd backend
uv sync
uv run uvicorn app.main:app --reload --port 8000
```

Tests:

```bash
cd backend && uv run pytest
```

API docs once running: http://localhost:8000/api/docs (tool endpoints need a signed-in session, see [Authentication](#authentication)).

## Authentication

Every page and every API call is reserved to users signed in through the self-hosted OAuth server (`OAuth-serveur`, see its `docs/adapter-une-application.md`, backend Python as OAuth client):

```
Browser ──opaque session cookie──▶ Caddy ─┬─ /*      static files (Nuxt SPA, nuxt generate)
                                           ├─ /auth/* ─▶ FastAPI (OAuth client / BFF)
                                           └─ /api/*  ─▶ FastAPI (session checked before the body is read)
```

- The FastAPI backend is the OAuth client: PKCE login, server-side sessions in SQLite, silent token refresh every 15 min (proof the user still has access), back-channel logout (`/auth/login`, `/auth/callback`, `/auth/logout`, `/auth/backchannel-logout`, `/api/me`). Code in `backend/app/auth/`, written to be identical across apps.
- The OAuth server is described by its discovery document (`OAUTH_ISSUER` + `/.well-known/oauth-authorization-server`): no endpoint URL or key in the configuration.
- The frontend is a static SPA served by Caddy: no Node and no secret in production. The API is never published. `/api/health` stays open (503 until discovery succeeded).
- The browser only holds an opaque `HttpOnly` cookie, never a token.

Before starting any profile, declare the application on the OAuth server (see [`docs/deploiement.md`](docs/deploiement.md)), grant access to the users concerned, and fill `OAUTH_ISSUER`, `OAUTH_CLIENT_ID`, `OAUTH_CLIENT_SECRET` and `PUBLIC_ORIGIN` in `.env`.

## Deployment

Full guide (in French): [`docs/deploiement.md`](docs/deploiement.md) — local run against a local OAuth server, first production deployment, updates, troubleshooting. Step-by-step production setup and updates (`make prod-deploy` on the server): [`docs/mise-en-production.md`](docs/mise-en-production.md). `make help` lists every command.

| | Command | URL |
|---|---|---|
| Dev (hot reload) | `make dev` | http://localhost:3001 (`FRONTEND_PORT`); OAuth server on :8080 |
| First production deployment | `make prod-build prod-up` | `127.0.0.1:3011` (`REMOTE_FRONTEND_PORT`), behind the server's Caddy |
| Production update | `make prod-deploy` | git pull, build, restart |

Both stacks share `docker-compose.yml` (dev adds `docker-compose.override.yml`, prod adds `docker-compose.prod.yml`; same layout as pdf-tools); only the `web` container is ever published. Every start checks `.env` first (`make env-check` / `make prod-check`). In production, the server's global Caddy needs only:

```
imagetools.example.tld {
	reverse_proxy 127.0.0.1:3011
}
```

## Configuration

Settings live in `.env` (see `.env.example`), read by whichever `docker-compose*.yml` profile is running.

| Variable | Default | Meaning |
|---|---|---|
| `FRONTEND_PORT` | 3001 | Dev stack: frontend host port |
| `REMOTE_FRONTEND_PORT` | 3011 | prod stack: frontend host port (bound to 127.0.0.1) |
| `MAX_UPLOAD_MB` | 50 | Largest accepted upload (maps to `IMGCONV_MAX_FILE_SIZE_MB`) |
| `OAUTH_ISSUER` | `http://localhost:8080` | Exact issuer of the OAuth server; endpoints and keys come from its discovery document |
| `OAUTH_CLIENT_ID` / `OAUTH_CLIENT_SECRET` | (unset) | Generated by the OAuth server when declaring the application |
| `PUBLIC_ORIGIN` | (prod only; dev: derived from `FRONTEND_PORT`) | Public origin of the app; redirect URI is `{PUBLIC_ORIGIN}/auth/callback`; also the CSRF origin |
| `IMGCONV_MAX_MEGAPIXELS` | 100 | Decompression-bomb ceiling (backend-only, not in `.env.example`) |
| `IMGCONV_REQUEST_TIMEOUT_S` | 30 | Per-request timeout (backend-only, not in `.env.example`) |
