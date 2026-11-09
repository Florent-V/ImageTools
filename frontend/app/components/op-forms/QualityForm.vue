<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">
        Compression
      </h3>
    </template>

    <div class="flex flex-col gap-4">
      <p class="text-xs text-(--ui-text-muted)">
        Le format d'origine de chaque image est conservé.
      </p>

      <URadioGroup
        v-model="qualityMode"
        orientation="horizontal"
        :items="[
          { label: 'Préréglage', value: 'preset' },
          { label: 'Poids cible', value: 'target_size' }
        ]"
      />

      <div
        v-if="qualityMode === 'preset'"
        class="flex flex-col gap-2"
      >
        <div class="flex gap-2">
          <UButton
            v-for="preset in presetNames"
            :key="preset"
            size="sm"
            :color="local.preset === preset ? 'primary' : 'neutral'"
            :variant="local.preset === preset ? 'solid' : 'outline'"
            @click="local.preset = preset"
          >
            {{ PRESET_LABELS[preset] }}
          </UButton>
        </div>
        <p class="text-xs text-(--ui-text-muted)">
          {{ PRESET_DESCRIPTIONS[local.preset ?? 'recommended'] }}
        </p>
      </div>
      <UFormField
        v-else
        label="Poids cible (Ko)"
      >
        <UInput
          v-model.number="targetSizeKb"
          type="number"
          :min="1"
          class="max-w-32"
        />
      </UFormField>

      <UCheckbox
        v-model="local.strip_metadata"
        label="Retirer les métadonnées EXIF"
      />
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { OutputSpec, Preset } from '~/utils/api'

const props = defineProps<{ modelValue: OutputSpec }>()
const emit = defineEmits<{ 'update:modelValue': [value: OutputSpec] }>()

// Keep in sync with backend/app/schemas/request.py's Preset.
const presetNames = ['light', 'recommended', 'strong'] as const

const PRESET_LABELS: Record<(typeof presetNames)[number], string> = {
  light: 'Léger',
  recommended: 'Équilibré',
  strong: 'Fort'
}

const PRESET_DESCRIPTIONS: Record<(typeof presetNames)[number], string> = {
  light: 'Qualité quasi intacte, gain de poids modeste.',
  recommended: 'Bon compromis qualité / poids — recommandé pour la plupart des cas.',
  strong: 'Poids minimal, perte de qualité visible sur les détails fins.'
}

const local = reactive<OutputSpec>({ ...props.modelValue })
const qualityMode = ref<'preset' | 'target_size'>(local.target_size_kb ? 'target_size' : 'preset')
const targetSizeKb = ref<number | null>(local.target_size_kb ?? null)

if (!local.preset && !local.target_size_kb) local.preset = 'recommended' as Preset

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
  value => emit('update:modelValue', { ...value }),
  { deep: true }
)

watch(
  () => props.modelValue,
  (newVal) => {
    if (JSON.stringify(newVal) !== JSON.stringify(local)) {
      Object.assign(local, newVal)
      qualityMode.value = newVal.target_size_kb ? 'target_size' : 'preset'
      targetSizeKb.value = newVal.target_size_kb ?? null
    }
  }
)
</script>
