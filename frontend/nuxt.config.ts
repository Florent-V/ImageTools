export default defineNuxtConfig({
  compatibilityDate: '2026-07-30',
  devtools: { enabled: false },
  telemetry: false,
  modules: ['@nuxt/ui'],
  css: ['~/assets/css/main.css'],
  components: [
    { path: '~/components/layout', pathPrefix: false },
    { path: '~/components', pathPrefix: false },
  ],
  // Static SPA served by Caddy (nuxt generate): no Node in production. The
  // backend is the OAuth client; the browser only holds an opaque session
  // cookie and calls /api/** and /auth/** on its own origin.
  ssr: false,
  nitro: {
    // Dev only: keep a single origin, as behind Caddy in production.
    devProxy: {
      '/api': { target: `${process.env.DEV_BACKEND_URL ?? 'http://localhost:8000'}/api`, changeOrigin: false },
      '/auth': { target: `${process.env.DEV_BACKEND_URL ?? 'http://localhost:8000'}/auth`, changeOrigin: false },
    },
  },
})
