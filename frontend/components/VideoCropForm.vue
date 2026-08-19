<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">Recadrage</h3>
    </template>

    <div class="flex flex-col gap-4">
      <div class="flex flex-wrap gap-2">
        <UButton
          v-for="preset in ratioPresets"
          :key="preset.id"
          size="sm"
          :color="activePresetId === preset.id ? 'primary' : 'neutral'"
          :variant="activePresetId === preset.id ? 'solid' : 'outline'"
          @click="selectPreset(preset)"
        >
          {{ preset.label }}
        </UButton>
      </div>

      <div
        ref="previewWrap"
        :class="[PREVIEW_WRAP_CLASS, selection ? 'cursor-default' : 'cursor-crosshair']"
        @pointerdown="onBackgroundPointerDown"
      >
        <img :src="currentPreviewSrc" ref="previewImg" :class="PREVIEW_IMG_CLASS" @load="onImageLoad" draggable="false" />
        <div
          v-if="selection"
          class="absolute border-2 border-(--ui-primary) bg-(--ui-primary)/15 cursor-move"
          :style="{
            left: `${selection.left}px`,
            top: `${selection.top}px`,
            width: `${selection.width}px`,
            height: `${selection.height}px`,
          }"
          @pointerdown.stop="startMove"
        >
          <div
            v-for="handle in handles"
            :key="handle.id"
            class="absolute w-3 h-3 rounded-full bg-(--ui-bg) border-2 border-(--ui-primary)"
            :style="{ left: handle.left, top: handle.top, cursor: handle.cursor, transform: 'translate(-50%, -50%)' }"
            @pointerdown.stop="(event: PointerEvent) => startResize(event, handle.id)"
          />
        </div>
      </div>

      <UFormField v-if="durationS > 0" label="Image de référence (si la première image est noire)">
        <div class="flex items-center gap-3">
          <input
            v-model.number="scrubTimestamp"
            type="range"
            min="0"
            :max="durationS"
            step="0.1"
            class="w-full"
            @input="onScrub"
          />
          <span class="w-12 shrink-0 text-right text-xs text-(--ui-text-muted)">{{ scrubTimestamp.toFixed(1) }}s</span>
        </div>
      </UFormField>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import { PREVIEW_IMG_CLASS, PREVIEW_WRAP_CLASS } from '~/utils/previewLayout'
import { fetchVideoFrame, type VideoCropRect, type VideoRatioPreset } from '~/utils/api'

const props = defineProps<{
  modelValue: { crop: VideoCropRect | null }
  previewSrc: string
  videoWidth: number
  videoHeight: number
  ratioPresets: VideoRatioPreset[]
  file: File
  durationS: number
}>()
const emit = defineEmits<{
  'update:modelValue': [value: { crop: VideoCropRect | null }]
}>()

type HandleId = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w'
const handles: { id: HandleId; left: string; top: string; cursor: string }[] = [
  { id: 'nw', left: '0%', top: '0%', cursor: 'nwse-resize' },
  { id: 'n', left: '50%', top: '0%', cursor: 'ns-resize' },
  { id: 'ne', left: '100%', top: '0%', cursor: 'nesw-resize' },
  { id: 'e', left: '100%', top: '50%', cursor: 'ew-resize' },
  { id: 'se', left: '100%', top: '100%', cursor: 'nwse-resize' },
  { id: 's', left: '50%', top: '100%', cursor: 'ns-resize' },
  { id: 'sw', left: '0%', top: '100%', cursor: 'nesw-resize' },
  { id: 'w', left: '0%', top: '50%', cursor: 'ew-resize' },
]

const previewWrap = ref<HTMLElement>()
const previewImg = ref<HTMLImageElement>()
const activePresetId = ref(props.ratioPresets[0]?.id ?? '')
const activeRatioValue = ref<number | null>(null)
const scrubTimestamp = ref(0)
const scrubbedPreviewSrc = ref<string>()
let scrubDebounce: ReturnType<typeof setTimeout> | undefined

const currentPreviewSrc = computed(() => scrubbedPreviewSrc.value ?? props.previewSrc)

interface DisplayBox {
  left: number
  top: number
  width: number
  height: number
}
const selection = ref<DisplayBox | null>(null)

// One of: creating a fresh box by dragging on the background, moving the
// whole box, or resizing from a specific handle. Null when idle.
type Interaction =
  | { kind: 'create'; originX: number; originY: number }
  | { kind: 'move'; grabX: number; grabY: number; start: DisplayBox }
  | { kind: 'resize'; handle: HandleId; start: DisplayBox }
  | null
const interaction = ref<Interaction>(null)

const librePreset = computed(() => props.ratioPresets.find((p) => p.ratio === null))

function displayScale(): number {
  if (!previewImg.value || previewImg.value.clientWidth === 0 || props.videoWidth === 0) return 1
  return props.videoWidth / previewImg.value.clientWidth
}

function displayBounds(): { width: number; height: number } {
  return { width: previewImg.value?.clientWidth ?? 0, height: previewImg.value?.clientHeight ?? 0 }
}

function clampBox(box: DisplayBox): DisplayBox {
  const bounds = displayBounds()
  const width = Math.min(box.width, bounds.width)
  const height = Math.min(box.height, bounds.height)
  return {
    width,
    height,
    left: Math.min(Math.max(box.left, 0), bounds.width - width),
    top: Math.min(Math.max(box.top, 0), bounds.height - height),
  }
}

function emitFromSelection(box: DisplayBox) {
  const scale = displayScale()
  const crop: VideoCropRect = {
    x: Math.round(box.left * scale),
    y: Math.round(box.top * scale),
    width: Math.round(box.width * scale),
    height: Math.round(box.height * scale),
  }
  emit('update:modelValue', { crop })
}

function onImageLoad() {
  if (props.modelValue.crop) {
    const scale = displayScale()
    selection.value = {
      left: props.modelValue.crop.x / scale,
      top: props.modelValue.crop.y / scale,
      width: props.modelValue.crop.width / scale,
      height: props.modelValue.crop.height / scale,
    }
    return
  }
  if (props.ratioPresets[0]) selectPreset(props.ratioPresets[0])
}

function selectPreset(preset: VideoRatioPreset) {
  activePresetId.value = preset.id
  activeRatioValue.value = preset.ratio ? preset.ratio[0] / preset.ratio[1] : null
  if (!previewImg.value) return
  const { width: displayWidth, height: displayHeight } = displayBounds()
  let width = displayWidth * 0.8
  let height = activeRatioValue.value ? width / activeRatioValue.value : displayHeight * 0.8
  if (height > displayHeight) {
    height = displayHeight * 0.8
    width = activeRatioValue.value ? height * activeRatioValue.value : width
  }
  const box: DisplayBox = {
    left: (displayWidth - width) / 2,
    top: (displayHeight - height) / 2,
    width,
    height,
  }
  selection.value = box
  emitFromSelection(box)
}

function relativePosition(event: PointerEvent): { x: number; y: number } {
  const rect = previewWrap.value!.getBoundingClientRect()
  return { x: event.clientX - rect.left, y: event.clientY - rect.top }
}

function capture(event: PointerEvent) {
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
}

function onBackgroundPointerDown(event: PointerEvent) {
  // Selection body/handles stop propagation before reaching here, so this
  // only fires for clicks on empty image area -> start a fresh free box.
  if (librePreset.value) {
    activePresetId.value = librePreset.value.id
    activeRatioValue.value = null
  }
  const origin = relativePosition(event)
  interaction.value = { kind: 'create', originX: origin.x, originY: origin.y }
  selection.value = { left: origin.x, top: origin.y, width: 0, height: 0 }
  capture(event)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
}

function startMove(event: PointerEvent) {
  if (!selection.value) return
  const pos = relativePosition(event)
  interaction.value = { kind: 'move', grabX: pos.x, grabY: pos.y, start: { ...selection.value } }
  capture(event)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
}

function startResize(event: PointerEvent, handle: HandleId) {
  if (!selection.value) return
  interaction.value = { kind: 'resize', handle, start: { ...selection.value } }
  capture(event)
  window.addEventListener('pointermove', onPointerMove)
  window.addEventListener('pointerup', onPointerUp)
}

function onPointerMove(event: PointerEvent) {
  const current = interaction.value
  if (!current || !previewWrap.value) return
  const pos = relativePosition(event)
  const bounds = displayBounds()

  if (current.kind === 'create') {
    const left = Math.min(current.originX, pos.x)
    const top = Math.min(current.originY, pos.y)
    let width = Math.abs(pos.x - current.originX)
    let height = Math.abs(pos.y - current.originY)
    if (activeRatioValue.value) height = width / activeRatioValue.value
    selection.value = clampBox({ left, top, width, height })
    return
  }

  if (current.kind === 'move') {
    const dx = pos.x - current.grabX
    const dy = pos.y - current.grabY
    const width = current.start.width
    const height = current.start.height
    selection.value = {
      left: Math.min(Math.max(current.start.left + dx, 0), bounds.width - width),
      top: Math.min(Math.max(current.start.top + dy, 0), bounds.height - height),
      width,
      height,
    }
    return
  }

  // resize: keep the edge/corner opposite the dragged handle fixed.
  const { handle, start } = current
  const right = start.left + start.width
  const bottom = start.top + start.height
  let left = start.left
  let top = start.top
  let width = start.width
  let height = start.height

  const clampedX = Math.min(Math.max(pos.x, 0), bounds.width)
  const clampedY = Math.min(Math.max(pos.y, 0), bounds.height)

  if (handle.includes('w')) {
    left = Math.min(clampedX, right - 1)
    width = right - left
  } else if (handle.includes('e')) {
    width = Math.max(clampedX - left, 1)
  }
  if (handle.includes('n')) {
    top = Math.min(clampedY, bottom - 1)
    height = bottom - top
  } else if (handle.includes('s')) {
    height = Math.max(clampedY - top, 1)
  }

  const ratio = activeRatioValue.value
  if (ratio) {
    if (handle === 'n' || handle === 's') {
      // vertical-only handle: derive width from height, keep box centered on its horizontal midpoint
      const midX = start.left + start.width / 2
      width = height * ratio
      left = midX - width / 2
    } else if (handle === 'e' || handle === 'w') {
      const midY = start.top + start.height / 2
      height = width / ratio
      top = midY - height / 2
    } else {
      // corner handle: derive height from width, keep the opposite corner fixed
      height = width / ratio
      if (handle.includes('n')) top = bottom - height
    }
  }

  selection.value = clampBox({ left, top, width, height })
}

function onPointerUp() {
  const current = interaction.value
  interaction.value = null
  window.removeEventListener('pointermove', onPointerMove)
  window.removeEventListener('pointerup', onPointerUp)
  if (!current || !selection.value) return
  if (current.kind === 'create' && (selection.value.width <= 4 || selection.value.height <= 4)) {
    selection.value = null
    return
  }
  emitFromSelection(selection.value)
}

function onScrub() {
  if (scrubDebounce) clearTimeout(scrubDebounce)
  scrubDebounce = setTimeout(async () => {
    const { preview_frame } = await fetchVideoFrame(props.file, scrubTimestamp.value)
    scrubbedPreviewSrc.value = preview_frame
  }, 300)
}
</script>
