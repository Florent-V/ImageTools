# ImageTools

A self-hosted toolbox for converting, resizing, compressing and touching up images and short videos — no third-party upload, no file ever written to disk. The server holds your images in memory for the length of a request, then forgets them.

Run it on a home server, a NAS, or your own laptop. Point a browser at it from any device on your network and it just works.

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

FastAPI + Pillow + ffmpeg on the backend, Nuxt 4 + Nuxt UI on the frontend, shipped as two Docker images behind an optional Caddy reverse proxy.

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

API docs once running: http://localhost:8000/api/docs

## Deployment

Three profiles, all built on the same `docker-compose.yml` (`backend` and `frontend` services, no port or Caddy config baked in).

Copy `.env.example` to `.env` before starting any profile — that's where ports live (to avoid clashing with other projects on the same machine) and where app config is set. `.env` is gitignored.

### Dev — hot reload

```bash
make dev
```

Starts `backend` (uvicorn --reload) and `frontend` (nuxt dev) with the code mounted as a volume. Backend on `:8010` (`BACKEND_PORT`), frontend on `:3000` (`FRONTEND_PORT`).

`docker-compose.override.yml` loads automatically with a plain `docker compose`, so `make up` / `down` / `restart` / `logs` / `build` / `rebuild` (no suffix) are really aliases for this **dev** profile — distinct from `up-home` / `up-remote` below, which target the production profiles explicitly.

### Self-hosted on your LAN

```bash
make up-home
```

Adds a dedicated Caddy container as the single entry point, routing `/api/*` to the backend and everything else to the frontend. Reachable from any device on the network via the host's local IP:

```
http://<machine-lan-ip>:8080
```

Port configurable via `HOME_PORT`.

Find the local IP with `ip addr show` (Linux) or `ifconfig` (macOS). No HTTPS, no domain name — this profile assumes a trusted home network only.

### Remote server (behind an existing Caddy)

```bash
make up-remote
```

Publishes `backend` on `:8011` (`REMOTE_BACKEND_PORT`) and `frontend` on `:3010` (`REMOTE_FRONTEND_PORT`), with no Caddy container of its own — built for a server where a global Caddy already routes other Docker projects by port. Add this block to that server's existing `Caddyfile`:

```
imagetools.example.tld {
	handle /api/* {
		reverse_proxy 127.0.0.1:8011
	}
	handle {
		reverse_proxy 127.0.0.1:3010
	}
}
```

Swap in the real domain name and reload Caddy (`caddy reload` or equivalent).

For direct port access with no Caddy in front (handy for testing), set `REMOTE_API_BASE_URL` and `REMOTE_CORS_ORIGINS` in `.env` (see `.env.example`) so the frontend can call the backend cross-origin.

## Configuration

Settings live in `.env` (see `.env.example`), read by whichever `docker-compose*.yml` profile is running.

| Variable | Default | Meaning |
|---|---|---|
| `BACKEND_PORT` | 8010 | Dev stack: backend host port |
| `FRONTEND_PORT` | 3000 | Dev stack: frontend host port |
| `HOME_PORT` | 8080 | prod-home stack: Caddy host port |
| `REMOTE_BACKEND_PORT` | 8011 | prod-remote stack: backend host port |
| `REMOTE_FRONTEND_PORT` | 3010 | prod-remote stack: frontend host port |
| `REMOTE_API_BASE_URL` | (unset) | prod-remote only: backend URL the browser calls directly, for no-proxy access |
| `REMOTE_CORS_ORIGINS` | `http://localhost:3010` | prod-remote only: origin(s) the backend accepts requests from |
| `MAX_UPLOAD_MB` | 50 | Largest accepted upload (maps to `IMGCONV_MAX_FILE_SIZE_MB`) |
| `CORS_ORIGINS` | `http://localhost:3000` | Origin(s) the backend accepts cross-origin requests from |
| `IMGCONV_MAX_MEGAPIXELS` | 100 | Decompression-bomb ceiling (backend-only, not in `.env.example`) |
| `IMGCONV_REQUEST_TIMEOUT_S` | 30 | Per-request timeout (backend-only, not in `.env.example`) |
