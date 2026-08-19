<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Redimensionner</h1>
      <p class="mt-1 text-(--ui-text-muted)">En pixels ou en pourcentage, avec ou sans respect des proportions.</p>
    </div>

    <DropZone
      v-if="formats"
      :read-formats="formats.read"
      :max-file-size-mb="formats.limits.max_file_size_mb"
      @files-selected="onFilesSelected"
    />
    <ResizeForm v-model="resizeOp" :reference-size="referenceSize" />
    <FormatForm v-if="formats" v-model="output" :formats="formats" />
    <UButton size="lg" icon="i-lucide-scaling" :loading="running" :disabled="!queue.length" class="self-start" @click="run">
      Redimensionner
    </UButton>
    <ImageQueue :items="queue" :resize-op="resizeOp" />
  </div>
</template>

<script setup lang="ts">
import { fetchFormats, type OutputSpec, type ResizeOp } from '~/utils/api'

const { data: formats } = await useAsyncData('formats', fetchFormats, { server: false })
const { queue, enqueue, process } = useProcessor()

const resizeOp = ref<ResizeOp>({ op: 'resize', width: null, height: null, keep_ratio: true, no_upscale: true })
// Resize never re-encodes lossily on its own — quality stays fixed at the
// format's max, same rationale as FormatForm on the /convert page.
const output = ref<OutputSpec>({ format: 'jpeg', quality: 100, strip_metadata: false })
const running = ref(false)

// Live width<->height linking needs some aspect ratio to compute against —
// the first queued image with known dimensions stands in for it. Backend
// still fits each image to this box independently (see resize.py), so a
// mismatched reference never distorts other images, only what the form shows.
const referenceSize = computed(() => {
  const first = queue.value.find((item) => item.originalWidth && item.originalHeight)
  return first ? { width: first.originalWidth!, height: first.originalHeight! } : null
})

function onFilesSelected(files: File[]) {
  enqueue(files)
}

async function run() {
  running.value = true
  try {
    await process({ ops: [resizeOp.value], output: output.value })
  } finally {
    running.value = false
  }
}
</script>
