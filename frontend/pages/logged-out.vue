<script setup lang="ts">
useHead({ title: 'Déconnecté' })
</script>

<template>
  <div class="max-w-md mx-auto py-16 text-center space-y-4">
    <h1 class="text-2xl font-bold">Vous êtes déconnecté</h1>
    <p class="text-(--ui-text-muted)">Votre session ImageTools est fermée.</p>
    <!-- Full navigation: /auth/login is served by the backend -->
    <UButton href="/auth/login" external>Se reconnecter</UButton>
  </div>
</template>
