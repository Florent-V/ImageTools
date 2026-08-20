export default defineNuxtConfig({
  compatibilityDate: '2026-07-30',
  devtools: { enabled: false },
  telemetry: false,
  modules: ['@nuxt/ui'],
  css: ['~/assets/css/main.css'],
  // Nuxt Icon's on-demand fetch route defaults under /api, which our
  // nitro.devProxy below forwards entirely to the backend — colliding with
  // it and silently breaking any icon not caught by the build-time bundle.
  icon: {
    localApiEndpoint: '/_nuxt_icon',
  },
  components: [
    { path: '~/components/layout', pathPrefix: false },
    { path: '~/components', pathPrefix: false },
  ],
  runtimeConfig: {
    public: {
      // Empty by default: same-origin relative /api calls, handled by the
      // dev proxy or a fronting Caddy. Only prod-remote's direct-port
      // access sets this, to call the backend cross-origin.
      apiBaseUrl: '',
    },
  },
  nitro: {
    devProxy: {
      '/api': {
        target: process.env.NUXT_DEV_API_TARGET || 'http://localhost:8000/api',
        changeOrigin: true,
      },
    },
    // Dev-only: Vite's HMR client runs module code through `new Function`,
    // which a strict script-src (no unsafe-eval) blocks outright — that
    // breaks the entire app (no hydration, no icons, no interactivity), not
    // just the intended XSS defence. Ship the strict CSP in production only,
    // where every SFC is precompiled and nothing needs eval.
    routeRules: process.env.NODE_ENV === 'production' ? {
      // No XSS sink exists in the app today (no v-html/innerHTML/eval
      // anywhere) — this is defence-in-depth for if that ever changes, plus
      // basic clickjacking protection.
      '/**': {
        headers: {
          // script-src needs 'unsafe-inline': Nuxt SSR embeds the hydration
          // payload as an inline <script> whose content (and hash) differs
          // per request, so a nonce/hash allowlist isn't viable without a
          // dedicated CSP module. default-src 'self' still blocks loading
          // any *external* script/resource, which is the more common XSS
          // exfiltration path — this is reduced defence-in-depth, not none.
          'Content-Security-Policy': "default-src 'self'; img-src 'self' blob: data:; media-src 'self' blob:; style-src 'self' 'unsafe-inline'; script-src 'self' 'unsafe-inline'; connect-src 'self'; frame-ancestors 'none'",
          'X-Content-Type-Options': 'nosniff',
          'X-Frame-Options': 'DENY',
          'Referrer-Policy': 'strict-origin-when-cross-origin',
        },
      },
    } : {},
  },
})
