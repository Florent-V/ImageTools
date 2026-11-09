<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">
        Format
      </h3>
    </template>

    <div class="flex flex-col gap-4">
      <UFormField label="Format de sortie">
        <USelect
          v-model="local.format"
          :items="formats.write"
          class="max-w-40"
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
import type { FormatsResponse, OutputSpec } from '~/utils/api'

const props = defineProps<{ formats: FormatsResponse, modelValue: OutputSpec }>()
const emit = defineEmits<{ 'update:modelValue': [value: OutputSpec] }>()

// Convert only changes the container format — quality stays fixed at the
// format's max (100) so a format-only change keeps as much detail as the
// target format allows.
const local = reactive<OutputSpec>({ ...props.modelValue, preset: null, quality: 100, target_size_kb: null })

watch(
  local,
  value => emit('update:modelValue', { ...value }),
  { deep: true }
)

watch(
  () => props.modelValue,
  (newVal) => {
    if (JSON.stringify(newVal) !== JSON.stringify(local)) Object.assign(local, newVal)
  }
)
</script>
