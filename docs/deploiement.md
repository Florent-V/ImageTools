# Déploiement

ImageTools est protégé par le serveur OAuth maison (`OAuth-serveur`). Ce guide couvre :

1. [Architecture et ports](#1-architecture-et-ports)
2. [Lancer en local avec le serveur OAuth local](#2-lancer-en-local-avec-le-serveur-oauth-local)
3. [Premier déploiement en production](#3-premier-déploiement-en-production) (guide complet pas à pas et mises à jour : [`mise-en-production.md`](mise-en-production.md))
4. [Mise à jour de la production](#4-mise-à-jour-de-la-production)
5. [Commandes Make](#5-commandes-make)
6. [Dépannage](#6-dépannage)

## 1. Architecture et ports

```
Navigateur ──cookie de session opaque──▶ Caddy (conteneur web) ─┬─ /*      fichiers statiques (nuxt generate)
                                                                ├─ /auth/* ─▶ api (FastAPI, client OAuth / BFF)
                                                                └─ /api/*  ─▶ api (session vérifiée avant lecture du corps)
api ──découverte, code + PKCE, refresh──▶ serveur OAuth       serveur OAuth ──logout_token──▶ api /auth/backchannel-logout
```

- Le **backend FastAPI** est le client OAuth : il garde les jetons et la session dans SQLite (volume `api-data`),
  renouvelle les jetons toutes les 15 min (`SESSION_REVALIDATE_INTERVAL`, ce qui prouve que l'accès existe encore) et
  reçoit les logout tokens. Le navigateur ne reçoit qu'un cookie opaque (`__Host-session` en production).
- Le **front** est une SPA statique servie par Caddy : aucun Node en production, aucun secret.
- Le serveur OAuth est décrit par sa **découverte** (`<OAUTH_ISSUER>/.well-known/oauth-authorization-server`) : aucune
  URL d'endpoint ni clé n'est recopiée dans la configuration. Au démarrage, l'API vérifie que l'issuer correspond
  exactement, que PKCE S256 est supporté et que les endpoints sont en https (hors `APP_ENV=dev`).
- L'**API** ne publie aucun port : elle n'est joignable que par le conteneur `web`. `/api/health` répond 503
  tant que la découverte n'a pas réussi.

| Service | Dev (`make dev`) | Production (`make prod-up`) |
|---|---|---|
| Front ImageTools | **http://localhost:3001** (`FRONTEND_PORT`, Nuxt dev, proxy `/api` et `/auth`) | `127.0.0.1:3010` (`REMOTE_FRONTEND_PORT`, conteneur Caddy), derrière le Caddy global |
| API ImageTools | `8000` (réseau hôte, derrière le proxy de Nuxt) | réseau Docker interne uniquement |
| Serveur OAuth local | http://localhost:8080 | `https://oauth.<domaine>` |
| Mailpit (codes MFA en dev) | http://localhost:8025 | — |

## 2. Lancer en local avec le serveur OAuth local

### 2.1 Démarrer le serveur OAuth

```bash
cd ~/DevProjects/OAuth-serveur
make start          # http://localhost:8080, e-mails (codes de connexion) sur http://localhost:8025
```

### 2.2 Déclarer l'application de dev (une seule fois)

Toujours dans `OAuth-serveur` (le client ID est tiré au hasard si `--id` est omis) :

```bash
make console c='app:application:create "ImageTools (dev)" \
    --home-url=http://localhost:3001/ \
    --redirect-uri=http://localhost:3001/auth/callback \
    --backchannel-logout-uri=http://host.docker.internal:3001/auth/backchannel-logout'
```

Notez le **client ID** et le **client secret** affichés (le secret n'est affiché qu'une fois).

- La redirect URI est ouverte par le **navigateur** : `localhost:3001`.
- L'URL de back-channel logout est appelée par le **conteneur du serveur OAuth** : `localhost` y désignerait le
  conteneur lui-même, d'où `host.docker.internal` (déjà configuré dans le `compose.override.yaml` du serveur OAuth).

Puis donnez-vous l'accès :

```bash
make grant email=vous@example.com app=<client_id>
```

L'administration web (http://localhost:8080/admin) permet de faire la même chose.

### 2.3 Configurer ImageTools

```bash
cd ~/DevProjects/ImageConverter
cp .env.example .env
```

Dans `.env` :

```dotenv
FRONTEND_PORT=3001
OAUTH_ISSUER=http://localhost:8080        # valeur EXACTE de l'issuer publié par le serveur OAuth
OAUTH_CLIENT_ID=<client_id>
OAUTH_CLIENT_SECRET=<client_secret>
PUBLIC_ORIGIN=http://localhost:3001       # le redirect URI en est déduit : {PUBLIC_ORIGIN}/auth/callback
```

En dev, l'API tourne en réseau hôte : l'issuer `http://localhost:8080` doit être joignable sous ce nom exact (il est
comparé comme chaîne). Le compose de dev règle `APP_ENV=dev`, `COOKIE_SECURE=false` et un cookie `imagetools-session`
(les navigateurs n'isolent pas les cookies par port : une autre app sur localhost écraserait `session`).

Si vous changez `FRONTEND_PORT`, changez aussi `PUBLIC_ORIGIN` et les URL déclarées sur le serveur OAuth.

### 2.4 Lancer

```bash
make dev            # premier plan, Ctrl+C pour arrêter (make up : en arrière-plan, make down : arrêt)
```

Ouvrez **http://localhost:3001** : redirection vers la connexion du serveur OAuth (code de connexion dans Mailpit,
http://localhost:8025), puis retour sur ImageTools, connecté.

`make dev` vérifie d'abord `.env` (`make env-check`) et s'arrête avec un message clair s'il manque une variable.

### 2.5 À tester

| Test | Attendu |
|---|---|
| Ouvrir http://localhost:3001/crop sans être connecté | Connexion sur le serveur OAuth, puis retour sur `/crop` |
| Convertir une image, une vidéo | Fonctionne comme avant |
| Outils du navigateur : cookies, réponses | Un seul cookie `imagetools-session` opaque (HttpOnly) ; aucun jeton, aucun secret |
| `make console c="app:application:test-backchannel-logout <client_id> vous@example.com"` (dans `OAuth-serveur`) | « HTTP 200 » ; ImageTools vous renvoie à la connexion à la requête suivante |
| Retirer l'accès à l'application dans l'admin | Session fermée à la requête suivante |
| Bouton de déconnexion (en haut à droite) | Page `/logged-out` (le serveur OAuth ne publie pas d'`end_session_endpoint`) ; sa session SSO reste ouverte |
| Mettre `OAUTH_ACCESS_TOKEN_TTL=PT1M` dans le serveur OAuth et naviguer plus d'une minute | Toujours connecté (renouvellement silencieux, toutes les 15 min au plus) |

## 3. Premier déploiement en production

### 3.1 Prérequis

- Docker et Docker Compose sur le serveur.
- Le Caddy global du serveur, qui route chaque domaine vers un port local.
- Un enregistrement DNS, par exemple `imagetools.<domaine>`, vers le serveur.
- Le serveur OAuth en production (`https://oauth.<domaine>`).

### 3.2 Déclarer l'application sur le serveur OAuth

Sur le serveur, dans le dossier du serveur OAuth :

```bash
make prod-console c='app:application:create "ImageTools" \
    --home-url=https://imagetools.<domaine>/ \
    --redirect-uri=https://imagetools.<domaine>/auth/callback \
    --backchannel-logout-uri=https://imagetools.<domaine>/auth/backchannel-logout'
make prod-grant email=vous@<domaine> app=<client_id>
```

Notez le client ID et le secret. (Raccourci si vous choisissez le client ID vous-même :
`make prod-app name="ImageTools" id=imagetools url=https://imagetools.<domaine>`.)

Déclarez de préférence l'URL **publique** de back-channel logout, même si les deux applications tournent sur la même
machine.

### 3.3 Installer ImageTools

```bash
git clone <url-du-dépôt> imagetools && cd imagetools
cp .env.example .env && chmod 600 .env
```

Dans `.env` :

```dotenv
REMOTE_FRONTEND_PORT=3010
MAX_UPLOAD_MB=50
OAUTH_ISSUER=https://oauth.<domaine>      # exactement l'issuer publié, barre finale comprise s'il y en a une
OAUTH_CLIENT_ID=<client_id>
OAUTH_CLIENT_SECRET=<client_secret>
PUBLIC_ORIGIN=https://imagetools.<domaine>
```

`FRONTEND_PORT` ne sert qu'en dev.

### 3.4 Démarrer

```bash
make prod-build prod-up
```

`prod-check` (lancé automatiquement) refuse de démarrer si une variable manque ou si `PUBLIC_ORIGIN` / `OAUTH_ISSUER`
ne sont pas en `https://`. L'API refuse aussi de démarrer si l'issuer publié diffère de `OAUTH_ISSUER`.

### 3.5 Brancher Caddy

Dans le `Caddyfile` global du serveur :

```caddyfile
imagetools.<domaine> {
	reverse_proxy 127.0.0.1:3010
}
```

Le conteneur `web` (Caddy) sert les fichiers statiques et route `/api/*` et `/auth/*` vers l'API. Puis `caddy reload` (ou l'équivalent de votre
installation).

### 3.6 Vérifier

1. https://imagetools.<domaine> → connexion sur le serveur OAuth → retour sur ImageTools.
2. Sur le serveur OAuth : `make prod-console c="app:application:test-backchannel-logout <client_id> vous@<domaine>"`
   → « HTTP 200 ».
3. `make prod-ps` : `api` sans port publié, `web` sur `127.0.0.1:3010`.

## 4. Mise à jour de la production

### Nouvelle version du code

```bash
cd imagetools
make prod-deploy
```

Fait `git pull --ff-only`, reconstruit les images, redémarre les conteneurs modifiés et affiche leur état. Les
sessions des utilisateurs survivent (base SQLite dans le volume `api-data`).

### Changement de configuration seulement (`.env`)

```bash
make prod-up        # recrée les conteneurs dont l'environnement a changé, sans reconstruire
```

### Cas particuliers

| Changement | Effet | À faire |
|---|---|---|
| Nouveau client secret (régénéré sur le serveur OAuth) | Renouvellements refusés : sessions fermées au plus tard 15 min après | Mettre à jour `OAUTH_CLIENT_SECRET`, `make prod-up` |
| Rotation de la clé de signature du serveur OAuth | Rien : la clé est relue par `kid` dans le JWKS | — |
| Vider les sessions | Tous les utilisateurs se reconnectent (SSO) | `docker compose exec api rm /data/sessions.db`, puis `make prod-restart` |
| Nouveau domaine | Redirect URI refusée par le serveur OAuth | Mettre à jour l'application sur le serveur OAuth, `PUBLIC_ORIGIN`, le bloc Caddy, `make prod-up` |

### Revenir en arrière

```bash
git log --oneline -5
git checkout <commit-précédent>
make prod-build prod-up
git checkout main       # avant le prochain make prod-deploy
```

## 5. Commandes Make

`make` (ou `make help`) liste toutes les commandes.

| Commande | Rôle |
|---|---|
| `make dev` | Stack de dev au premier plan, rechargement à chaud, http://localhost:3001 |
| `make up` / `make down` / `make logs` / `make ps` | Dev en arrière-plan / arrêt / journaux / état |
| `make test` | Tests du backend (dont `tests/auth/`) |
| `make env-check` | Vérifie `.env` (variables OAuth) |
| `make prod-build prod-up` | Premier déploiement |
| `make prod-deploy` | Mise à jour : `git pull`, build, redémarrage |
| `make prod-up` | Applique un changement de `.env` |
| `make prod-logs` / `make prod-ps` | Journaux / état de la production |
| `make prod-restart` / `make prod-down` | Redémarrage sans rebuild / arrêt |

## 6. Dépannage

| Symptôme | Cause probable |
|---|---|
| `Empty in .env: …` au lancement | Variable manquante dans `.env` (voir `.env.example`) |
| Page du serveur OAuth « redirect_uri invalide » | `PUBLIC_ORIGIN` différent de l'URL déclarée sur le serveur OAuth (port, `http`/`https`, domaine) |
| « Vous n'avez pas accès à l'application » | Accès non attribué : `make grant` / `make prod-grant` sur le serveur OAuth |
| L'API ne démarre pas : `issuer mismatch` | `OAUTH_ISSUER` n'est pas exactement l'issuer publié (comparer avec `curl <issuer>/.well-known/oauth-authorization-server`) |
| `/api/health` renvoie 503, « OAuth server unreachable » | L'API ne joint pas le serveur OAuth ; elle réessaie toutes les 30 s. En dev : l'issuer doit être joignable sous le même nom depuis le conteneur (réseau hôte) |
| `/?auth_error=server_error` après la connexion | Échange du code refusé : client ID/secret erronés. Voir `make logs` |
| Connexion refusée en boucle sur http (prod) | `COOKIE_SECURE=false` est refusé hors `APP_ENV=dev` ; la production exige https |
| Retrait d'accès non pris en compte avant ~15 min | Back-channel logout injoignable : vérifier l'URL déclarée et les journaux du serveur OAuth (« Échec du back-channel logout ») |
| Boucle de connexion en dev sur http | Ouvrir `http://localhost:3001`, pas l'IP de la machine : les cookies `Secure` ne sont acceptés en http que sur `localhost` |
