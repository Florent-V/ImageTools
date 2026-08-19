<template>
  <UCard v-if="result">
    <template #header>
      <h3 class="font-semibold">Kit PWA prêt</h3>
    </template>

    <div class="flex flex-col gap-3">
      <p class="text-sm text-(--ui-text-muted)">
        {{ result.fileCount }} fichiers générés — icônes, manifest et snippet HTML inclus.
      </p>
      <UButton icon="i-lucide-download" color="primary" class="self-start" @click="download">
        Télécharger le kit (.zip)
      </UButton>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { PwaKitResult } from '~/utils/api'

const props = defineProps<{ result: PwaKitResult | null }>()

function download() {
  if (!props.result) return
  const url = URL.createObjectURL(props.result.blob)
  const anchor = document.createElement('a')
  anchor.href = url
  anchor.download = 'pwa-assets.zip'
  anchor.click()
  URL.revokeObjectURL(url)
}
</script>
