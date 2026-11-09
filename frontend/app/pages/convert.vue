<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">
        Convertir
      </h1>
      <p class="mt-1 text-(--ui-text-muted)">
        Changez le format de vos images sans toucher à la qualité.
      </p>
    </div>

    <DropZone
      v-if="formats"
      :read-formats="formats.read"
      :max-file-size-mb="formats.limits.max_file_size_mb"
      @files-selected="onFilesSelected"
    />
    <FormatForm
      v-if="formats"
      v-model="output"
      :formats="formats"
    />
    <UButton
      size="lg"
      icon="i-lucide-refresh-cw"
      :loading="running"
      :disabled="!queue.length"
      class="self-start"
      @click="run"
    >
      Convertir
    </UButton>
    <ImageQueue :items="queue" />
  </div>
</template>

<script setup lang="ts">
import type { OutputSpec } from '~/utils/api'

const { formats, queue, enqueue, run: runProcess, running } = await useToolPage()

const output = ref<OutputSpec>({ format: 'jpeg', quality: 100, strip_metadata: false })

function onFilesSelected(files: File[]) {
  enqueue(files)
}

async function run() {
  await runProcess({ ops: [], output: output.value })
}
</script>
