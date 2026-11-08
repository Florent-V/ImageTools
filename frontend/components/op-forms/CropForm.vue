<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">Recadrage</h3>
    </template>

    <div class="flex flex-col gap-4">
      <div v-if="!lockedRatio" class="flex gap-2">
        <UButton
          v-for="preset in ratioPresets"
          :key="preset.label"
          size="sm"
          :color="activeRatio === preset.label ? 'primary' : 'neutral'"
          :variant="activeRatio === preset.label ? 'solid' : 'outline'"
          @click="applyRatio(preset.ratio, preset.label)"
        >
          {{ preset.label }}
        </UButton>
      </div>

      <div
        ref="previewWrap"
        :class="[PREVIEW_WRAP_CLASS, box.selection.value ? 'cursor-default' : 'cursor-crosshair']"
        @pointerdown="box.onBackgroundPointerDown"
      >
        <img ref="previewImg" :src="previewSrc" :class="PREVIEW_IMG_CLASS" draggable="false" @load="onImageLoad" >
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
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { CropOp } from '~/utils/api'
import { PREVIEW_IMG_CLASS, PREVIEW_WRAP_CLASS } from '~/utils/previewLayout'
import { useBoxSelection, type DisplayBox } from '~/composables/useBoxSelection'

const props = defineProps<{
  modelValue: CropOp | null
  previewSrc: string
  imageWidth: number
  imageHeight: number
  lockedRatio?: number
}>()
const emit = defineEmits<{ 'update:modelValue': [value: CropOp] }>()

const ratioPresets = [
  { label: '1:1', ratio: 1 },
  { label: '16:9', ratio: 16 / 9 },
  { label: '4:3', ratio: 4 / 3 },
  { label: 'Libre', ratio: null },
]

const previewWrap = ref<HTMLElement>()
const previewImg = ref<HTMLImageElement>()
const activeRatio = ref('Libre')
const activeRatioValue = ref<number | null>(props.lockedRatio ?? null)

function emitFromSelection(selectionBox: DisplayBox, scale: number) {
  emit('update:modelValue', {
    op: 'crop',
    x: Math.round(selectionBox.left * scale),
    y: Math.round(selectionBox.top * scale),
    width: Math.round(selectionBox.width * scale),
    height: Math.round(selectionBox.height * scale),
  })
}

const box = useBoxSelection({
  previewWrap,
  previewImg,
  sourceWidth: () => props.imageWidth,
  ratio: () => activeRatioValue.value,
  onFreeform: () => {
    if (!props.lockedRatio) {
      activeRatio.value = 'Libre'
      activeRatioValue.value = null
    }
  },
  onChange: emitFromSelection,
})

function onImageLoad() {
  if (props.modelValue) {
    const scale = box.displayScale()
    box.applyBox({
      left: props.modelValue.x / scale,
      top: props.modelValue.y / scale,
      width: props.modelValue.width / scale,
      height: props.modelValue.height / scale,
    })
    return
  }
  if (props.lockedRatio) applyRatio(props.lockedRatio, 'Locked')
}

function applyRatio(ratio: number | null, label: string) {
  activeRatio.value = label
  activeRatioValue.value = ratio
  box.applyPreset(ratio)
}
</script>
