import { processImage, ApiError, type ProcessRequest, type ProcessResult } from '~/utils/api'

export type QueueItemStatus = 'queued' | 'processing' | 'done' | 'error'

export interface QueueItem {
  id: string
  file: File
  status: QueueItemStatus
  previewUrl?: string
  originalWidth?: number
  originalHeight?: number
  result?: ProcessResult
  errorMessage?: string
}

const CONCURRENCY = 3

export function useProcessor() {
  const queue = ref<QueueItem[]>([])
  const progress = ref(0)

  async function enqueue(files: File[]) {
    for (const file of files) {
      queue.value.push({ id: crypto.randomUUID(), file, status: 'queued' })
      // Re-read through queue.value so every mutation below goes through Vue's
      // reactive proxy — mutating the plain object pushed above directly would
      // bypass it, and writes after the `await` (dimensions resolve later than
      // the first render) would silently never trigger a re-render.
      const item = queue.value[queue.value.length - 1]!
      // <img> decodes a broader set of formats than createImageBitmap in some
      // browsers, so the preview must not depend on the bitmap decode succeeding.
      item.previewUrl = URL.createObjectURL(file)
      try {
        const bitmap = await createImageBitmap(file)
        item.originalWidth = bitmap.width
        item.originalHeight = bitmap.height
        bitmap.close()
      } catch {
        // Dimensions unavailable client-side (e.g. TIFF in some browsers) — the
        // server is still the source of truth and will validate on process/inspect.
      }
    }
  }

  async function runOne(
    item: QueueItem,
    buildRequest: (item: QueueItem) => ProcessRequest,
    watermarkFile?: File,
  ) {
    item.status = 'processing'
    try {
      item.result = await processImage(item.file, buildRequest(item), watermarkFile)
      // Swap the thumbnail to the processed output so the queue vignette
      // reflects the transform (crop/rotate/etc.) before the user downloads.
      const nextPreviewUrl = URL.createObjectURL(item.result.blob)
      if (item.previewUrl) URL.revokeObjectURL(item.previewUrl)
      item.previewUrl = nextPreviewUrl
      item.status = 'done'
    } catch (err) {
      item.status = 'error'
      item.errorMessage = err instanceof ApiError ? err.message : 'Unexpected error'
    } finally {
      progress.value += 1
    }
  }

  async function process(
    request: ProcessRequest | ((item: QueueItem) => ProcessRequest),
    watermarkFile?: File,
  ) {
    const buildRequest = typeof request === 'function' ? request : () => request
    const pending = queue.value.filter((item) => item.status === 'queued' || item.status === 'error')
    progress.value = 0
    let cursor = 0
    async function worker() {
      while (cursor < pending.length) {
        const item = pending[cursor]!
        cursor += 1
        await runOne(item, buildRequest, watermarkFile)
      }
    }
    const workerCount = Math.min(CONCURRENCY, pending.length)
    await Promise.all(Array.from({ length: workerCount }, worker))
  }

  function clear() {
    queue.value = []
    progress.value = 0
  }

  const results = computed(() => queue.value.filter((item) => item.status === 'done'))
  const errors = computed(() => queue.value.filter((item) => item.status === 'error'))

  return { queue, progress, enqueue, process, clear, results, errors }
}
