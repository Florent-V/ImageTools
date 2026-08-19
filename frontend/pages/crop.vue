<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Recadrer</h1>
      <p class="mt-1 text-(--ui-text-muted)">Sélection visuelle ou coordonnées.</p>
    </div>

    <DropZone
      v-if="formats"
      :read-formats="formats.read"
      :max-file-size-mb="formats.limits.max_file_size_mb"
      @files-selected="onFilesSelected"
    />
    <CropForm
      v-if="previewSrc && inspected"
      v-model="cropOp"
      :preview-src="previewSrc"
      :image-width="inspected.width"
      :image-height="inspected.height"
    />
    <UAlert v-if="inspectError" color="error" variant="soft" icon="i-lucide-triangle-alert" :title="inspectError" />
    <UButton
      size="lg"
      icon="i-lucide-crop"
      :loading="running"
      :disabled="!queue.length || !cropOp"
      class="self-start"
      @click="run"
    >
      Recadrer
    </UButton>
    <ImageQueue :items="queue" />
  </div>
</template>

<script setup lang="ts">
import { ApiError, fetchFormats, inspectImage, type CropOp, type InspectResponse, type OutputSpec } from '~/utils/api'

const { data: formats } = await useAsyncData('formats', fetchFormats, { server: false })
const { queue, enqueue, process } = useProcessor()

const previewSrc = ref<string>()
const inspected = ref<InspectResponse>()
const cropOp = ref<CropOp | null>(null)
const inspectError = ref<string>()
const running = ref(false)

// Crop only removes pixels — output keeps the source format at max quality,
// metadata untouched, no other transformation (no OutputForm on this page).
const output = computed<OutputSpec>(() => {
  const raw = inspected.value?.format.toLowerCase()
  const format = raw === 'jpg' ? 'jpeg' : raw
  const supported = format && formats.value?.write.includes(format)
  return { format: supported ? (format as OutputSpec['format']) : 'png', quality: 100, strip_metadata: false }
})

onBeforeUnmount(() => {
  if (previewSrc.value) URL.revokeObjectURL(previewSrc.value)
})

async function onFilesSelected(files: File[]) {
  enqueue(files)
  if (!previewSrc.value && files[0]) {
    previewSrc.value = URL.createObjectURL(files[0])
    inspectError.value = undefined
    try {
      inspected.value = await inspectImage(files[0])
    } catch (err) {
      inspectError.value = err instanceof ApiError ? err.message : "Impossible d'analyser cette image."
    }
  }
}

async function run() {
  if (!cropOp.value) return
  running.value = true
  try {
    await process({ ops: [cropOp.value], output: output.value })
  } finally {
    running.value = false
  }
}
</script>
