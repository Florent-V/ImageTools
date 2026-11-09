<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">
        Rotation / miroir
      </h3>
    </template>

    <div class="flex flex-col gap-4">
      <div class="flex gap-2">
        <UButton
          v-for="deg in ([0, 90, 180, 270] as const)"
          :key="deg"
          size="sm"
          :color="local.degrees === deg ? 'primary' : 'neutral'"
          :variant="local.degrees === deg ? 'solid' : 'outline'"
          @click="local.degrees = deg"
        >
          {{ deg }}°
        </UButton>
      </div>

      <UCheckbox
        v-model="local.flip_horizontal"
        label="Miroir horizontal"
      />
      <UCheckbox
        v-model="local.flip_vertical"
        label="Miroir vertical"
      />
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { RotateOp } from '~/utils/api'

const props = defineProps<{ modelValue: RotateOp }>()
const emit = defineEmits<{ 'update:modelValue': [value: RotateOp] }>()

// op forced last so it always wins over props.modelValue — same pattern as ResizeForm.vue
const local = reactive<RotateOp>({
  degrees: 0,
  flip_horizontal: false,
  flip_vertical: false,
  ...props.modelValue,
  op: 'rotate'
})

watch(
  local,
  value => emit('update:modelValue', { ...value }),
  { deep: true }
)
</script>
