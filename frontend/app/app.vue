<script setup lang="ts">
useHead({
  meta: [{ name: 'viewport', content: 'width=device-width, initial-scale=1' }],
  link: [{ rel: 'icon', href: '/favicon.ico' }],
  htmlAttrs: { lang: 'fr' }
})

const title = 'ImageTools'
const description = 'Convertissez, compressez, redimensionnez et recadrez vos images sans jamais les envoyer sur Internet.'

useSeoMeta({
  title,
  description,
  ogTitle: title,
  ogDescription: description,
  twitterCard: 'summary_large_image'
})

// Set by the backend after a failed login (/?auth_error=<code>)
const route = useRoute()
const { user, login } = useUser()
const authError = computed(() => (!user.value && typeof route.query.auth_error === 'string' ? route.query.auth_error : null))
</script>

<template>
  <UApp>
    <AppHeader />

    <div class="flex items-start min-h-[calc(100vh-64px)]">
      <AppSidebar class="hidden md:block" />
      <UMain class="flex-1 p-4 md:p-8">
        <div
          v-if="authError"
          class="max-w-md mx-auto py-16 text-center space-y-4"
        >
          <h1 class="text-2xl font-bold">
            Connexion impossible
          </h1>
          <p class="text-(--ui-text-muted)">
            {{ authError === 'access_denied' ? 'Votre compte n’a pas accès à cette application.' : 'Le serveur d’authentification a refusé ou échoué la connexion.' }}
          </p>
          <UButton @click="login('/')">
            Réessayer
          </UButton>
        </div>
        <NuxtPage v-else />
      </UMain>
    </div>

    <AppFooter />
  </UApp>
</template>
