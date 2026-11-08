<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Atelier</h1>
      <p class="mt-1 text-(--ui-text-muted)">Enchaînez plusieurs opérations en pipeline.</p>
    </div>

    <DropZone
      v-if="formats"
      :read-formats="formats.read"
      :max-file-size-mb="formats.limits.max_file_size_mb"
      @files-selected="onFilesSelected"
    />

    <div class="flex flex-wrap gap-2">
      <UButton icon="i-lucide-scaling" color="neutral" variant="outline" @click="addStep('resize')">
        Redimensionner
      </UButton>
      <UButton icon="i-lucide-rotate-cw" color="neutral" variant="outline" @click="addStep('rotate')">
        Rotation
      </UButton>
      <UButton
        icon="i-lucide-crop"
        color="neutral"
        variant="outline"
        :disabled="!inspected || hasGeometryStep"
        @click="addStep('crop')"
      >
        Recadrer
      </UButton>
      <UButton
        icon="i-lucide-file-down"
        color="neutral"
        variant="outline"
        :disabled="hasCompressStep"
        @click="addStep('compress')"
      >
        Compression
      </UButton>
      <UButton
        icon="i-lucide-refresh-cw"
        color="neutral"
        variant="outline"
        :disabled="hasConvertStep"
        @click="addStep('convert')"
      >
        Convertir
      </UButton>
    </div>

    <ol class="grid grid-cols-1 items-start gap-4 lg:grid-cols-2 xl:grid-cols-3">
      <li v-for="(step, index) in steps" :key="step.id" class="flex flex-col gap-2">
        <div class="flex gap-2">
          <UButton icon="i-lucide-arrow-up" size="sm" color="neutral" variant="ghost" :disabled="index === 0" @click="moveUp(index)" />
          <UButton icon="i-lucide-arrow-down" size="sm" color="neutral" variant="ghost" :disabled="index === steps.length - 1" @click="moveDown(index)" />
          <UButton icon="i-lucide-x" size="sm" color="error" variant="ghost" @click="removeStep(index)">Retirer</UButton>
        </div>
        <ResizeForm v-if="step.kind === 'resize'" v-model="step.value" />
        <RotateForm v-else-if="step.kind === 'rotate'" v-model="step.value" />
        <CropForm
          v-else-if="step.kind === 'crop' && previewSrc && inspected"
          v-model="step.value"
          :preview-src="previewSrc"
          :image-width="inspected.width"
          :image-height="inspected.height"
        />
        <QualityForm v-else-if="step.kind === 'compress'" v-model="output" />
        <FormatForm v-else-if="step.kind === 'convert' && formats" v-model="output" :formats="formats" />
      </li>
    </ol>

    <UAlert v-if="inspectError" color="error" variant="soft" icon="i-lucide-triangle-alert" :title="inspectError" />
    <UButton size="lg" icon="i-lucide-play" :loading="running" :disabled="!queue.length" class="self-start" @click="run">
      Traiter
    </UButton>
    <ImageQueue :items="queue" />
  </div>
</template>

<script setup lang="ts">
import type {
  CropOp,
  Operation,
  OutputSpec,
  ResizeOp,
  RotateOp,
} from '~/utils/api'
import { detectWritableFormat } from '~/utils/fileFormat'
import type { QueueItem } from '~/composables/useProcessor'

type PipelineStep =
  | { id: string; kind: 'resize'; value: ResizeOp }
  | { id: string; kind: 'rotate'; value: RotateOp }
  | { id: string; kind: 'crop'; value: CropOp }
  | { id: string; kind: 'compress' }
  | { id: string; kind: 'convert' }

const { formats, queue, enqueue, run: runProcess, running } = await useToolPage()
const { inspected, inspectError, inspectFirst } = useFirstFileInspect()

const previewSrc = ref<string>()
const steps = ref<PipelineStep[]>([])

// Nothing shown by default — the user builds the pipeline by adding tiles.
// "Compression"/"Convertir" tiles edit this shared output spec; without them
// each image keeps its own original format and quality (see buildOutput).
const output = ref<OutputSpec>({ format: 'jpeg', quality: 100, strip_metadata: false })

const hasGeometryStep = computed(() => steps.value.some((s) => s.kind === 'resize' || s.kind === 'rotate'))
const hasCompressStep = computed(() => steps.value.some((s) => s.kind === 'compress'))
const hasConvertStep = computed(() => steps.value.some((s) => s.kind === 'convert'))

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

function addStep(kind: PipelineStep['kind']) {
  const id = crypto.randomUUID()
  if (kind === 'compress' || kind === 'convert') {
    steps.value.push({ id, kind })
    return
  }
  const defaults: Record<'resize' | 'rotate' | 'crop', Operation> = {
    resize: { op: 'resize', width: null, height: null, keep_ratio: true, no_upscale: true } satisfies ResizeOp,
    rotate: { op: 'rotate', degrees: 0, flip_horizontal: false, flip_vertical: false } satisfies RotateOp,
    crop: {
      op: 'crop',
      x: 0,
      y: 0,
      width: inspected.value?.width ?? 0,
      height: inspected.value?.height ?? 0,
    } satisfies CropOp,
  }
  steps.value.push({ id, kind, value: defaults[kind] } as PipelineStep)
}

function removeStep(index: number) {
  steps.value.splice(index, 1)
}

function moveUp(index: number) {
  if (index === 0) return
  ;[steps.value[index - 1], steps.value[index]] = [steps.value[index]!, steps.value[index - 1]!]
}

function moveDown(index: number) {
  if (index === steps.value.length - 1) return
  ;[steps.value[index], steps.value[index + 1]] = [steps.value[index + 1]!, steps.value[index]!]
}

function isPipelineOp(step: PipelineStep): step is Extract<PipelineStep, { kind: 'resize' | 'rotate' | 'crop' }> {
  return step.kind === 'resize' || step.kind === 'rotate' || step.kind === 'crop'
}

// No convert tile -> keep each image's own original format. No compress
// tile -> keep max quality, no preset/target. Mirrors /compress and the
// /crop, /rotate "preserve original" defaults.
function buildOutput(item: QueueItem): OutputSpec {
  const originalFormat = detectWritableFormat(item.file.name) ?? 'jpeg'
  return {
    format: hasConvertStep.value ? output.value.format : originalFormat,
    quality: hasCompressStep.value ? (output.value.quality ?? null) : 100,
    preset: hasCompressStep.value ? (output.value.preset ?? null) : null,
    target_size_kb: hasCompressStep.value ? (output.value.target_size_kb ?? null) : null,
    strip_metadata: output.value.strip_metadata ?? false,
  }
}

async function run() {
  const ops = steps.value.filter(isPipelineOp).map((step) => step.value)
  await runProcess((item: QueueItem) => ({ ops, output: buildOutput(item) }))
}
</script>
