export interface ToolNavItem {
  title: string
  description: string
  icon: string
  to: string | null
  wip: boolean
}

export interface ToolNavCategory {
  title: string
  icon: string
  color: 'indigo' | 'amber' | 'emerald' | 'sky' | 'fuchsia'
  tools: ToolNavItem[]
}

export const TOOL_CATEGORIES: ToolNavCategory[] = [
  {
    title: 'Convertir',
    icon: 'i-lucide-refresh-cw',
    color: 'indigo',
    tools: [
      { title: 'Convertir un format', description: 'Changez de format sans perte de résolution.', icon: 'i-lucide-file-symlink', to: '/convert', wip: false },
    ],
  },
  {
    title: 'Ajuster',
    icon: 'i-lucide-crop',
    color: 'sky',
    tools: [
      { title: 'Redimensionner', description: 'En pixels ou en pourcentage.', icon: 'i-lucide-scaling', to: '/resize', wip: false },
      { title: 'Recadrer', description: 'Sélection visuelle ou coordonnées.', icon: 'i-lucide-crop', to: '/crop', wip: false },
      { title: 'Rotation / miroir', description: '90°, 180°, 270°, retournement.', icon: 'i-lucide-rotate-cw', to: '/rotate', wip: false },
    ],
  },
  {
    title: 'Compresser',
    icon: 'i-lucide-file-down',
    color: 'emerald',
    tools: [
      { title: 'Compresser', description: 'Réduisez le poids à dimensions constantes.', icon: 'i-lucide-file-down', to: '/compress', wip: false },
    ],
  },
  {
    title: 'Atelier',
    icon: 'i-lucide-layers',
    color: 'amber',
    tools: [
      { title: 'Atelier', description: 'Enchaînez plusieurs opérations en pipeline.', icon: 'i-lucide-layers', to: '/workshop', wip: false },
    ],
  },
  {
    title: 'PWA',
    icon: 'i-lucide-smartphone',
    color: 'indigo',
    tools: [
      {
        title: "Kit d'icônes PWA",
        description: 'Manifest, icônes Android/iOS, favicon et splash iOS en un clic.',
        icon: 'i-lucide-smartphone',
        to: '/pwa',
        wip: false,
      },
    ],
  },
  {
    title: 'Retoucher',
    icon: 'i-lucide-wand-2',
    color: 'fuchsia',
    tools: [
      { title: 'Filigrane', description: 'Texte ou image, position et opacité.', icon: 'i-lucide-stamp', to: '/watermark', wip: false },
      { title: 'Flou / pixellisation', description: 'Sélection manuelle de zone.', icon: 'i-lucide-blend', to: null, wip: true },
      { title: 'Amélioration qualité', description: 'Netteté, contraste, balance des blancs.', icon: 'i-lucide-sparkle', to: null, wip: true },
      { title: 'GIF animé', description: 'Depuis plusieurs images.', icon: 'i-lucide-film', to: null, wip: true },
    ],
  },
  {
    title: 'Intelligence artificielle',
    icon: 'i-lucide-sparkles',
    color: 'fuchsia',
    tools: [
      { title: 'Agrandissement', description: 'Upscale ×2/×4 par IA.', icon: 'i-lucide-expand', to: null, wip: true },
      { title: "Suppression d'arrière-plan", description: 'Détourage automatique.', icon: 'i-lucide-scissors', to: null, wip: true },
      { title: 'Restauration de visages', description: 'Amélioration par IA.', icon: 'i-lucide-scan-face', to: null, wip: true },
      { title: 'Floutage auto visages/plaques', description: 'Détection et flou automatiques.', icon: 'i-lucide-eye-off', to: null, wip: true },
    ],
  },
  {
    title: 'Éditeur',
    icon: 'i-lucide-pen-tool',
    color: 'amber',
    tools: [
      { title: 'Éditeur photo', description: 'Recadrage, texte, formes, filtres.', icon: 'i-lucide-pen-tool', to: null, wip: true },
      { title: 'Générateur', description: 'Texte libre et dessin sur votre image.', icon: 'i-lucide-image-plus', to: '/generator', wip: false },
    ],
  },
  {
    title: 'Vidéo',
    icon: 'i-lucide-video',
    color: 'sky',
    tools: [
      { title: 'Vidéo réseaux sociaux', description: 'Recadrer, convertir et compresser pour TikTok, Instagram, YouTube.', icon: 'i-lucide-video', to: '/video', wip: false },
    ],
  },
]
