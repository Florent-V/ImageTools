<template>
  <div class="flex items-center gap-2">
    <span v-if="label" class="text-sm text-(--ui-text-muted)">{{ label }}</span>
    <input
      type="color"
      :value="modelValue"
      class="h-8 w-8 cursor-pointer rounded-md border border-(--ui-border) bg-transparent p-0.5"
      @input="emit('update:modelValue', ($event.target as HTMLInputElement).value)"
    >
  </div>
</template>

<script setup lang="ts">
defineProps<{
  modelValue: string
  label?: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: string] }>()
</script>
