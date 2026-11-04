// Full navigation, not navigateTo: /auth/login is served by the backend
export function redirectToLogin(returnTo: string): void {
  window.location.href = `/auth/login?return_to=${encodeURIComponent(returnTo)}`
}
