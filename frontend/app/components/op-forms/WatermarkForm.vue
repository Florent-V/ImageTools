<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">
        Filigrane
      </h3>
    </template>

    <div class="flex flex-col gap-4">
      <div class="flex gap-2">
        <UButton
          size="sm"
          :color="op.mode === 'text' ? 'primary' : 'neutral'"
          :variant="op.mode === 'text' ? 'solid' : 'outline'"
          @click="op.mode = 'text'"
        >
          Texte
        </UButton>
        <UButton
          size="sm"
          :color="op.mode === 'image' ? 'primary' : 'neutral'"
          :variant="op.mode === 'image' ? 'solid' : 'outline'"
          @click="op.mode = 'image'"
        >
          Image
        </UButton>
      </div>

      <UInput
        v-if="op.mode === 'text'"
        v-model="textValue"
        placeholder="Texte du filigrane"
      />
      <div
        v-else
        class="flex flex-col gap-2"
      >
        <input
          ref="markInput"
          type="file"
          accept="image/*"
          class="sr-only"
          @change="onMarkPicked"
        >
        <UButton
          size="sm"
          variant="outline"
          icon="i-lucide-image-plus"
          @click="markInput?.click()"
        >
          {{ markFile ? markFile.name : 'Choisir une image' }}
        </UButton>
      </div>

      <div
        ref="previewWrap"
        :class="[PREVIEW_WRAP_CLASS, markReady ? 'cursor-move' : 'cursor-default']"
      >
        <img
          ref="previewImg"
          :src="previewSrc"
          :class="PREVIEW_IMG_CLASS"
          draggable="false"
          @load="onImageLoad"
        >
        <div
          v-if="op.white_veil"
          class="absolute inset-0 rounded-md bg-white pointer-events-none"
          :style="{ opacity: op.veil_opacity }"
        />
        <div
          v-if="markReady"
          class="absolute flex items-center justify-center overflow-hidden rounded-sm border border-dashed border-(--ui-primary)"
          :style="markStyle"
          @pointerdown="startMove"
        >
          <img
            v-if="op.mode === 'image' && markPreviewSrc"
            :src="markPreviewSrc"
            class="h-full w-full object-contain"
            draggable="false"
          >
          <span
            v-else
            class="whitespace-nowrap font-bold text-black"
            :style="{ fontSize: `${textFontSizePx}px` }"
          >
            {{ op.text || 'Texte' }}
          </span>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-4">
        <div class="flex items-center gap-2">
          <span class="text-sm text-(--ui-text-muted)">Taille</span>
          <UButton
            size="sm"
            variant="outline"
            icon="i-lucide-minus"
            @click="adjustScale(-0.05)"
          />
          <span class="w-12 text-center text-sm tabular-nums">{{ Math.round(op.scale * 100) }}%</span>
          <UButton
            size="sm"
            variant="outline"
            icon="i-lucide-plus"
            @click="adjustScale(0.05)"
          />
        </div>

        <div class="flex min-w-40 flex-1 items-center gap-2">
          <span class="text-sm text-(--ui-text-muted)">Opacité</span>
          <USlider
            v-model="opacityPercent"
            :min="0"
            :max="100"
            class="flex-1"
          />
          <span class="w-10 text-right text-sm tabular-nums">{{ opacityPercent }}%</span>
        </div>

        <div class="flex min-w-40 flex-1 items-center gap-2">
          <span class="text-sm text-(--ui-text-muted)">Rotation</span>
          <USlider
            v-model="rotationValue"
            :min="-180"
            :max="180"
            class="flex-1"
          />
          <span class="w-12 text-right text-sm tabular-nums">{{ op.rotation ?? 0 }}°</span>
        </div>
      </div>

      <div class="flex flex-wrap items-center gap-4">
        <UCheckbox
          v-model="op.white_veil"
          label="Voile blanc (toute la photo)"
        />
        <div
          v-if="op.white_veil"
          class="flex min-w-40 flex-1 items-center gap-2"
        >
          <span class="text-sm text-(--ui-text-muted)">Opacité du voile</span>
          <USlider
            v-model="veilOpacityPercent"
            :min="0"
            :max="100"
            class="flex-1"
          />
          <span class="w-10 text-right text-sm tabular-nums">{{ veilOpacityPercent }}%</span>
        </div>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { WatermarkOp } from '~/utils/api'
import { PREVIEW_IMG_CLASS, PREVIEW_WRAP_CLASS, relativePoint } from '~/utils/previewLayout'
import { usePointerDrag } from '~/composables/usePointerDrag'

const props = defineProps<{
  modelValue: WatermarkOp
  previewSrc: string
}>()
const emit = defineEmits<{
  'update:modelValue': [value: WatermarkOp]
  'watermark-file': [file: File | undefined]
}>()

const op = reactive<WatermarkOp>({ ...props.modelValue })
watch(op, value => emit('update:modelValue', { ...value }), { deep: true })
watch(
  () => props.modelValue,
  value => Object.assign(op, value)
)

const previewWrap = ref<HTMLElement>()
const previewImg = ref<HTMLImageElement>()
const markInput = ref<HTMLInputElement>()
const markFile = ref<File>()
const markPreviewSrc = ref<string>()
const markNaturalRatio = ref(1) // height / width, for sizing the image preview box
const imageReady = ref(false)

const markReady = computed(() => imageReady.value && (op.mode === 'text' ? !!op.text : !!markPreviewSrc.value))

function onImageLoad() {
  imageReady.value = true
}

function onMarkPicked(event: Event) {
  const file = (event.target as HTMLInputElement).files?.[0]
  if (!file) return
  if (markPreviewSrc.value) URL.revokeObjectURL(markPreviewSrc.value)
  markFile.value = file
  markPreviewSrc.value = URL.createObjectURL(file)
  emit('watermark-file', file)
  const img = new Image()
  img.onload = () => {
    markNaturalRatio.value = img.height / img.width
  }
  img.src = markPreviewSrc.value
}

onBeforeUnmount(() => {
  if (markPreviewSrc.value) URL.revokeObjectURL(markPreviewSrc.value)
})

function adjustScale(delta: number) {
  op.scale = Math.min(2, Math.max(0.05, Math.round((op.scale + delta) * 100) / 100))
}

const textValue = computed({
  get: () => op.text ?? '',
  set: (value: string) => (op.text = value)
})

const opacityPercent = computed({
  get: () => Math.round(op.opacity * 100),
  set: (value: number) => (op.opacity = value / 100)
})

const veilOpacityPercent = computed({
  get: () => Math.round((op.veil_opacity ?? 0.3) * 100),
  set: (value: number) => (op.veil_opacity = value / 100)
})

const rotationValue = computed({
  get: () => op.rotation ?? 0,
  set: (value: number) => (op.rotation = value)
})

// Text box has no natural width/height like an image does; approximate the
// display box from character count so drag/position math has a target size.
const markStyle = computed(() => {
  const bounds = { width: previewImg.value?.clientWidth ?? 0, height: previewImg.value?.clientHeight ?? 0 }
  const width = bounds.width * op.scale
  const height = op.mode === 'image' ? width * markNaturalRatio.value : width / Math.max(1, (op.text?.length || 4) * 0.55)
  const left = op.position_x * bounds.width - width / 2
  const top = op.position_y * bounds.height - height / 2
  return {
    left: `${left}px`,
    top: `${top}px`,
    width: `${width}px`,
    height: `${height}px`,
    transform: `rotate(${op.rotation ?? 0}deg)`,
    opacity: op.opacity
  }
})

const textFontSizePx = computed(() => {
  const bounds = { width: previewImg.value?.clientWidth ?? 0 }
  const width = bounds.width * op.scale
  return Math.max(6, width / Math.max(1, (op.text?.length || 4) * 0.55) * 0.7)
})

let moveStart: { x: number, y: number, posX: number, posY: number } | null = null

const drag = usePointerDrag(
  (event) => {
    if (!moveStart || !previewImg.value) return
    const pos = relativePoint(event, previewWrap.value!)
    const bounds = { width: previewImg.value.clientWidth, height: previewImg.value.clientHeight }
    if (!bounds.width || !bounds.height) return
    const dx = (pos.x - moveStart.x) / bounds.width
    const dy = (pos.y - moveStart.y) / bounds.height
    op.position_x = Math.min(1, Math.max(0, moveStart.posX + dx))
    op.position_y = Math.min(1, Math.max(0, moveStart.posY + dy))
  },
  () => {
    moveStart = null
  }
)

function startMove(event: PointerEvent) {
  const pos = relativePoint(event, previewWrap.value!)
  moveStart = { x: pos.x, y: pos.y, posX: op.position_x, posY: op.position_y }
  drag.start(event)
}
</script>
