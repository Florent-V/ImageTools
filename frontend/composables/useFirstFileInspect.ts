// The inspect-and-map-error-to-French-message block was copy-pasted
// byte-for-byte across crop/watermark/rotate/workshop/pwa. Each page keeps
// its own "when do I call this" guard (they genuinely differ: some re-run on
// failure, some don't) — only the inspect call itself is shared.
import { ApiError, inspectImage, type InspectResponse } from '~/utils/api'

export function useFirstFileInspect() {
  const inspected = ref<InspectResponse>()
  const inspectError = ref<string>()

  async function inspectFirst(file: File) {
    inspectError.value = undefined
    try {
      inspected.value = await inspectImage(file)
    } catch (err) {
      inspectError.value = err instanceof ApiError ? err.message : "Impossible d'analyser cette image."
    }
  }

  return { inspected, inspectError, inspectFirst }
}
