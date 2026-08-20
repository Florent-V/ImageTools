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
        :class="[PREVIEW_WRAP_CLASS, box.selection.value ? 'cursor-default' : 'cursor-crosshair']"
        @pointerdown="box.onBackgroundPointerDown"
      >
        <img :src="currentPreviewSrc" ref="previewImg" :class="PREVIEW_IMG_CLASS" @load="onImageLoad" draggable="false" />
        <div
          v-if="box.selection.value"
          class="absolute border-2 border-(--ui-primary) bg-(--ui-primary)/15 cursor-move"
          :style="{
            left: `${box.selection.value.left}px`,
            top: `${box.selection.value.top}px`,
            width: `${box.selection.value.width}px`,
            height: `${box.selection.value.height}px`,
          }"
          @pointerdown.stop="box.startMove"
        >
          <div
            v-for="handle in box.handles"
            :key="handle.id"
            class="absolute w-3 h-3 rounded-full bg-(--ui-bg) border-2 border-(--ui-primary)"
            :style="{ left: handle.left, top: handle.top, cursor: handle.cursor, transform: 'translate(-50%, -50%)' }"
            @pointerdown.stop="(event: PointerEvent) => box.startResize(event, handle.id)"
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
import { useBoxSelection, type DisplayBox } from '~/composables/useBoxSelection'
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

const previewWrap = ref<HTMLElement>()
const previewImg = ref<HTMLImageElement>()
const activePresetId = ref(props.ratioPresets[0]?.id ?? '')
const activeRatioValue = ref<number | null>(null)
const scrubTimestamp = ref(0)
const scrubbedPreviewSrc = ref<string>()
let scrubDebounce: ReturnType<typeof setTimeout> | undefined

const currentPreviewSrc = computed(() => scrubbedPreviewSrc.value ?? props.previewSrc)
const librePreset = computed(() => props.ratioPresets.find((p) => p.ratio === null))

function emitFromSelection(selectionBox: DisplayBox, scale: number) {
  emit('update:modelValue', {
    crop: {
      x: Math.round(selectionBox.left * scale),
      y: Math.round(selectionBox.top * scale),
      width: Math.round(selectionBox.width * scale),
      height: Math.round(selectionBox.height * scale),
    },
  })
}

const box = useBoxSelection({
  previewWrap,
  previewImg,
  sourceWidth: () => props.videoWidth,
  ratio: () => activeRatioValue.value,
  onFreeform: () => {
    if (librePreset.value) {
      activePresetId.value = librePreset.value.id
      activeRatioValue.value = null
    }
  },
  onChange: emitFromSelection,
})

function onImageLoad() {
  if (props.modelValue.crop) {
    const scale = box.displayScale()
    box.applyBox({
      left: props.modelValue.crop.x / scale,
      top: props.modelValue.crop.y / scale,
      width: props.modelValue.crop.width / scale,
      height: props.modelValue.crop.height / scale,
    })
    return
  }
  if (props.ratioPresets[0]) selectPreset(props.ratioPresets[0])
}

function selectPreset(preset: VideoRatioPreset) {
  activePresetId.value = preset.id
  activeRatioValue.value = preset.ratio ? preset.ratio[0] / preset.ratio[1] : null
  box.applyPreset(activeRatioValue.value)
}

function onScrub() {
  if (scrubDebounce) clearTimeout(scrubDebounce)
  scrubDebounce = setTimeout(async () => {
    const { preview_frame } = await fetchVideoFrame(props.file, scrubTimestamp.value)
    scrubbedPreviewSrc.value = preview_frame
  }, 300)
}
</script>
