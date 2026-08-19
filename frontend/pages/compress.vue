<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Compresser</h1>
      <p class="mt-1 text-(--ui-text-muted)">Réduisez le poids de vos images sans changer leur format.</p>
    </div>

    <DropZone
      v-if="formats"
      :read-formats="formats.read"
      :max-file-size-mb="formats.limits.max_file_size_mb"
      @files-selected="onFilesSelected"
    />
    <QualityForm v-if="formats" v-model="output" />
    <UAlert
      v-if="unwritableNames.length"
      color="warning"
      variant="soft"
      icon="i-lucide-triangle-alert"
      :title="`Format non compressible tel quel, converti en JPEG : ${unwritableNames.join(', ')}`"
    />
    <UButton size="lg" icon="i-lucide-file-down" :loading="running" :disabled="!queue.length" class="self-start" @click="run">
      Compresser
    </UButton>
    <ImageQueue :items="queue" />
  </div>
</template>

<script setup lang="ts">
import { fetchFormats, type OutputSpec } from '~/utils/api'
import { detectWritableFormat } from '~/utils/fileFormat'
import type { QueueItem } from '~/composables/useProcessor'

const { data: formats } = await useAsyncData('formats', fetchFormats, { server: false })
const { queue, enqueue, process } = useProcessor()

// format is a placeholder here — the actual per-file format is resolved at
// request-build time in run() so each image keeps its own original format.
const output = ref<OutputSpec>({ format: 'jpeg', preset: 'recommended', strip_metadata: false })
const running = ref(false)

const unwritableNames = computed(() =>
  queue.value.filter((item) => !detectWritableFormat(item.file.name)).map((item) => item.file.name),
)

function onFilesSelected(files: File[]) {
  enqueue(files)
}

async function run() {
  running.value = true
  try {
    await process((item: QueueItem) => ({
      ops: [],
      output: { ...output.value, format: detectWritableFormat(item.file.name) ?? 'jpeg' },
    }))
  } finally {
    running.value = false
  }
}
</script>
