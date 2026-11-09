import type { Ref } from 'vue'
import { usePointerDrag } from '~/composables/usePointerDrag'
import { relativePoint } from '~/utils/previewLayout'

export interface TextBlock {
  id: string
  text: string
  x: number // fraction of image width, anchor is the block's own center
  y: number // fraction of image height
  font: string
  scale: number // font size as a fraction of image width
  color: string
  rotation: number // degrees
}

export function useTextBlocks(previewWrap: Ref<HTMLElement | undefined>) {
  const blocks = ref<TextBlock[]>([])
  const selectedId = ref<string | null>(null)
  const editingId = ref<string | null>(null)

  const selected = computed(() => blocks.value.find(b => b.id === selectedId.value) ?? null)

  function place(pos: { x: number, y: number }) {
    const block: TextBlock = { id: crypto.randomUUID(), text: 'Texte', x: pos.x, y: pos.y, font: 'Arial', scale: 0.06, color: '#ffffff', rotation: 0 }
    blocks.value.push(block)
    selectedId.value = block.id
    return block
  }

  // Cascades each new block a bit further from center so it doesn't land
  // exactly on top of the previous one when added from the button.
  function add() {
    const offset = (blocks.value.length % 6) * 0.05
    place({ x: 0.5 + offset, y: 0.4 + offset })
  }

  function remove(id: string) {
    blocks.value = blocks.value.filter(b => b.id !== id)
    if (selectedId.value === id) selectedId.value = null
  }

  function startEditing(block: TextBlock, event: MouseEvent) {
    selectedId.value = block.id
    editingId.value = block.id
    nextTick(() => {
      const el = event.currentTarget as HTMLElement
      el.focus()
      const range = document.createRange()
      range.selectNodeContents(el)
      const sel = window.getSelection()
      sel?.removeAllRanges()
      sel?.addRange(range)
    })
  }

  function stopEditing(block: TextBlock, event: FocusEvent) {
    if (editingId.value !== block.id) return
    block.text = (event.target as HTMLElement).textContent?.trim() || 'Texte'
    editingId.value = null
  }

  let moveStart: { x: number, y: number, blockX: number, blockY: number, block: TextBlock } | null = null
  const moveDrag = usePointerDrag(
    (event) => {
      if (!moveStart || !previewWrap.value) return
      const pos = relativePoint(event, previewWrap.value, true)
      moveStart.block.x = Math.min(1, Math.max(0, moveStart.blockX + (pos.x - moveStart.x)))
      moveStart.block.y = Math.min(1, Math.max(0, moveStart.blockY + (pos.y - moveStart.y)))
    },
    () => {
      moveStart = null
    }
  )

  function startMove(event: PointerEvent, block: TextBlock) {
    if (editingId.value === block.id || !previewWrap.value) return
    selectedId.value = block.id
    const pos = relativePoint(event, previewWrap.value, true)
    moveStart = { x: pos.x, y: pos.y, blockX: block.x, blockY: block.y, block }
    moveDrag.start(event)
  }

  let rotatingBlock: TextBlock | null = null
  const rotateDrag = usePointerDrag(
    (event) => {
      if (!rotatingBlock || !previewWrap.value) return
      const rect = previewWrap.value.getBoundingClientRect()
      const centerX = rect.left + rotatingBlock.x * rect.width
      const centerY = rect.top + rotatingBlock.y * rect.height
      const angle = Math.atan2(event.clientX - centerX, -(event.clientY - centerY)) * (180 / Math.PI)
      rotatingBlock.rotation = Math.round(angle)
    },
    () => {
      rotatingBlock = null
    }
  )

  function startRotate(event: PointerEvent, block: TextBlock) {
    rotatingBlock = block
    rotateDrag.start(event)
  }

  return { blocks, selectedId, editingId, selected, add, remove, startEditing, stopEditing, startMove, startRotate }
}
