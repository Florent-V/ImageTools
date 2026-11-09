# Mise en production et mises à jour

Guide pas à pas pour mettre ImageTools en production sur un serveur, puis le mettre à jour (connexion au serveur et `make prod-deploy`). Tout passe par les
commandes `make` du dépôt (`make help` les liste). Pour le contexte (architecture, dev local, dépannage), voir
[`deploiement.md`](deploiement.md).

1. [Ce que vous mettez en place](#1-ce-que-vous-mettez-en-place)
2. [Prérequis](#2-prérequis)
3. [Déclarer l'application sur le serveur OAuth](#3-déclarer-lapplication-sur-le-serveur-oauth)
4. [Installer ImageTools sur le serveur](#4-installer-imagetools-sur-le-serveur)
5. [Brancher le Caddy global](#5-brancher-le-caddy-global)
6. [Vérifier la mise en production](#6-vérifier-la-mise-en-production)
7. [Exploitation courante](#7-exploitation-courante)
8. [Mises à jour](#8-mises-à-jour)
9. [Dépannage en production](#9-dépannage-en-production)

## 1. Ce que vous mettez en place

```
Internet ─▶ Caddy global (HTTPS, HSTS) ─▶ 127.0.0.1:3011 ─▶ conteneur web (Caddy : statique, /api, /auth)
                                                                  └─▶ conteneur api (FastAPI, client OAuth)
                                                                         └─ volume api-data : sessions SQLite
Serveur OAuth (https://oauth.<domaine>) ◀── découverte, code + PKCE, refresh ── api
Serveur OAuth ── logout token (back-channel, via l'URL publique) ──▶ api
```

- Deux conteneurs : `api` (aucun port publié) et `web` (publié sur `127.0.0.1:REMOTE_FRONTEND_PORT` uniquement).
- Le TLS est géré par le Caddy global du serveur. Les conteneurs parlent en http entre eux.
- Aucun secret côté navigateur ; aucun Node en production.

## 2. Prérequis

| Quoi | Détail |
|---|---|
| Serveur | Linux avec Docker et Docker Compose v2, `git`, `make` |
| DNS | Un enregistrement (`imagetools.<domaine>`) vers le serveur |
| Caddy global | Déjà installé sur le serveur, il gère le HTTPS de chaque domaine |
| Serveur OAuth | En production, en `https://`, avec la découverte `/.well-known/oauth-authorization-server` |
| Accès au dépôt | Le serveur doit pouvoir faire `git pull` (clé de déploiement en lecture seule si le dépôt est privé) |

Vérifiez la découverte depuis le serveur avant de commencer :

```bash
curl -fsS https://oauth.<domaine>/.well-known/oauth-authorization-server | head -c 300
```

Le champ `issuer` doit être **exactement** la valeur à mettre dans `OAUTH_ISSUER` (barre finale comprise s'il y en a
une) : l'API refuse de démarrer sinon.

## 3. Déclarer l'application sur le serveur OAuth

Sur le serveur, dans le dossier du serveur OAuth :

```bash
make prod-console c='app:application:create "ImageTools" \
    --home-url=https://imagetools.<domaine>/ \
    --redirect-uri=https://imagetools.<domaine>/auth/callback \
    --backchannel-logout-uri=https://imagetools.<domaine>/auth/backchannel-logout'
make prod-grant email=vous@<domaine> app=<client_id>
```

- **Notez le client ID et le client secret** : le secret n'est affiché qu'une fois (il est stocké haché).
- Déclarez l'URL **publique** de back-channel logout, même si les deux applications sont sur la même machine :
  c'est le serveur OAuth qui l'appelle.
- Répétez `make prod-grant` pour chaque utilisateur autorisé. Aucun rôle n'est nécessaire : ImageTools ne vérifie
  que l'accès.

## 4. Installer ImageTools sur le serveur

### 4.1 Récupérer le code

```bash
git clone git@github.com:Florent-V/ImageTools.git imagetools
cd imagetools
```

### 4.2 Configurer `.env`

```bash
cp .env.example .env && chmod 600 .env
```

Renseignez (le fichier est ignoré par git et ne doit jamais être commité) :

```dotenv
REMOTE_FRONTEND_PORT=3011
MAX_UPLOAD_MB=50
OAUTH_ISSUER=https://oauth.<domaine>
OAUTH_CLIENT_ID=<client_id>
OAUTH_CLIENT_SECRET=<client_secret>
PUBLIC_ORIGIN=https://imagetools.<domaine>
```

Ne définissez **pas** `APP_ENV` ni `COOKIE_SECURE` : les valeurs par défaut (`prod`, `true`) sont les bonnes. L'API
refuse `COOKIE_SECURE=false` hors `APP_ENV=dev`. `FRONTEND_PORT` ne sert qu'en dev.

### 4.3 Vérifier la configuration

```bash
make prod-check
```

Refuse de continuer si une variable manque, si `PUBLIC_ORIGIN` ou `OAUTH_ISSUER` ne sont pas en `https://`, ou si
`APP_ENV` n'est pas `prod`.

### 4.4 Construire et démarrer

```bash
make prod-build prod-up
```

`prod-up` attend que l'API soit saine (`up -d --wait`) : elle ne l'est qu'une fois la découverte du serveur OAuth
réussie. Si la commande échoue, voir [§9](#9-dépannage-en-production) et `make prod-logs`.

```bash
make prod-ps        # api sans port publié ; web sur 127.0.0.1:3011
```

## 5. Brancher le Caddy global

Dans le `Caddyfile` du serveur :

```caddyfile
imagetools.<domaine> {
	reverse_proxy 127.0.0.1:3011
}
```

Puis rechargez Caddy (`caddy reload`, ou l'équivalent de votre installation). Le conteneur `web` sert les fichiers
statiques et route `/api/*` et `/auth/*` vers l'API ; il ajoute déjà la CSP et les headers de sécurité. Le HSTS reste
à la charge du Caddy global (activé par défaut avec HTTPS automatique).

Les envois de fichiers allant jusqu'à 200 Mo, ne mettez pas de limite de corps plus basse devant (`request_body`)
sur ce domaine.

## 6. Vérifier la mise en production

Depuis votre poste :

```bash
curl -fsS https://imagetools.<domaine>/api/health          # {"status":"ok"}
curl -s  -o /dev/null -w "%{http_code}\n" https://imagetools.<domaine>/api/me   # 401 sans session
curl -sI https://imagetools.<domaine>/ | grep -i content-security-policy
```

Puis dans un navigateur :

| Test | Attendu |
|---|---|
| Ouvrir `https://imagetools.<domaine>/crop` | Redirection vers le serveur OAuth, connexion (et 2FA), retour sur `/crop` |
| Outils de développement → cookies | Un seul cookie `__Host-session`, `HttpOnly` et `Secure` ; aucun jeton |
| Convertir une image, traiter une vidéo | Fonctionne |
| Bouton de déconnexion | Déconnexion globale (app et SSO) : retour sur l'écran de connexion du serveur OAuth |

Test du back-channel logout, sur le serveur OAuth :

```bash
make prod-console c="app:application:test-backchannel-logout <client_id> vous@<domaine>"
```

Attendu : « HTTP 200 ». Dans l'app, la requête suivante renvoie à la connexion. Si ce test échoue, la révocation
d'accès ne sera prise en compte qu'au prochain renouvellement de jeton (15 min au plus) : corrigez l'URL déclarée.

## 7. Exploitation courante

| Besoin | Commande |
|---|---|
| État des conteneurs | `make prod-ps` |
| Journaux en continu | `make prod-logs` |
| Redémarrer sans reconstruire | `make prod-restart` |
| Appliquer un changement de `.env` | `make prod-up` (recrée les conteneurs dont l'environnement a changé) |
| Arrêter | `make prod-down` (le volume `api-data`, donc les sessions, est conservé) |

**Données à sauvegarder :** aucune donnée utilisateur n'est conservée (les fichiers traités ne sont pas stockés).
Le volume `api-data` ne contient que les sessions : le perdre déconnecte les utilisateurs, qui se reconnectent par
SSO. Aucune sauvegarde n'est nécessaire ; sauvegardez en revanche `.env` (il contient le secret du client OAuth).

| Changement | Effet | À faire |
|---|---|---|
| Nouveau client secret (régénéré sur le serveur OAuth) | Renouvellements refusés : sessions fermées au plus tard 15 min après | Mettre à jour `OAUTH_CLIENT_SECRET`, `make prod-up` |
| Rotation de la clé de signature du serveur OAuth | Rien : les clés sont relues par `kid` dans le JWKS | — |
| Nouveau domaine | Redirect URI refusée | Mettre à jour l'application sur le serveur OAuth, `PUBLIC_ORIGIN`, le bloc Caddy, `make prod-up` |

## 8. Mises à jour

Connectez-vous au serveur et lancez, depuis le dossier du dépôt :

```bash
cd imagetools
make prod-deploy
```

Enchaîne : `prod-check`, `git pull --ff-only`, `prod-build` (images reconstruites avec `--pull`), `prod-up`
(redémarrage des conteneurs modifiés, attente de l'état sain), puis affiche `prod-ps`. Les sessions survivent (volume
`api-data`). Si une étape échoue, la commande s'arrête avec un code non nul ; tant que `prod-up` n'a pas remplacé
l'API, les conteneurs précédents continuent de tourner.

Contrôle après la mise à jour :

```bash
make prod-ps
curl -fsS https://imagetools.<domaine>/api/health
```

**Retour arrière :**

```bash
git log --oneline -5
git checkout <commit-précédent>
make prod-build prod-up
git checkout main          # avant le prochain make prod-deploy
```

Un déploiement automatique (timer sur le serveur ou GitHub Actions) n'est pas mis en place : le déploiement est
volontairement manuel.

## 9. Dépannage en production

| Symptôme | Cause probable |
|---|---|
| `make prod-check` : `PUBLIC_ORIGIN must be https://` | `.env` encore en valeurs de dev |
| `make prod-up` bloque puis échoue, l'API reste `unhealthy` | Découverte impossible : voir `make prod-logs` (`issuer mismatch`, serveur OAuth injoignable depuis le serveur, endpoints en http) |
| `issuer mismatch` dans les journaux | `OAUTH_ISSUER` n'est pas exactement l'issuer publié : comparez avec la sortie du `curl` du §2 |
| Page OAuth « redirect_uri invalide » | `PUBLIC_ORIGIN` différent de l'URL déclarée sur le serveur OAuth (domaine, `https`) |
| « Vous n'avez pas accès à l'application » | `make prod-grant` manquant pour cet utilisateur (sur le serveur OAuth) |
| Retour sur `/?auth_error=server_error` après connexion | Client ID ou secret erronés ; voir `make prod-logs` |
| Retrait d'accès non pris en compte avant 15 min | Back-channel injoignable : refaire le test du §6 et vérifier l'URL publique déclarée |
| Envoi d'un gros fichier refusé (413) | Une limite de corps plus basse devant le conteneur `web` (Caddy global) |
| `/api/health` renvoie 503 après un redémarrage | Le serveur OAuth était injoignable : l'API réessaie toute seule toutes les 30 s |
