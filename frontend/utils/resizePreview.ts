import type { ResizeOp } from '~/utils/api'

// Mirrors backend/app/engine/operations/resize.py's _target_size + no_upscale
// check, so the queue vignette can predict the exact output resolution
// before the request is sent.
export function computeResizeTarget(
  current: { width: number; height: number },
  op: ResizeOp,
): { width: number; height: number } | null {
  const { width, height } = current
  let factor: number

  if (op.percent) {
    factor = op.percent / 100
  } else if (!op.keep_ratio && op.width && op.height) {
    const target = { width: op.width, height: op.height }
    if (op.no_upscale && (target.width > width || target.height > height)) return null
    return target
  } else if (op.width && op.height) {
    factor = Math.min(op.width / width, op.height / height)
  } else if (op.width) {
    factor = op.width / width
  } else if (op.height) {
    factor = op.height / height
  } else {
    return null
  }

  const target = { width: Math.max(1, Math.round(width * factor)), height: Math.max(1, Math.round(height * factor)) }
  if (op.no_upscale && (target.width > width || target.height > height)) return null
  return target
}
