# ImageTools — Roadmap

État au 2026-08-13. v1 (backend + frontend + déploiement) est complet et fonctionnel. Ce document liste ce qu'il reste à faire, dans l'ordre de priorité suggéré.

Référence : [`docs/superpowers/specs/2026-07-24-image-converter-design.md`](docs/superpowers/specs/2026-07-24-image-converter-design.md) §11 pour la feuille de route détaillée par version.

## Priorité haute — hors roadmap existante

Découvertes lors de l'analyse spec/plan, non couvertes par v2/v3/v4 ci-dessous.

- [ ] **Support HEIC en lecture** — absent de v1 et de tout le roadmap v2-v4. Format par défaut des photos iPhone ; gap pratique majeur pour un usage mobile réel.
- [ ] **Authentification avant exposition prod-remote** — le profil `prod-remote` route déjà vers un Caddy externe, mais `basic_auth`/HTTPS restent "phase 2, non construits" (design §9). Ne pas exposer `prod-remote` sur Internet sans ça.
- [ ] **Confirmer le choix "pas de persistance / pas de reprise de lot"** — décision assumée pour la confidentialité (design §2, §4), mais divergence UX notable avec iLoveIMG. À valider que c'est toujours voulu avant d'aller plus loin.

## v2 — extensions du même moteur Pillow

- [ ] Filigrane texte et image (position, opacité, taille)
- [ ] Flou / pixellisation de zone (sélection manuelle)
- [ ] Amélioration qualité sans IA (niveaux auto, balance des blancs, netteté, réduction de bruit, contraste)
- [ ] Images vers PDF (`img2pdf`, sans réencodage)
- [ ] GIF animé depuis plusieurs images
- [ ] Authentification et HTTPS (Caddy) — recoupe le point priorité haute ci-dessus

## Vidéo — moteur ffmpeg

Fait. Hors du moteur Pillow existant ; tourne dans le conteneur
backend existant (pas de service séparé — décision prise à
l'implémentation, plus simple pour un usage mono-utilisateur
autohébergé). Un seul outil : recadrage (préréglages TikTok/Reels/
Shorts, Instagram carré/portrait, YouTube, ou recadrage manuel),
résolution et compression, en une seule interface (`/video`).
Synchrone (vidéos ≤60s/200 Mo), pas de file d'attente.

- [x] Recadrage + conversion + compression vidéo (voir
      `docs/superpowers/specs/2026-08-13-video-social-export-design.md`)
- [x] Page `/video` restylée avec NuxtUI (`video.vue`, `VideoCropForm.vue`)

## v3 — IA (service Docker séparé, optionnel)

- [ ] Agrandissement (Real-ESRGAN, ×2/×4)
- [ ] Suppression d'arrière-plan (`rembg` ou BiRefNet)
- [ ] Restauration de visages (GFPGAN)
- [ ] Floutage automatique visages/plaques (détection + flou v2)

## v4 — éditeur photo

- [ ] Éditeur canvas (recadrage, texte, formes, filtres, luminosité/contraste, cadres) — export liste de calques/opérations, appliqué en pleine résolution côté backend
- [ ] Générateur de mèmes (préréglage de l'éditeur, deux zones de texte)

## Écarté (décision assumée, pas un oubli)

- HTML vers image — nécessite navigateur headless (Playwright, +400 Mo), hors sujet traitement d'images locales
- mDNS / nom de domaine local — IP + port LAN suffit
- TLS en prod-home — réseau LAN de confiance
- Pinia, internationalisation — pas de besoin identifié en v1
