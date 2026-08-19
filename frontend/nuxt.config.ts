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
  },
})
