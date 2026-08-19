<template>
  <div class="flex items-center gap-2">
    <span v-if="label" class="text-sm text-(--ui-text-muted)">{{ label }}</span>
    <UButton size="sm" variant="outline" icon="i-lucide-minus" @click="step(-1)" />
    <span class="w-12 text-center text-sm tabular-nums">{{ Math.round(modelValue * 100) }}%</span>
    <UButton size="sm" variant="outline" icon="i-lucide-plus" @click="step(1)" />
  </div>
</template>

<script setup lang="ts">
// Value is a fraction of the source image width (like WatermarkOp.scale), so
// a step stays proportional to the original resolution regardless of how
// large the preview is displayed.
const props = defineProps<{
  modelValue: number
  step: number
  min: number
  max: number
  label?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: number] }>()

function step(direction: 1 | -1) {
  const next = Math.round((props.modelValue + direction * props.step) * 1000) / 1000
  emit('update:modelValue', Math.min(props.max, Math.max(props.min, next)))
}
</script>
