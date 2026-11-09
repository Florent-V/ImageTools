// Shared sizing for every image-preview canvas (crop, watermark, video crop).
// One relative cap so the preview never dwarfs the page on a wide monitor,
// while still scaling down to fit on narrow screens.
export const PREVIEW_WRAP_CLASS = 'relative block w-full max-w-3xl mx-auto select-none touch-none'
export const PREVIEW_IMG_CLASS = 'block w-full rounded-md'

// A pointer event's position relative to an element's box — px by default,
// or normalized to [0,1] of the element's size when normalize is true.
// Previously reimplemented per-component under three different names.
export function relativePoint(event: PointerEvent, el: HTMLElement, normalize = false): { x: number, y: number } {
  const rect = el.getBoundingClientRect()
  const x = event.clientX - rect.left
  const y = event.clientY - rect.top
  if (!normalize) return { x, y }
  return { x: Math.min(1, Math.max(0, x / rect.width)), y: Math.min(1, Math.max(0, y / rect.height)) }
}
