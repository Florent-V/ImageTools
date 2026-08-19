<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">Sortie</h3>
    </template>

    <div class="flex flex-col gap-4">
      <UFormField label="Format">
        <USelect v-model="local.format" :items="formats.write" class="max-w-40" />
      </UFormField>

      <URadioGroup
        v-model="qualityMode"
        orientation="horizontal"
        :items="[
          { label: 'Préréglage', value: 'preset' },
          { label: 'Poids cible', value: 'target_size' },
        ]"
      />

      <div v-if="qualityMode === 'preset'" class="flex gap-2">
        <UButton
          v-for="preset in presetNames"
          :key="preset"
          size="sm"
          :color="local.preset === preset ? 'primary' : 'neutral'"
          :variant="local.preset === preset ? 'solid' : 'outline'"
          @click="local.preset = preset"
        >
          {{ preset }}
        </UButton>
      </div>
      <UFormField v-else label="Poids cible (Ko)">
        <UInput v-model.number="targetSizeKb" type="number" :min="1" class="max-w-32" />
      </UFormField>

      <UCheckbox v-model="local.strip_metadata" label="Retirer les métadonnées EXIF" />
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { FormatsResponse, OutputSpec, Preset } from '~/utils/api'

const props = defineProps<{ formats: FormatsResponse; modelValue: OutputSpec }>()
const emit = defineEmits<{ 'update:modelValue': [value: OutputSpec] }>()

// Keep in sync with backend/app/schemas/request.py's Preset and utils/api.ts's Preset type.
const presetNames = ['light', 'recommended', 'strong'] as const

const local = reactive<OutputSpec>({ ...props.modelValue })
const qualityMode = ref<'preset' | 'target_size'>(local.target_size_kb ? 'target_size' : 'preset')
const targetSizeKb = ref<number | null>(local.target_size_kb ?? null)

// Normalize initialization: if both preset and target_size_kb are set, clear the one that doesn't match qualityMode
if (local.preset && local.target_size_kb) {
  if (qualityMode.value === 'target_size') {
    local.preset = null
  } else {
    local.target_size_kb = null
  }
}

watch(qualityMode, (mode) => {
  if (mode === 'preset') {
    local.target_size_kb = null
    local.preset = local.preset ?? ('recommended' as Preset)
  } else {
    local.preset = null
  }
})

watch(targetSizeKb, (value) => {
  local.target_size_kb = qualityMode.value === 'target_size' ? value : null
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
      // Update qualityMode and targetSizeKb based on new value
      qualityMode.value = newVal.target_size_kb ? 'target_size' : 'preset'
      targetSizeKb.value = newVal.target_size_kb ?? null
    }
  },
)
</script>
