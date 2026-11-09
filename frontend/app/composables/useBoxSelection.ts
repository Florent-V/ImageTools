// Shared drag/resize engine behind CropForm.vue and VideoCropForm.vue — same
// pointer-capture state machine, same ratio-locked math, previously
// duplicated ~200 lines between the two with no way to fix one without
// forgetting the other. Preset-picker UI stays in each component: the image
// side uses a hardcoded ratio menu, the video side a server-provided preset
// list — legitimately different data sources, not duplication.
import type { Ref } from 'vue'
import { relativePoint } from '~/utils/previewLayout'

export type HandleId = 'nw' | 'n' | 'ne' | 'e' | 'se' | 's' | 'sw' | 'w'

export const CROP_HANDLES: { id: HandleId, left: string, top: string, cursor: string }[] = [
  { id: 'nw', left: '0%', top: '0%', cursor: 'nwse-resize' },
  { id: 'n', left: '50%', top: '0%', cursor: 'ns-resize' },
  { id: 'ne', left: '100%', top: '0%', cursor: 'nesw-resize' },
  { id: 'e', left: '100%', top: '50%', cursor: 'ew-resize' },
  { id: 'se', left: '100%', top: '100%', cursor: 'nwse-resize' },
  { id: 's', left: '50%', top: '100%', cursor: 'ns-resize' },
  { id: 'sw', left: '0%', top: '100%', cursor: 'nesw-resize' },
  { id: 'w', left: '0%', top: '50%', cursor: 'ew-resize' }
]

export interface DisplayBox {
  left: number
  top: number
  width: number
  height: number
}

interface UseBoxSelectionOptions {
  previewWrap: Ref<HTMLElement | undefined>
  previewImg: Ref<HTMLImageElement | undefined>
  sourceWidth: () => number
  ratio: () => number | null
  onFreeform?: () => void
  onChange: (box: DisplayBox, scale: number) => void
}

export function useBoxSelection(opts: UseBoxSelectionOptions) {
  const selection = ref<DisplayBox | null>(null)

  // One of: creating a fresh box by dragging on the background, moving the
  // whole box, or resizing from a specific handle. Null when idle.
  type Interaction
    = | { kind: 'create', originX: number, originY: number }
      | { kind: 'move', grabX: number, grabY: number, start: DisplayBox }
      | { kind: 'resize', handle: HandleId, start: DisplayBox }
      | null
  const interaction = ref<Interaction>(null)

  function displayScale(): number {
    const width = opts.previewImg.value?.clientWidth ?? 0
    const source = opts.sourceWidth()
    if (!width || !source) return 1
    return source / width
  }

  function displayBounds(): { width: number, height: number } {
    return { width: opts.previewImg.value?.clientWidth ?? 0, height: opts.previewImg.value?.clientHeight ?? 0 }
  }

  function clampBox(box: DisplayBox): DisplayBox {
    const bounds = displayBounds()
    const width = Math.min(box.width, bounds.width)
    const height = Math.min(box.height, bounds.height)
    return {
      width,
      height,
      left: Math.min(Math.max(box.left, 0), bounds.width - width),
      top: Math.min(Math.max(box.top, 0), bounds.height - height)
    }
  }

  function applyBox(box: DisplayBox) {
    selection.value = box
  }

  function applyPreset(ratio: number | null) {
    const bounds = displayBounds()
    let width = bounds.width * 0.8
    let height = ratio ? width / ratio : bounds.height * 0.8
    if (height > bounds.height) {
      height = bounds.height * 0.8
      width = ratio ? height * ratio : width
    }
    const box: DisplayBox = { left: (bounds.width - width) / 2, top: (bounds.height - height) / 2, width, height }
    selection.value = box
    opts.onChange(box, displayScale())
  }

  function relativePosition(event: PointerEvent): { x: number, y: number } {
    return relativePoint(event, opts.previewWrap.value!)
  }

  function capture(event: PointerEvent) {
    ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  }

  function onBackgroundPointerDown(event: PointerEvent) {
    // Selection body/handles stop propagation before reaching here, so this
    // only fires for clicks on empty preview area -> start a fresh box.
    opts.onFreeform?.()
    const origin = relativePosition(event)
    interaction.value = { kind: 'create', originX: origin.x, originY: origin.y }
    selection.value = { left: origin.x, top: origin.y, width: 0, height: 0 }
    capture(event)
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
  }

  function startMove(event: PointerEvent) {
    if (!selection.value) return
    const pos = relativePosition(event)
    interaction.value = { kind: 'move', grabX: pos.x, grabY: pos.y, start: { ...selection.value } }
    capture(event)
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
  }

  function startResize(event: PointerEvent, handle: HandleId) {
    if (!selection.value) return
    interaction.value = { kind: 'resize', handle, start: { ...selection.value } }
    capture(event)
    window.addEventListener('pointermove', onPointerMove)
    window.addEventListener('pointerup', onPointerUp)
  }

  function onPointerMove(event: PointerEvent) {
    const current = interaction.value
    if (!current || !opts.previewWrap.value) return
    const pos = relativePosition(event)
    const bounds = displayBounds()

    if (current.kind === 'create') {
      let width = Math.abs(pos.x - current.originX)
      let height = Math.abs(pos.y - current.originY)
      const ratio = opts.ratio()

      if (!ratio) {
        const left = Math.min(current.originX, pos.x)
        const top = Math.min(current.originY, pos.y)
        selection.value = clampBox({ left, top, width, height })
        return
      }

      // Ratio-locked: derive left/top from the anchor + clamped dimensions
      // directly (not via clampBox, which would clamp width/height
      // independently and break the locked ratio) so the box shrinks to fit
      // near an edge instead of overshooting it or losing its aspect ratio.
      const growingRight = pos.x >= current.originX
      const growingDown = pos.y >= current.originY
      const maxWidthAllowed = Math.max(0, growingRight ? bounds.width - current.originX : current.originX)
      const maxHeightAllowed = Math.max(0, growingDown ? bounds.height - current.originY : current.originY)

      let largerDim = Math.max(width, height)
      if (ratio >= 1) {
        largerDim = Math.min(largerDim, maxWidthAllowed, maxHeightAllowed * ratio)
        width = largerDim
        height = largerDim / ratio
      } else {
        largerDim = Math.min(largerDim, maxHeightAllowed, maxWidthAllowed / ratio)
        height = largerDim
        width = largerDim * ratio
      }

      const left = growingRight ? current.originX : current.originX - width
      const top = growingDown ? current.originY : current.originY - height
      selection.value = { left, top, width, height }
      return
    }

    if (current.kind === 'move') {
      const dx = pos.x - current.grabX
      const dy = pos.y - current.grabY
      const width = current.start.width
      const height = current.start.height
      selection.value = {
        left: Math.min(Math.max(current.start.left + dx, 0), bounds.width - width),
        top: Math.min(Math.max(current.start.top + dy, 0), bounds.height - height),
        width,
        height
      }
      return
    }

    // resize: keep the edge/corner opposite the dragged handle fixed.
    const { handle, start } = current
    const right = start.left + start.width
    const bottom = start.top + start.height
    let left = start.left
    let top = start.top
    let width = start.width
    let height = start.height

    const clampedX = Math.min(Math.max(pos.x, 0), bounds.width)
    const clampedY = Math.min(Math.max(pos.y, 0), bounds.height)

    if (handle.includes('w')) {
      left = Math.min(clampedX, right - 1)
      width = right - left
    } else if (handle.includes('e')) {
      width = Math.max(clampedX - left, 1)
    }
    if (handle.includes('n')) {
      top = Math.min(clampedY, bottom - 1)
      height = bottom - top
    } else if (handle.includes('s')) {
      height = Math.max(clampedY - top, 1)
    }

    const ratio = opts.ratio()
    if (ratio) {
      if (handle === 'n' || handle === 's') {
        // vertical-only handle: derive width from height, keep box centered on its horizontal midpoint
        const midX = start.left + start.width / 2
        width = height * ratio
        left = midX - width / 2
      } else if (handle === 'e' || handle === 'w') {
        const midY = start.top + start.height / 2
        height = width / ratio
        top = midY - height / 2
      } else {
        // corner handle: derive height from width, keep the opposite corner fixed
        height = width / ratio
        if (handle.includes('n')) top = bottom - height
      }
    }

    selection.value = clampBox({ left, top, width, height })
  }

  function onPointerUp() {
    const current = interaction.value
    interaction.value = null
    window.removeEventListener('pointermove', onPointerMove)
    window.removeEventListener('pointerup', onPointerUp)
    if (!current || !selection.value) return
    if (current.kind === 'create' && (selection.value.width <= 4 || selection.value.height <= 4)) {
      selection.value = null
      return
    }
    opts.onChange(selection.value, displayScale())
  }

  return {
    selection,
    handles: CROP_HANDLES,
    displayScale,
    applyBox,
    applyPreset,
    onBackgroundPointerDown,
    startMove,
    startResize
  }
}
