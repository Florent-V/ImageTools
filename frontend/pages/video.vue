<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Vidéo réseaux sociaux</h1>
      <p class="mt-1 text-(--ui-text-muted)">
        Recadrez, convertissez et compressez une vidéo pour TikTok, Instagram, YouTube…
      </p>
    </div>

    <DropZone accept="video/*" :multiple="false" icon="i-lucide-file-video" label="une vidéo" @files-selected="onFilesSelected">
      <template #hint>
        <p v-if="limits" class="text-xs text-(--ui-text-muted)">
          Limite : {{ limits.max_duration_s }}s, {{ limits.max_file_size_mb }} Mo.
        </p>
      </template>
    </DropZone>

    <UAlert v-if="inspectError" color="error" variant="soft" icon="i-lucide-triangle-alert" :title="inspectError" />

    <VideoCropForm
      v-if="file && previewSrc && inspected && presets"
      v-model="cropState"
      :preview-src="previewSrc"
      :video-width="inspected.width"
      :video-height="inspected.height"
      :ratio-presets="presets.ratios"
      :file="file"
      :duration-s="inspected.duration_s"
    />

    <div v-if="presets" class="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <UCard v-if="resolutionOptions.length">
        <template #header>
          <h3 class="font-semibold">Format</h3>
        </template>
        <div class="grid grid-cols-1 gap-4 sm:grid-cols-3">
          <UFormField label="Conteneur">
            <USelect v-model="container" :items="containerItems" class="w-full" />
          </UFormField>
          <UFormField label="Résolution">
            <USelect v-model="selectedResolutionIndex" :items="resolutionItems" class="w-full" />
          </UFormField>
          <UFormField label="Images par seconde">
            <USelect v-model="fps" :items="fpsItems" class="w-full" />
          </UFormField>
        </div>
      </UCard>

      <UCard>
        <template #header>
          <h3 class="font-semibold">Compression</h3>
        </template>
        <div class="flex flex-col gap-2">
          <div class="flex flex-wrap gap-2">
            <UButton
              v-for="q in presets.quality"
              :key="q"
              size="sm"
              :color="quality === q ? 'primary' : 'neutral'"
              :variant="quality === q ? 'solid' : 'outline'"
              @click="quality = q"
            >
              {{ QUALITY_LABELS[q] }}
            </UButton>
          </div>
          <p class="text-xs text-(--ui-text-muted)">{{ QUALITY_DESCRIPTIONS[quality] }}</p>
        </div>
      </UCard>
    </div>

    <UButton size="lg" icon="i-lucide-scissors" :loading="running" :disabled="!canProcess" class="self-start" @click="run">
      Traiter
    </UButton>

    <div v-if="running" class="flex flex-col gap-1.5 max-w-md">
      <UProgress :model-value="progress" />
      <p class="text-xs text-(--ui-text-muted)">
        Traitement en cours… ~{{ remainingSeconds }}s estimées
      </p>
    </div>

    <UAlert v-if="processError" color="error" variant="soft" icon="i-lucide-triangle-alert" :title="processError" />

    <div v-if="result" class="flex items-center gap-3 rounded-lg border border-(--ui-border) p-3">
      <UIcon name="i-lucide-file-video" class="h-8 w-8 shrink-0 text-(--ui-text-muted)" />
      <div class="min-w-0 flex-1">
        <p class="text-sm font-medium">{{ downloadName }}</p>
        <p class="text-sm text-emerald-500">
          {{ formatSize(result.inputSize) }} → {{ formatSize(result.outputSize) }}
          ({{ result.outputWidth }}×{{ result.outputHeight }})
        </p>
      </div>
      <UButton :href="resultUrl" :download="downloadName" icon="i-lucide-download" color="primary" variant="soft" size="sm">
        Télécharger
      </UButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import {
  ApiError,
  fetchVideoLimits,
  fetchVideoPresets,
  inspectVideo,
  processVideo,
  type VideoContainer,
  type VideoCropRect,
  type VideoFps,
  type VideoInspectResponse,
  type VideoProcessResult,
  type VideoQuality,
} from '~/utils/api'
import { computeResolutionOptions } from '~/utils/videoResolution'
import { estimateProcessingSeconds } from '~/utils/videoProgressEstimate'

const QUALITY_LABELS: Record<VideoQuality, string> = {
  light: 'Léger',
  recommended: 'Équilibré',
  strong: 'Fort',
  max: 'Sans compression',
}
const QUALITY_DESCRIPTIONS: Record<VideoQuality, string> = {
  light: 'Qualité quasi intacte, gain de poids modeste.',
  recommended: 'Bon compromis qualité / poids — recommandé pour la plupart des cas.',
  strong: 'Poids minimal, perte de qualité visible sur les détails fins.',
  max: 'Qualité quasi sans perte, fichier nettement plus lourd.',
}

const { data: limits } = await useAsyncData('video-limits', fetchVideoLimits, { server: false })
const { data: presets } = await useAsyncData('video-presets', fetchVideoPresets, { server: false })

const file = ref<File>()
const previewSrc = ref<string>()
const inspected = ref<VideoInspectResponse>()
const inspectError = ref<string>()
const cropState = ref<{ crop: VideoCropRect | null }>({ crop: null })
const container = ref<VideoContainer>('mp4')
const fps = ref<VideoFps>('original')
const quality = ref<VideoQuality>('recommended')
const selectedResolutionIndex = ref(0)
const running = ref(false)
const processError = ref<string>()
const result = ref<VideoProcessResult>()
const resultUrl = ref<string>()
const progress = ref(0)
const remainingSeconds = ref(0)
let progressTimer: ReturnType<typeof setInterval> | undefined

onBeforeUnmount(() => {
  if (resultUrl.value) URL.revokeObjectURL(resultUrl.value)
  if (progressTimer) clearInterval(progressTimer)
})

const containerItems = computed(() => (presets.value?.containers ?? []).map((c) => ({ label: c.label, value: c.id })))
const fpsItems = computed(() => (presets.value?.fps ?? []).map((f) => ({ label: f === 'original' ? 'Original' : `${f} fps`, value: f })))

const resolutionOptions = computed(() => {
  const crop = cropState.value.crop
  if (!crop || !presets.value) return []
  return computeResolutionOptions(crop.width, crop.height, presets.value.resolution_ladder)
})
const resolutionItems = computed(() =>
  resolutionOptions.value.map((res, index) => ({ label: `${res.label} (${res.width}×${res.height})`, value: index })),
)

watch(resolutionOptions, () => {
  selectedResolutionIndex.value = 0
})

const canProcess = computed(() => !!file.value && !!cropState.value.crop && resolutionOptions.value.length > 0 && !running.value)
const downloadName = computed(() => {
  const base = file.value ? baseName(file.value.name) : 'video'
  return `${base}.${container.value}`
})

function baseName(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot === -1 ? name : name.slice(0, dot)
}

function formatSize(bytes: number): string {
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(0)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
}

async function loadFile(picked: File) {
  file.value = picked
  inspectError.value = undefined
  inspected.value = undefined
  result.value = undefined
  cropState.value = { crop: null }

  try {
    const inspection = await inspectVideo(picked)
    inspected.value = inspection
    previewSrc.value = inspection.preview_frame
  } catch (err) {
    inspectError.value = err instanceof ApiError ? err.message : "Impossible d'analyser cette vidéo."
  }
}

function onFilesSelected(files: File[]) {
  const picked = files[0]
  if (picked) loadFile(picked)
}

async function run() {
  if (!file.value || !cropState.value.crop || !inspected.value) return
  const resolution = resolutionOptions.value[selectedResolutionIndex.value]
  if (!resolution) return
  running.value = true
  processError.value = undefined

  const estimatedSeconds = estimateProcessingSeconds(inspected.value.duration_s, resolution.width, resolution.height, container.value)
  const startedAt = performance.now()
  progress.value = 0
  remainingSeconds.value = Math.ceil(estimatedSeconds)
  progressTimer = setInterval(() => {
    const elapsedS = (performance.now() - startedAt) / 1000
    progress.value = Math.min(90, (elapsedS / estimatedSeconds) * 90)
    remainingSeconds.value = Math.max(0, Math.ceil(estimatedSeconds - elapsedS))
  }, 100)

  try {
    const output = await processVideo(file.value, {
      crop: cropState.value.crop,
      output: {
        resolution_width: resolution.width,
        resolution_height: resolution.height,
        quality: quality.value,
        container: container.value,
        fps: fps.value,
      },
    })
    progress.value = 100
    result.value = output
    if (resultUrl.value) URL.revokeObjectURL(resultUrl.value)
    resultUrl.value = URL.createObjectURL(output.blob)
  } catch (err) {
    processError.value = err instanceof ApiError ? err.message : 'Erreur lors du traitement.'
  } finally {
    clearInterval(progressTimer)
    running.value = false
  }
}
</script>
