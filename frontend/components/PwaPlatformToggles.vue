<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">Plateformes à générer</h3>
    </template>

    <div class="grid grid-cols-2 gap-3 sm:grid-cols-3">
      <UCheckbox v-model="local.android" label="Android / Chrome" />
      <UCheckbox v-model="local.ios" label="iOS (apple-touch-icon)" />
      <UCheckbox v-model="local.favicon" label="Favicon" />
      <UCheckbox v-model="local.windows" label="Windows tiles" />
      <UCheckbox v-model="local.splash" label="Splash screens iOS" />
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { PwaPlatforms } from '~/utils/api'

const props = defineProps<{ modelValue: PwaPlatforms }>()
const emit = defineEmits<{ 'update:modelValue': [value: PwaPlatforms] }>()

const local = reactive<PwaPlatforms>({ ...props.modelValue })

watch(local, (value) => emit('update:modelValue', { ...value }), { deep: true })
watch(
  () => props.modelValue,
  (newVal) => {
    if (JSON.stringify(newVal) !== JSON.stringify(local)) Object.assign(local, newVal)
  },
)
</script>
