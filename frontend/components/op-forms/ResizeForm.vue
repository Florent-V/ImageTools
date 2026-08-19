<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">Redimensionnement</h3>
    </template>

    <div class="flex flex-col gap-4">
      <URadioGroup
        v-model="mode"
        orientation="horizontal"
        :items="[
          { label: 'Pixels', value: 'pixels' },
          { label: 'Pourcentage', value: 'percent' },
        ]"
      />

      <template v-if="mode === 'pixels'">
        <div class="flex gap-3">
          <UFormField label="Largeur">
            <UInput v-model.number="width" type="number" :min="1" placeholder="auto" class="max-w-28" />
          </UFormField>
          <UFormField label="Hauteur">
            <UInput v-model.number="height" type="number" :min="1" placeholder="auto" class="max-w-28" />
          </UFormField>
          <p v-if="local.keep_ratio && !referenceSize" class="self-end text-xs text-(--ui-text-muted)">
            Ajoutez une image pour calculer l'autre valeur automatiquement.
          </p>
        </div>
        <UCheckbox v-model="local.keep_ratio" label="Conserver les proportions" />
      </template>
      <UFormField v-else label="Pourcentage">
        <UInput v-model.number="percent" type="number" :min="1" :max="1000" class="max-w-28" />
      </UFormField>

      <UCheckbox v-model="local.no_upscale" label="Ne jamais agrandir" />
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { ResizeOp } from '~/utils/api'

const props = defineProps<{ modelValue: ResizeOp; referenceSize?: { width: number; height: number } | null }>()
const emit = defineEmits<{ 'update:modelValue': [value: ResizeOp] }>()

const local = reactive<ResizeOp>({ keep_ratio: true, no_upscale: true, ...props.modelValue, op: 'resize' })
const mode = ref<'pixels' | 'percent'>(local.percent ? 'percent' : 'pixels')
const width = ref<number | null>(local.width ?? null)
const height = ref<number | null>(local.height ?? null)
const percent = ref<number | null>(local.percent ?? null)

// Normalize initialization: if either width or height and percent are set, clear the one that doesn't match mode
if ((local.width || local.height) && local.percent) {
  if (mode.value === 'percent') {
    local.width = null
    local.height = null
  } else {
    local.percent = null
  }
}

watch(mode, (value) => {
  if (value === 'pixels') {
    local.percent = null
  } else {
    local.width = null
    local.height = null
  }
})

// Guards re-entrancy: setting the derived field below would otherwise
// re-trigger its own watcher and bounce back to recompute this one.
let syncingRatio = false

watch(width, (value) => {
  if (mode.value !== 'pixels' || syncingRatio) return
  local.width = value
  if (local.keep_ratio && value !== null && props.referenceSize) {
    syncingRatio = true
    height.value = Math.max(1, Math.round((value * props.referenceSize.height) / props.referenceSize.width))
    local.height = height.value
    syncingRatio = false
  } else if (local.keep_ratio && value !== null) {
    height.value = null
  }
})
watch(height, (value) => {
  if (mode.value !== 'pixels' || syncingRatio) return
  local.height = value
  if (local.keep_ratio && value !== null && props.referenceSize) {
    syncingRatio = true
    width.value = Math.max(1, Math.round((value * props.referenceSize.width) / props.referenceSize.height))
    local.width = width.value
    syncingRatio = false
  } else if (local.keep_ratio && value !== null) {
    width.value = null
  }
})
watch(percent, (value) => {
  if (mode.value === 'percent') local.percent = value
})

watch(
  local,
  (value) => emit('update:modelValue', { ...value }),
  { deep: true },
)

watch(
  () => props.modelValue,
  (newVal) => {
    // Only sync if the incoming value is actually different
    if (JSON.stringify(newVal) !== JSON.stringify(local)) {
      Object.assign(local, newVal)
      // Update mode and related refs based on new value
      mode.value = newVal.percent ? 'percent' : 'pixels'
      width.value = newVal.width ?? null
      height.value = newVal.height ?? null
      percent.value = newVal.percent ?? null
    }
  },
)
</script>
