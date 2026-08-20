<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Filigrane</h1>
      <p class="mt-1 text-(--ui-text-muted)">Texte ou image, position et opacité.</p>
    </div>

    <DropZone
      v-if="formats"
      :read-formats="formats.read"
      :max-file-size-mb="formats.limits.max_file_size_mb"
      @files-selected="onFilesSelected"
    />
    <WatermarkForm
      v-if="previewSrc && inspected"
      v-model="watermarkOp"
      :preview-src="previewSrc"
      @watermark-file="(file) => (watermarkFile = file)"
    />
    <UAlert v-if="inspectError" color="error" variant="soft" icon="i-lucide-triangle-alert" :title="inspectError" />
    <UButton
      size="lg"
      icon="i-lucide-stamp"
      :loading="running"
      :disabled="!queue.length || !canRun"
      class="self-start"
      @click="run"
    >
      Appliquer le filigrane
    </UButton>
    <ImageQueue :items="queue" />
  </div>
</template>

<script setup lang="ts">
import type { OutputSpec, WatermarkOp } from '~/utils/api'

const { formats, queue, enqueue, run: runProcess, running } = await useToolPage()
const { inspected, inspectError, inspectFirst } = useFirstFileInspect()

const previewSrc = ref<string>()
const watermarkFile = ref<File>()

const watermarkOp = ref<WatermarkOp>({
  op: 'watermark',
  mode: 'text',
  text: '',
  position_x: 0.5,
  position_y: 0.5,
  scale: 0.5,
  opacity: 0.7,
  rotation: 0,
  white_veil: false,
  veil_opacity: 0.3,
})

const canRun = computed(() =>
  watermarkOp.value.mode === 'text' ? !!watermarkOp.value.text?.trim() : !!watermarkFile.value,
)

// Watermarking only overlays pixels — output keeps the source format at max
// quality, same rationale as /crop.
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
    await inspectFirst(files[0])
  }
}

async function run() {
  if (!canRun.value) return
  await runProcess({ ops: [watermarkOp.value], output: output.value }, watermarkFile.value)
}
</script>
