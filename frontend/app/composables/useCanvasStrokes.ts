import type { Ref } from 'vue'
import { usePointerDrag } from '~/composables/usePointerDrag'
import { relativePoint } from '~/utils/previewLayout'

export interface Stroke {
  color: string
  widthScale: number // stroke width as a fraction of image width
  points: { x: number, y: number }[]
}

export function paintStroke(ctx: CanvasRenderingContext2D, stroke: Stroke, width: number, height: number) {
  if (stroke.points.length < 2) return
  ctx.strokeStyle = stroke.color
  ctx.lineWidth = Math.max(1, stroke.widthScale * width)
  ctx.lineCap = 'round'
  ctx.lineJoin = 'round'
  ctx.beginPath()
  const [start, ...rest] = stroke.points
  if (!start) return
  ctx.moveTo(start.x * width, start.y * height)
  for (const point of rest) ctx.lineTo(point.x * width, point.y * height)
  ctx.stroke()
}

export function useCanvasStrokes(previewWrap: Ref<HTMLElement | undefined>, canvas: Ref<HTMLCanvasElement | undefined>) {
  const strokes = ref<Stroke[]>([])
  const liveStroke = ref<Stroke | null>(null)

  function redraw() {
    const el = canvas.value
    if (!el) return
    const ctx = el.getContext('2d')
    if (!ctx) return
    ctx.clearRect(0, 0, el.width, el.height)
    for (const stroke of strokes.value) paintStroke(ctx, stroke, el.width, el.height)
    if (liveStroke.value) paintStroke(ctx, liveStroke.value, el.width, el.height)
  }

  const drag = usePointerDrag(
    (event) => {
      if (!liveStroke.value || !previewWrap.value) return
      liveStroke.value.points.push(relativePoint(event, previewWrap.value, true))
      redraw()
    },
    () => {
      if (liveStroke.value && liveStroke.value.points.length > 1) strokes.value.push(liveStroke.value)
      liveStroke.value = null
      redraw()
    }
  )

  function start(event: PointerEvent, color: string, widthScale: number) {
    if (!previewWrap.value) return
    liveStroke.value = { color, widthScale, points: [relativePoint(event, previewWrap.value, true)] }
    drag.start(event)
  }

  function undo() {
    strokes.value.pop()
    redraw()
  }

  return { strokes, start, undo, redraw }
}
