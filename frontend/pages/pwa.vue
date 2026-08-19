<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Kit d'icônes PWA</h1>
      <p class="mt-1 text-(--ui-text-muted)">
        Manifest, icônes Android/iOS, favicon et splash iOS générés en un clic — traités sur ce serveur, jamais
        partagés.
      </p>
    </div>

    <DropZone
      v-if="formats"
      :read-formats="formats.read"
      :max-file-size-mb="formats.limits.max_file_size_mb"
      @files-selected="onFilesSelected"
    />

    <CropForm
      v-if="previewSrc && inspected"
      v-model="cropRect"
      :preview-src="previewSrc"
      :image-width="inspected.width"
      :image-height="inspected.height"
      :locked-ratio="1"
    />
    <UAlert v-if="inspectError" color="error" variant="soft" icon="i-lucide-triangle-alert" :title="inspectError" />

    <PwaManifestForm v-model="manifest" v-model:background-color="backgroundColor" />
    <PwaPlatformToggles v-model="platforms" />

    <UButton
      size="lg"
      icon="i-lucide-smartphone"
      :loading="running"
      :disabled="!file || !cropRect || !manifest.name || !manifest.short_name"
      class="self-start"
      @click="run"
    >
      Générer le kit
    </UButton>
    <UAlert v-if="runError" color="error" variant="soft" icon="i-lucide-triangle-alert" :title="runError" />

    <PwaResultPanel :result="result" />
  </div>
</template>

<script setup lang="ts">
import {
  ApiError,
  fetchFormats,
  generatePwaKit,
  inspectImage,
  type CropOp,
  type InspectResponse,
  type PwaGenerateRequest,
  type PwaKitResult,
  type PwaManifestFields,
  type PwaPlatforms as PwaPlatformsType,
} from '~/utils/api'

const { data: formats } = await useAsyncData('formats', fetchFormats, { server: false })

const file = ref<File>()
const previewSrc = ref<string>()
const inspected = ref<InspectResponse>()
const cropRect = ref<CropOp | null>(null)
const inspectError = ref<string>()
const runError = ref<string>()
const running = ref(false)
const result = ref<PwaKitResult | null>(null)

const backgroundColor = ref('#FFFFFF')
const manifest = ref<PwaManifestFields>({
  name: '',
  short_name: '',
  theme_color: '#000000',
  display: 'standalone',
  description: null,
  orientation: null,
})
const platforms = ref<PwaPlatformsType>({ android: true, ios: true, favicon: true, windows: true, splash: true })

onBeforeUnmount(() => {
  if (previewSrc.value) URL.revokeObjectURL(previewSrc.value)
})

async function onFilesSelected(files: File[]) {
  if (!files[0]) return
  if (previewSrc.value) URL.revokeObjectURL(previewSrc.value)
  file.value = files[0]
  cropRect.value = null
  result.value = null
  previewSrc.value = URL.createObjectURL(files[0])
  inspectError.value = undefined
  try {
    inspected.value = await inspectImage(files[0])
  } catch (err) {
    inspectError.value = err instanceof ApiError ? err.message : "Impossible d'analyser cette image."
  }
}

async function run() {
  if (!file.value || !cropRect.value) return
  running.value = true
  runError.value = undefined
  try {
    const request: PwaGenerateRequest = {
      crop: { x: cropRect.value.x, y: cropRect.value.y, width: cropRect.value.width, height: cropRect.value.height },
      background_color: backgroundColor.value,
      manifest: manifest.value,
      platforms: platforms.value,
    }
    result.value = await generatePwaKit(file.value, request)
  } catch (err) {
    runError.value = err instanceof ApiError ? err.message : 'Erreur inattendue.'
  } finally {
    running.value = false
  }
}
</script>
