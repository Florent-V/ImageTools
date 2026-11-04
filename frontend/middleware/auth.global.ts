// The whole app is reserved to users signed in through the OAuth server
const PUBLIC_PATHS = ['/logged-out']

export default defineNuxtRouteMiddleware(async (to) => {
  if (PUBLIC_PATHS.includes(to.path)) return
  // The backend sends login failures here: show them (app.vue) instead of looping
  if (to.query.auth_error) return
  const { user, loaded, refresh } = useUser()
  if (!loaded.value) await refresh()
  if (!user.value) {
    redirectToLogin(to.fullPath)
    return abortNavigation()
  }
})
