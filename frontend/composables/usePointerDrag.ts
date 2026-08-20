// The grab → window-listener-pair → capture → cleanup shape was reimplemented
// independently in CropForm/VideoCropForm (now inside useBoxSelection),
// WatermarkForm, and GeneratorForm (block move + rotate). One helper, callers
// supply their own move/end logic since what each one computes differs.
export function usePointerDrag(onMove: (event: PointerEvent) => void, onEnd?: (event: PointerEvent) => void) {
  function handleUp(event: PointerEvent) {
    window.removeEventListener('pointermove', onMove)
    window.removeEventListener('pointerup', handleUp)
    onEnd?.(event)
  }

  function start(event: PointerEvent) {
    ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
    window.addEventListener('pointermove', onMove)
    window.addEventListener('pointerup', handleUp)
  }

  return { start }
}
