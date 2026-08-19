<template>
  <div class="flex flex-col gap-6">
    <div>
      <h1 class="text-2xl font-bold tracking-tight">Générateur</h1>
      <p class="mt-1 text-(--ui-text-muted)">Ajoutez du texte ou dessinez librement sur votre image.</p>
    </div>

    <DropZone v-if="!previewSrc" :read-formats="READ_FORMATS" :max-file-size-mb="MAX_FILE_SIZE_MB" @files-selected="onFilesSelected" />

    <template v-else>
      <GeneratorForm ref="generatorForm" :preview-src="previewSrc" :file-name="file!.name" :mime-type="file!.type" />

      <div class="flex flex-wrap items-center gap-3">
        <UButton size="lg" icon="i-lucide-image-plus" variant="outline" @click="reset">Nouvelle image</UButton>
        <UButton size="lg" icon="i-lucide-download" :loading="exporting" @click="exportAndDownload">
          Télécharger
        </UButton>
        <a v-if="resultUrl" ref="downloadLink" :href="resultUrl" :download="resultName" class="sr-only" />
      </div>
      <UAlert v-if="exportError" color="error" variant="soft" icon="i-lucide-triangle-alert" :title="exportError" />
    </template>
  </div>
</template>

<script setup lang="ts">
// Entirely client-side: the image never leaves the browser, no backend call
// is involved (unlike the other tools, which post to the processing API).
// DropZone checks these against normalizedExtension(), which returns
// upper-case canonical extensions (JPG -> JPEG, TIF -> TIFF).
const READ_FORMATS = ['JPEG', 'PNG', 'WEBP', 'GIF', 'BMP', 'TIFF']
const MAX_FILE_SIZE_MB = 50

const previewSrc = ref<string>()
const file = ref<File>()
const exporting = ref(false)
const exportError = ref<string>()
const resultUrl = ref<string>()
const resultName = ref<string>()

const generatorForm = ref<{ exportImage: () => Promise<{ blob: Blob; fileName: string }> }>()
const downloadLink = ref<HTMLAnchorElement>()

onBeforeUnmount(() => {
  if (previewSrc.value) URL.revokeObjectURL(previewSrc.value)
  if (resultUrl.value) URL.revokeObjectURL(resultUrl.value)
})

function onFilesSelected(files: File[]) {
  const picked = files[0]
  if (!picked) return
  file.value = picked
  previewSrc.value = URL.createObjectURL(picked)
}

function reset() {
  if (previewSrc.value) URL.revokeObjectURL(previewSrc.value)
  if (resultUrl.value) URL.revokeObjectURL(resultUrl.value)
  previewSrc.value = undefined
  file.value = undefined
  resultUrl.value = undefined
  resultName.value = undefined
  exportError.value = undefined
}

async function exportAndDownload() {
  if (!generatorForm.value) return
  exporting.value = true
  exportError.value = undefined
  try {
    const { blob, fileName } = await generatorForm.value.exportImage()
    if (resultUrl.value) URL.revokeObjectURL(resultUrl.value)
    resultUrl.value = URL.createObjectURL(blob)
    resultName.value = fileName
    await nextTick()
    downloadLink.value?.click()
  } catch {
    exportError.value = "Impossible de générer l'image."
  } finally {
    exporting.value = false
  }
}
</script>
