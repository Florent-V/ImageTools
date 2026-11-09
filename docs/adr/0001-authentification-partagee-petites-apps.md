# ADR 0001 — Authentification partagée pour les applications sans base de données

**Date** : 2026-08-13
**Statut** : remplacé — ImageConverter est protégé par le serveur OAuth maison (`OAuth-serveur`), intégré dans l'application (Nuxt BFF + vérification du jeton dans FastAPI), voir le README.

## Contexte

Le serveur personnel héberge et hébergera plusieurs applications de tailles très différentes :

- des applications avec authentification intégrée (base de données utilisateurs, gestion des comptes) — hors périmètre de cet ADR ;
- des petites applications sans état, sans base de données, sans espace utilisateur — dont **ImageConverter** est la première (voir [design principal](../superpowers/specs/2026-07-24-image-converter-design.md) §9 : « authentification et HTTPS : phase 2, prévue non construite »).

Créer une base de données et un système de comptes pour chaque petite application est disproportionné : ce sont des outils personnels, l'utilisateur est seul, le besoin réel est « une porte fermée devant plusieurs apps », pas une gestion d'identité par app.

**Contrainte de topologie confirmée** : les petites applications seront exposées en sous-domaines d'un même domaine (ex. `app3.tondomaine.fr`, `app4.tondomaine.fr`, `imageconverter.tondomaine.fr`). Cette contrainte est ce qui rend possible un cookie de session partagé entre toutes ces apps — c'est le point de départ de la comparaison ci-dessous.

Le serveur distant expose déjà un Caddy global (hors dépôts applicatifs, voir [design frontend/déploiement](../superpowers/specs/2026-07-30-frontend-deployment-design.md) §2) qui route vers chaque conteneur par nom de domaine. La solution retenue doit s'intégrer à ce Caddy existant sans le remplacer.

## Décision à prendre

Comment protéger N petites applications sans authentification propre, derrière une **authentification unique, partagée, gratuite**, sans toucher aux applications elles-mêmes (le contrôle d'accès se fait devant, pas dedans) — sans perturber les applications qui ont déjà leur propre authentification intégrée.

## Critères de décision

| Critère | Poids | Pourquoi |
|---|---|---|
| Gratuit / open-source | obligatoire | pas de budget pour ça |
| Aucune modification du code des petites apps | haute | ImageConverter et consorts n'ont ni notion d'utilisateur ni middleware d'auth — tout doit se passer dans le reverse proxy |
| Intégration avec Caddy existant | haute | éviter de dupliquer un point d'entrée réseau |
| Session unique (SSO) entre les petites apps | moyenne | se logguer une fois, naviguer entre app3/app4/app5 sans re-taper le mot de passe |
| Coût opérationnel (RAM, conteneurs, base de données à maintenir) | haute | objectif explicite : ne pas recréer une base de données par app — donc pas question d'en ajouter une lourde pour l'auth non plus |
| N'affecte pas les apps à auth intégrée | obligatoire | app1/app2 gardent leur système, aucune double authentification |

## Options considérées

### A. `basic_auth` natif dans Caddy, par app

Chaque bloc Caddyfile des petites apps reçoit une directive `basic_auth` avec un hash bcrypt. Aucun service supplémentaire.

- ✅ Zéro conteneur ajouté, zéro base de données, configuration en quelques lignes.
- ✅ Peut réutiliser le même couple identifiant/hash sur app3, app4, app5 → même mot de passe partout.
- ❌ Pas de vraie session partagée : le navigateur redemande les identifiants par domaine (popup native du navigateur), pas de logout propre, pas de 2FA, pas d'écran de login personnalisé.
- ❌ Ajouter une app = éditer le Caddyfile global à la main à chaque fois.

### B. Authelia + `forward_auth` (Caddy) — **recommandé**

Un conteneur unique (`authelia/authelia`, gratuit, open-source) sert de portail d'authentification central. Caddy délègue la vérification à Authelia via la directive `forward_auth` avant de router vers app3/app4/app5. Authelia gère lui-même : écran de login, session cookie, 2FA (TOTP) optionnelle, règles d'accès par domaine.

- ✅ Gratuit, léger (un seul binaire Go, pas de JVM).
- ✅ Stockage utilisateurs en **fichier YAML** (mots de passe hashés argon2) — pas de serveur de base de données à faire tourner. Le stockage interne (sessions, historique de tentatives) utilise **SQLite embarqué**, aucun service externe.
- ✅ **Vraie session SSO** : cookie posé sur le domaine parent (ex. `.tondomaine.fr`), valable pour toutes les sous-app protégées. Un seul login pour app3/app4/app5.
- ✅ S'intègre nativement à Caddy (directive `forward_auth`, une ligne par app protégée).
- ✅ N'exige aucune modification des petites apps : la vérification a lieu entièrement au niveau du proxy.
- ✅ N'a aucun contact avec app1/app2 : leur config Caddy reste inchangée, elles gardent leur propre authentification.
- ⚠️ Exige que les apps protégées soient des sous-domaines du même domaine parent (contrainte déjà confirmée ci-dessus).
- ⚠️ Notifications (reset de mot de passe) : sans serveur SMTP configuré, Authelia écrit dans un fichier local plutôt que d'envoyer un email — acceptable en usage perso, à documenter.

### C. oauth2-proxy + fournisseur OIDC externe (ou Authelia/Authentik en IdP)

Un sidecar `oauth2-proxy` par application, chacun pointant vers un fournisseur d'identité OIDC commun.

- ✅ Fonctionne même si les apps sont sur des domaines complètement différents (pas de contrainte de sous-domaine).
- ✅ Gratuit.
- ❌ Un conteneur sidecar **par application** protégée (complexité qui grandit avec le nombre d'apps) — inutile ici puisque toutes les apps sont sur le même domaine.
- ❌ Nécessite quand même un fournisseur OIDC derrière (Authelia, Authentik, Google, GitHub...) — ajoute une brique par rapport à l'option B sans bénéfice, vu la contrainte de sous-domaine déjà satisfaite.

### D. Authentik

IdP complet (OIDC + SAML), interface d'administration riche, pensé pour des besoins d'entreprise (multi-fournisseurs, provisioning...).

- ✅ Gratuit, très complet, capable de servir aussi de fournisseur d'identité pour de futures apps à auth intégrée (SSO OIDC réel plutôt que juste `forward_auth`).
- ❌ Nécessite **PostgreSQL + Redis** en plus du conteneur applicatif — exactement la lourdeur (base de données à maintenir) que l'objectif initial cherche à éviter pour ce cas d'usage.
- ❌ Surdimensionné pour « fermer la porte devant 3 apps sans utilisateurs ».

## Décision

**Option B — Authelia devant Caddy, via `forward_auth`.**

Elle coche toutes les cases obligatoires et hautes : gratuite, aucune base de données serveur à opérer (fichier YAML + SQLite embarqué), aucune modification des petites apps, intégration Caddy native, vraie session SSO grâce à la contrainte de sous-domaine déjà en place. Les options C et D résolvent des problèmes que ce projet n'a pas (domaines hétérogènes, IAM d'entreprise) au prix d'une complexité opérationnelle plus grande.

app1/app2 (auth intégrée) ne sont pas concernées : leur bloc Caddyfile n'a pas de directive `forward_auth`, Authelia ne les voit jamais.

## Conséquences

- Un nouveau conteneur (`authelia`) à faire tourner en permanence sur le serveur, hors des dépôts applicatifs — comme Caddy aujourd'hui.
- Un sous-domaine dédié au portail (ex. `auth.tondomaine.fr`).
- Un fichier `users_database.yml` à maintenir manuellement (ajout/suppression de comptes, changement de mot de passe) — pas d'interface d'admin web dans la configuration minimale (existe en version payante *Authelia Pro*, non nécessaire ici).
- Chaque petite app protégée nécessite l'ajout d'un bloc `forward_auth` dans le Caddyfile global — geste manuel à chaque nouvelle app, comme documenté au design frontend/déploiement §6 pour le bloc distant.
- ImageConverter en particulier : le design §9 prévoit déjà `basic_auth` et HTTPS dans Caddy comme phase 2. Cette ADR **remplace** ce plan initial (basic_auth par app) par le portail Authelia partagé — à refléter dans une mise à jour du design principal si cette ADR est adoptée.

## Plan de mise en œuvre (aperçu)

1. Déployer le conteneur `authelia` sur le serveur (hors de ce dépôt, comme le Caddy global) avec stockage SQLite local et provider de session `memory` (une seule instance, pas de Redis nécessaire).
2. Créer `users_database.yml` avec le ou les comptes utilisateur (hash argon2 via `authelia crypto hash generate`).
3. Définir la politique d'accès (`access_control`) dans la config Authelia : quels sous-domaines sont protégés, niveau requis (`one_factor` suffit pour un usage perso sans données sensibles ; `two_factor` si souhaité).
4. Ajouter au Caddyfile global un sous-domaine `auth.tondomaine.fr` pointant vers Authelia, puis un bloc `forward_auth` sur chaque petite app (app3/app4/app5, puis `imageconverter.tondomaine.fr` quand exposée en `prod-remote`).
5. Vérifier : accès à app3 redirige vers le login Authelia, session valide ensuite sur app4/app5 sans re-login ; app1/app2 inchangées.
6. Mettre à jour le design ImageConverter §9 pour remplacer « `basic_auth` phase 2 » par référence à cette ADR.
