<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">Générateur</h3>
    </template>

    <div class="flex flex-col gap-4">
      <div class="flex gap-2">
        <UButton size="sm" :color="mode === 'text' ? 'primary' : 'neutral'" :variant="mode === 'text' ? 'solid' : 'outline'" icon="i-lucide-type" @click="mode = 'text'">
          Texte
        </UButton>
        <UButton size="sm" :color="mode === 'draw' ? 'primary' : 'neutral'" :variant="mode === 'draw' ? 'solid' : 'outline'" icon="i-lucide-pencil" @click="mode = 'draw'">
          Dessin
        </UButton>
      </div>

      <div
        ref="previewWrap"
        :class="[PREVIEW_WRAP_CLASS, mode === 'draw' ? 'cursor-crosshair' : 'cursor-default']"
        @pointerdown="onWrapPointerDown"
      >
        <img :src="previewSrc" ref="previewImg" :class="PREVIEW_IMG_CLASS" draggable="false" @load="onImageLoad" />
        <canvas ref="drawCanvas" class="absolute inset-0 h-full w-full" :class="mode === 'draw' ? '' : 'pointer-events-none'" />
        <div
          v-for="block in textBlocks"
          :key="block.id"
          class="absolute rounded-sm px-1 select-none"
          :class="[
            block.id === selectedId ? 'outline-dashed outline-2 outline-(--ui-primary)' : '',
            editingId === block.id ? 'cursor-text' : 'cursor-move',
          ]"
          :style="textBlockStyle(block)"
          :contenteditable="editingId === block.id"
          @pointerdown.stop="startMoveBlock($event, block)"
          @dblclick.stop="startEditing(block, $event)"
          @blur="stopEditing(block, $event)"
          @keydown.enter.prevent="($event.target as HTMLElement).blur()"
        >
          {{ block.text || 'Texte' }}
          <div
            v-if="block.id === selectedId && editingId !== block.id"
            class="absolute top-0 left-1/2 h-5 w-5 -translate-x-1/2 -translate-y-8 cursor-grab rounded-full border-2 border-(--ui-primary) bg-(--ui-bg) active:cursor-grabbing"
            @pointerdown.stop="startRotateBlock($event, block)"
          />
        </div>
      </div>

      <div v-if="mode === 'text'" class="flex flex-col gap-2">
        <div class="flex flex-wrap items-center gap-4">
          <UButton size="sm" icon="i-lucide-plus" @click="addBlock">Ajouter un texte</UButton>
          <template v-if="selectedBlock">
            <USelect v-model="selectedBlock.font" :items="FONTS" class="max-w-40" />
            <ColorPicker v-model="selectedBlock.color" label="Couleur" />
            <SizeStepper v-model="selectedBlock.scale" :step="0.01" :min="0.02" :max="0.5" label="Taille" />
            <UButton size="sm" color="error" variant="outline" icon="i-lucide-trash-2" @click="deleteBlock(selectedBlock.id)" />
          </template>
        </div>
        <p v-if="textBlocks.length" class="text-sm text-(--ui-text-muted)">
          Glissez un bloc pour le déplacer, double-cliquez dessus pour modifier son texte.
        </p>
      </div>

      <div v-else class="flex flex-wrap items-center gap-4">
        <ColorPicker v-model="drawColor" label="Couleur" />
        <SizeStepper v-model="drawWidthScale" :step="0.005" :min="0.002" :max="0.08" label="Épaisseur" />
        <UButton size="sm" variant="outline" icon="i-lucide-undo-2" :disabled="!strokes.length" @click="undoStroke">
          Effacer le dernier trait
        </UButton>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import { PREVIEW_IMG_CLASS, PREVIEW_WRAP_CLASS } from '~/utils/previewLayout'
import ColorPicker from '~/components/shared/ColorPicker.vue'
import SizeStepper from '~/components/shared/SizeStepper.vue'

const FONTS = ['Arial', 'Georgia', 'Times New Roman', 'Courier New', 'Trebuchet MS', 'Comic Sans MS', 'Impact', 'Verdana']

interface TextBlock {
  id: string
  text: string
  x: number // fraction of image width, anchor is the block's own center
  y: number // fraction of image height
  font: string
  scale: number // font size as a fraction of image width
  color: string
  rotation: number // degrees
}

interface Stroke {
  color: string
  widthScale: number // stroke width as a fraction of image width
  points: { x: number; y: number }[]
}

const props = defineProps<{
  previewSrc: string
  fileName: string
  mimeType: string
}>()

const mode = ref<'text' | 'draw'>('text')
const textBlocks = ref<TextBlock[]>([])
const strokes = ref<Stroke[]>([])
const liveStroke = ref<Stroke | null>(null)
const selectedId = ref<string | null>(null)
const editingId = ref<string | null>(null)
const drawColor = ref('#ff3b30')
const drawWidthScale = ref(0.01)

const previewWrap = ref<HTMLElement>()
const previewImg = ref<HTMLImageElement>()
const drawCanvas = ref<HTMLCanvasElement>()
const naturalWidth = ref(0)
const naturalHeight = ref(0)

const selectedBlock = computed(() => textBlocks.value.find((b) => b.id === selectedId.value) ?? null)

function textBlockStyle(block: TextBlock) {
  return {
    left: `${block.x * 100}%`,
    top: `${block.y * 100}%`,
    transform: `translate(-50%, -50%) rotate(${block.rotation}deg)`,
    fontFamily: block.font,
    color: block.color,
    fontSize: `${(previewImg.value?.clientWidth ?? 0) * block.scale}px`,
    whiteSpace: 'nowrap' as const,
  }
}

function onImageLoad() {
  naturalWidth.value = previewImg.value!.naturalWidth
  naturalHeight.value = previewImg.value!.naturalHeight
  syncCanvasSize()
}

function syncCanvasSize() {
  const canvas = drawCanvas.value
  const img = previewImg.value
  if (!canvas || !img || !img.clientWidth) return
  canvas.width = img.clientWidth
  canvas.height = img.clientHeight
  redrawOverlay()
}

let resizeObserver: ResizeObserver | undefined
onMounted(() => {
  resizeObserver = new ResizeObserver(() => syncCanvasSize())
  if (previewWrap.value) resizeObserver.observe(previewWrap.value)
})
onBeforeUnmount(() => resizeObserver?.disconnect())

function paintStroke(ctx: CanvasRenderingContext2D, stroke: Stroke, width: number, height: number) {
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

function redrawOverlay() {
  const canvas = drawCanvas.value
  if (!canvas) return
  const ctx = canvas.getContext('2d')
  if (!ctx) return
  ctx.clearRect(0, 0, canvas.width, canvas.height)
  for (const stroke of strokes.value) paintStroke(ctx, stroke, canvas.width, canvas.height)
  if (liveStroke.value) paintStroke(ctx, liveStroke.value, canvas.width, canvas.height)
}

function relativePoint(event: PointerEvent): { x: number; y: number } {
  const rect = previewWrap.value!.getBoundingClientRect()
  return {
    x: Math.min(1, Math.max(0, (event.clientX - rect.left) / rect.width)),
    y: Math.min(1, Math.max(0, (event.clientY - rect.top) / rect.height)),
  }
}

function onWrapPointerDown(event: PointerEvent) {
  if (mode.value === 'draw') {
    startStroke(event)
    return
  }
  // Text blocks call .stop on their own pointerdown, so this only fires for
  // clicks on empty image area -> deselect (blocks are only created via the
  // "Ajouter un texte" button, not by clicking the image).
  selectedId.value = null
}

function placeBlock(pos: { x: number; y: number }) {
  const block: TextBlock = { id: crypto.randomUUID(), text: 'Texte', x: pos.x, y: pos.y, font: 'Arial', scale: 0.06, color: '#ffffff', rotation: 0 }
  textBlocks.value.push(block)
  selectedId.value = block.id
  return block
}

// Cascades each new block a bit further from center so it doesn't land
// exactly on top of the previous one when added from the button.
function addBlock() {
  const offset = (textBlocks.value.length % 6) * 0.05
  placeBlock({ x: 0.5 + offset, y: 0.4 + offset })
}

function startEditing(block: TextBlock, event: MouseEvent) {
  selectedId.value = block.id
  editingId.value = block.id
  nextTick(() => {
    const el = event.currentTarget as HTMLElement
    el.focus()
    const range = document.createRange()
    range.selectNodeContents(el)
    const selection = window.getSelection()
    selection?.removeAllRanges()
    selection?.addRange(range)
  })
}

function stopEditing(block: TextBlock, event: FocusEvent) {
  if (editingId.value !== block.id) return
  block.text = (event.target as HTMLElement).textContent?.trim() || 'Texte'
  editingId.value = null
}

function startStroke(event: PointerEvent) {
  liveStroke.value = { color: drawColor.value, widthScale: drawWidthScale.value, points: [relativePoint(event)] }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  window.addEventListener('pointermove', onStrokeMove)
  window.addEventListener('pointerup', onStrokeEnd)
}

function onStrokeMove(event: PointerEvent) {
  if (!liveStroke.value) return
  liveStroke.value.points.push(relativePoint(event))
  redrawOverlay()
}

function onStrokeEnd() {
  window.removeEventListener('pointermove', onStrokeMove)
  window.removeEventListener('pointerup', onStrokeEnd)
  if (liveStroke.value && liveStroke.value.points.length > 1) strokes.value.push(liveStroke.value)
  liveStroke.value = null
  redrawOverlay()
}

function undoStroke() {
  strokes.value.pop()
  redrawOverlay()
}

function deleteBlock(id: string) {
  textBlocks.value = textBlocks.value.filter((b) => b.id !== id)
  if (selectedId.value === id) selectedId.value = null
}

let moveStart: { x: number; y: number; blockX: number; blockY: number; block: TextBlock } | null = null

function startMoveBlock(event: PointerEvent, block: TextBlock) {
  if (editingId.value === block.id) return
  selectedId.value = block.id
  const pos = relativePoint(event)
  moveStart = { x: pos.x, y: pos.y, blockX: block.x, blockY: block.y, block }
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  window.addEventListener('pointermove', onMoveBlock)
  window.addEventListener('pointerup', onMoveBlockEnd)
}

function onMoveBlock(event: PointerEvent) {
  if (!moveStart) return
  const pos = relativePoint(event)
  moveStart.block.x = Math.min(1, Math.max(0, moveStart.blockX + (pos.x - moveStart.x)))
  moveStart.block.y = Math.min(1, Math.max(0, moveStart.blockY + (pos.y - moveStart.y)))
}

function onMoveBlockEnd() {
  moveStart = null
  window.removeEventListener('pointermove', onMoveBlock)
  window.removeEventListener('pointerup', onMoveBlockEnd)
}

let rotatingBlock: TextBlock | null = null

function startRotateBlock(event: PointerEvent, block: TextBlock) {
  rotatingBlock = block
  ;(event.currentTarget as HTMLElement).setPointerCapture(event.pointerId)
  window.addEventListener('pointermove', onRotateBlock)
  window.addEventListener('pointerup', onRotateBlockEnd)
}

function onRotateBlock(event: PointerEvent) {
  if (!rotatingBlock || !previewWrap.value) return
  const rect = previewWrap.value.getBoundingClientRect()
  const centerX = rect.left + rotatingBlock.x * rect.width
  const centerY = rect.top + rotatingBlock.y * rect.height
  const angle = Math.atan2(event.clientX - centerX, -(event.clientY - centerY)) * (180 / Math.PI)
  rotatingBlock.rotation = Math.round(angle)
}

function onRotateBlockEnd() {
  rotatingBlock = null
  window.removeEventListener('pointermove', onRotateBlock)
  window.removeEventListener('pointerup', onRotateBlockEnd)
}

const EXPORTABLE_MIMES = ['image/png', 'image/jpeg', 'image/webp']

async function exportImage(): Promise<{ blob: Blob; fileName: string }> {
  const img = previewImg.value
  if (!img || !naturalWidth.value || !naturalHeight.value) throw new Error('Image not ready')

  const canvas = document.createElement('canvas')
  canvas.width = naturalWidth.value
  canvas.height = naturalHeight.value
  const ctx = canvas.getContext('2d')!
  ctx.drawImage(img, 0, 0, canvas.width, canvas.height)

  for (const stroke of strokes.value) paintStroke(ctx, stroke, canvas.width, canvas.height)

  for (const block of textBlocks.value) {
    const fontSize = block.scale * canvas.width
    ctx.save()
    ctx.translate(block.x * canvas.width, block.y * canvas.height)
    ctx.rotate((block.rotation * Math.PI) / 180)
    ctx.font = `${fontSize}px ${block.font}`
    ctx.fillStyle = block.color
    ctx.textAlign = 'center'
    ctx.textBaseline = 'middle'
    ctx.fillText(block.text || 'Texte', 0, 0)
    ctx.restore()
  }

  const mime = EXPORTABLE_MIMES.includes(props.mimeType) ? props.mimeType : 'image/png'
  const blob = await new Promise<Blob>((resolve, reject) => {
    canvas.toBlob((result) => (result ? resolve(result) : reject(new Error('Export failed'))), mime, 0.92)
  })
  return { blob, fileName: `edit-${props.fileName}` }
}

defineExpose({ exportImage })
</script>
