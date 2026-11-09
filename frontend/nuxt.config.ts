export default defineNuxtConfig({
  modules: ['@nuxt/ui', '@nuxt/eslint'],
  // Static SPA served by Caddy (nuxt generate): no Node in production. The
  // backend is the OAuth client; the browser only holds an opaque session
  // cookie and calls /api/** and /auth/** on its own origin.
  ssr: false,
  components: [
    { path: '~/components/layout', pathPrefix: false },
    { path: '~/components', pathPrefix: false }
  ],
  devtools: { enabled: false },
  css: ['~/assets/css/main.css'],
  compatibilityDate: '2026-07-30',
  nitro: {
    // Dev only: keep a single origin, as behind Caddy in production.
    devProxy: {
      '/api': { target: `${process.env.BACKEND_URL ?? 'http://localhost:8000'}/api`, changeOrigin: false },
      '/auth': { target: `${process.env.BACKEND_URL ?? 'http://localhost:8000'}/auth`, changeOrigin: false }
    }
  },
  vite: {
    // Dev only: the OAuth server (in Docker) calls the back-channel logout URL
    // through host.docker.internal, which Vite would otherwise refuse.
    server: { allowedHosts: ['host.docker.internal'] }
  },
  telemetry: false,
  eslint: {
    config: {
      stylistic: {
        commaDangle: 'never',
        braceStyle: '1tbs'
      }
    }
  },
  // Static build: no Nuxt server to serve icons and the Iconify API must not
  // be called. Every icon used in the sources is bundled.
  icon: {
    provider: 'none',
    clientBundle: { scan: { globInclude: ['**/*.{vue,ts}'] } }
  }
})
