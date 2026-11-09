<template>
  <div
    v-if="items.length"
    class="flex flex-col gap-3"
  >
    <UButton
      v-if="doneItems.length >= 2"
      icon="i-lucide-archive"
      color="neutral"
      variant="subtle"
      class="self-start"
      @click="downloadZip"
    >
      Télécharger tout (.zip)
    </UButton>

    <ul class="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6">
      <li
        v-for="entry in itemsView"
        :key="entry.item.id"
        class="flex flex-col gap-1.5 rounded-lg border border-(--ui-border) p-2"
      >
        <div class="relative aspect-square w-full overflow-hidden rounded-md bg-(--ui-bg-elevated)">
          <img
            v-if="entry.item.previewUrl"
            :src="entry.item.previewUrl"
            class="h-full w-full object-cover"
            alt=""
          >
          <div
            v-else
            class="flex h-full w-full items-center justify-center"
          >
            <UIcon
              name="i-lucide-image"
              class="h-6 w-6 text-(--ui-text-muted)"
            />
          </div>
          <UBadge
            :color="statusColor(entry.item.status)"
            variant="solid"
            size="sm"
            class="absolute right-1 top-1"
          >
            {{ statusLabel(entry.item.status) }}
          </UBadge>
        </div>
        <div class="flex min-w-0 flex-col gap-1">
          <span
            class="truncate text-sm font-medium"
            :title="entry.item.file.name"
          >{{ entry.item.file.name }}</span>
          <div
            v-if="entry.original"
            class="flex flex-wrap items-center justify-center gap-1"
          >
            <UBadge
              color="neutral"
              variant="subtle"
              size="sm"
            >
              {{ entry.original }}
            </UBadge>
            <template v-if="entry.target">
              <UIcon
                name="i-lucide-arrow-right"
                class="h-3 w-3 shrink-0 text-(--ui-text-muted)"
              />
              <UBadge
                color="primary"
                variant="subtle"
                size="sm"
              >
                {{ entry.target }}
              </UBadge>
            </template>
          </div>
          <span class="truncate text-xs text-(--ui-text-muted)">{{ formatSize(entry.item.file.size) }}</span>
          <span
            v-if="entry.item.status === 'error'"
            class="truncate text-xs text-(--ui-error)"
            :title="entry.item.errorMessage"
          >
            {{ entry.item.errorMessage }}
          </span>
          <template v-if="entry.item.status === 'done' && entry.item.result">
            <span class="truncate text-xs text-emerald-500">
              {{ formatSize(entry.item.result.outputSize) }} ({{ gainPercent(entry.item.result) }}%)
            </span>
            <UButton
              :href="objectUrl(entry.item)"
              :download="downloadName(entry.item)"
              icon="i-lucide-download"
              color="primary"
              variant="soft"
              size="xs"
              block
            >
              Télécharger
            </UButton>
          </template>
        </div>
      </li>
    </ul>
  </div>
</template>

<script setup lang="ts">
import { zip, type Zippable } from 'fflate'
import type { QueueItem, QueueItemStatus } from '~/composables/useProcessor'
import type { ResizeOp } from '~/utils/api'
import { computeResizeTarget } from '~/utils/resizePreview'

const props = defineProps<{ items: QueueItem[], resizeOp?: ResizeOp }>()

const LABELS: Record<QueueItemStatus, string> = {
  queued: 'en attente',
  processing: 'en cours',
  done: 'terminé',
  error: 'erreur'
}

const COLORS: Record<QueueItemStatus, 'neutral' | 'warning' | 'success' | 'error'> = {
  queued: 'neutral',
  processing: 'warning',
  done: 'success',
  error: 'error'
}

const doneItems = computed(() => props.items.filter(item => item.status === 'done'))

const urlCache = new Map<string, string>()

// Items disappear from the prop when the queue is cleared or replaced, not
// just when this component unmounts — revoke whatever's no longer referenced.
watch(
  () => props.items,
  (current) => {
    const liveIds = new Set(current.map(item => item.id))
    for (const [id, url] of urlCache) {
      if (!liveIds.has(id)) {
        URL.revokeObjectURL(url)
        urlCache.delete(id)
      }
    }
  }
)

onBeforeUnmount(() => {
  urlCache.forEach(url => URL.revokeObjectURL(url))
})

function statusLabel(status: QueueItemStatus): string {
  return LABELS[status]
}

function statusColor(status: QueueItemStatus) {
  return COLORS[status]
}

interface QueueItemView {
  item: QueueItem
  original: string | null
  target: string | null
}

const itemsView = computed<QueueItemView[]>(() =>
  props.items.map((item) => {
    if (!item.originalWidth || !item.originalHeight) return { item, original: null, target: null }
    const original = `${item.originalWidth}×${item.originalHeight}`

    if (item.status === 'done' && item.result) {
      return { item, original, target: `${item.result.outputWidth}×${item.result.outputHeight}` }
    }
    if (props.resizeOp) {
      const target = computeResizeTarget({ width: item.originalWidth, height: item.originalHeight }, props.resizeOp)
      if (target && (target.width !== item.originalWidth || target.height !== item.originalHeight)) {
        return { item, original, target: `${target.width}×${target.height}` }
      }
    }
    return { item, original, target: null }
  })
)

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`
  return `${(bytes / 1024).toFixed(1)} Ko`
}

function objectUrl(item: QueueItem): string {
  const cached = urlCache.get(item.id)
  if (cached) return cached
  const url = URL.createObjectURL(item.result!.blob)
  urlCache.set(item.id, url)
  return url
}

function baseName(fileName: string): string {
  const dot = fileName.lastIndexOf('.')
  return dot === -1 ? fileName : fileName.slice(0, dot)
}

function downloadName(item: QueueItem): string {
  return `${baseName(item.file.name)}.${item.result!.extension}`
}

function gainPercent(result: NonNullable<QueueItem['result']>): string {
  if (result.inputSize === 0) return '0'
  const gain = ((result.inputSize - result.outputSize) / result.inputSize) * 100
  return gain.toFixed(0)
}

async function downloadZip() {
  const entries: Zippable = {}
  for (const item of doneItems.value) {
    const buffer = new Uint8Array(await item.result!.blob.arrayBuffer())
    entries[downloadName(item)] = buffer
  }
  zip(entries, (err, data) => {
    if (err) return
    const blob = new Blob([data], { type: 'application/zip' })
    const url = URL.createObjectURL(blob)
    const anchor = document.createElement('a')
    anchor.href = url
    anchor.download = 'images.zip'
    anchor.click()
    URL.revokeObjectURL(url)
  })
}
</script>
