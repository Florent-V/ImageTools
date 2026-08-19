<script setup lang="ts">
const open = defineModel<boolean>('open', { default: false })

const route = useRoute()
watch(() => route.fullPath, () => {
  open.value = false
})

const colorClasses: Record<string, string> = {
  indigo: 'text-indigo-500 bg-indigo-500/10',
  amber: 'text-amber-500 bg-amber-500/10',
  emerald: 'text-emerald-500 bg-emerald-500/10',
  sky: 'text-sky-500 bg-sky-500/10',
  fuchsia: 'text-fuchsia-500 bg-fuchsia-500/10',
}
</script>

<template>
  <USlideover v-model:open="open" side="left" title="Outils">
    <template #body>
      <nav class="space-y-6">
        <div v-for="category in TOOL_CATEGORIES" :key="category.title">
          <div class="flex items-center gap-2 px-1 text-sm font-semibold text-(--ui-text-muted)">
            <span class="flex h-6 w-6 items-center justify-center rounded-md" :class="colorClasses[category.color]">
              <UIcon :name="category.icon" class="h-3.5 w-3.5" />
            </span>
            {{ category.title }}
          </div>
          <ul class="mt-2 space-y-0.5">
            <li v-for="tool in category.tools" :key="tool.title">
              <div
                v-if="tool.wip"
                class="flex w-full cursor-not-allowed items-center justify-between rounded-md px-3 py-2 text-sm text-(--ui-text-muted)/60"
              >
                <span>{{ tool.title }}</span>
                <UBadge color="neutral" variant="subtle" size="sm">WIP</UBadge>
              </div>
              <UButton
                v-else
                :to="tool.to!"
                variant="ghost"
                color="neutral"
                icon="i-lucide-arrow-right"
                trailing
                class="w-full justify-between"
              >
                {{ tool.title }}
              </UButton>
            </li>
          </ul>
        </div>
      </nav>
    </template>
  </USlideover>
</template>
