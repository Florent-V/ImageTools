// Every per-tool page (compress/resize/crop/watermark/rotate/convert/workshop)
// opened with the identical `useAsyncData('formats', ...) + useProcessor()`
// pair and wrapped every run in an identical running-flag try/finally. One
// composable now owns both.
import { fetchFormats, type ProcessRequest } from '~/utils/api'
import { useProcessor, type QueueItem } from '~/composables/useProcessor'

export async function useToolPage() {
  const { data: formats } = await useAsyncData('formats', fetchFormats, { server: false })
  const { queue, enqueue, process, clear, results, errors, progress } = useProcessor()
  const running = ref(false)

  async function run(request: ProcessRequest | ((item: QueueItem) => ProcessRequest), watermarkFile?: File) {
    running.value = true
    try {
      await process(request, watermarkFile)
    } finally {
      running.value = false
    }
  }

  return { formats, queue, enqueue, run, running, clear, results, errors, progress }
}
