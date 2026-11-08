<template>
  <div>
    <div
      class="flex flex-col items-center justify-center gap-3 rounded-xl border-2 border-dashed p-10 text-center transition-colors cursor-pointer"
      :class="isOver ? 'border-(--ui-primary) bg-(--ui-primary)/5' : 'border-(--ui-border) hover:border-(--ui-primary)/50'"
      @dragover.prevent="isOver = true"
      @dragleave.prevent="isOver = false"
      @drop.prevent="onDrop"
      @click="fileInput?.click()"
    >
      <UIcon :name="icon" class="h-8 w-8 text-(--ui-text-muted)" />
      <p class="text-sm text-(--ui-text-muted)">
        Glissez-déposez {{ label }} ici, ou
        <span class="font-medium text-(--ui-primary)">cliquez pour choisir un fichier</span>.
      </p>
      <slot name="hint" />
      <input
        ref="fileInput"
        type="file"
        :accept="accept"
        :multiple="multiple"
        class="sr-only"
        @change="onPick"
      >
    </div>
    <p v-if="rejected.length" class="mt-2 text-sm text-(--ui-error)">
      Rejeté : {{ rejected.join(', ') }}
    </p>
  </div>
</template>

<script setup lang="ts">
import { normalizedExtension } from '~/utils/fileFormat'

const props = withDefaults(
  defineProps<{
    readFormats?: string[]
    maxFileSizeMb?: number
    multiple?: boolean
    accept?: string
    icon?: string
    label?: string
  }>(),
  {
    readFormats: undefined,
    maxFileSizeMb: undefined,
    multiple: true,
    accept: 'image/*',
    icon: 'i-lucide-upload-cloud',
    label: 'des images',
  },
)

const emit = defineEmits<{ 'files-selected': [files: File[]] }>()

const isOver = ref(false)
const rejected = ref<string[]>([])
const fileInput = ref<HTMLInputElement>()

function isAcceptable(file: File): boolean {
  const withinSize = props.maxFileSizeMb === undefined || file.size <= props.maxFileSizeMb * 1024 * 1024
  const knownFormat = props.readFormats === undefined || props.readFormats.includes(normalizedExtension(file.name))
  return withinSize && knownFormat
}

function filterFiles(files: FileList | File[]) {
  const candidates = props.multiple ? Array.from(files) : Array.from(files).slice(0, 1)
  const accepted: File[] = []
  const badNames: string[] = []
  for (const file of candidates) {
    if (isAcceptable(file)) accepted.push(file)
    else badNames.push(file.name)
  }
  rejected.value = badNames
  if (accepted.length) emit('files-selected', accepted)
}

function onDrop(event: DragEvent) {
  isOver.value = false
  if (event.dataTransfer?.files.length) filterFiles(event.dataTransfer.files)
}

function onPick(event: Event) {
  const input = event.target as HTMLInputElement
  if (input.files?.length) filterFiles(input.files)
  input.value = ''
}
</script>
