<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">
        Rotation / miroir
      </h1>
      <p class="mt-1 text-(--ui-text-muted)">
        90°, 180°, 270°, retournement horizontal et vertical.
      </p>
    </div>

    <DropZone
      v-if="formats"
      :read-formats="formats.read"
      :max-file-size-mb="formats.limits.max_file_size_mb"
      @files-selected="onFilesSelected"
    />
    <RotateForm v-model="rotateOp" />
    <UAlert
      v-if="inspectError"
      color="error"
      variant="soft"
      icon="i-lucide-triangle-alert"
      :title="inspectError"
    />
    <UButton
      size="lg"
      icon="i-lucide-rotate-cw"
      :loading="running"
      :disabled="!queue.length"
      class="self-start"
      @click="run"
    >
      Appliquer
    </UButton>
    <ImageQueue :items="queue" />
  </div>
</template>

<script setup lang="ts">
import type { OutputSpec, RotateOp } from '~/utils/api'

const { formats, queue, enqueue, run: runProcess, running } = await useToolPage()
const { inspected, inspectError, inspectFirst } = useFirstFileInspect()

const rotateOp = ref<RotateOp>({ op: 'rotate', degrees: 0, flip_horizontal: false, flip_vertical: false })

// Rotate only reorders pixels — output keeps the source format at max
// quality, metadata untouched, no other transformation (no OutputForm here).
const output = computed<OutputSpec>(() => {
  const raw = inspected.value?.format.toLowerCase()
  const format = raw === 'jpg' ? 'jpeg' : raw
  const supported = format && formats.value?.write.includes(format)
  return { format: supported ? (format as OutputSpec['format']) : 'png', quality: 100, strip_metadata: false }
})

async function onFilesSelected(files: File[]) {
  enqueue(files)
  if (!inspected.value && files[0]) {
    await inspectFirst(files[0])
  }
}

async function run() {
  await runProcess({ ops: [rotateOp.value], output: output.value })
}
</script>
