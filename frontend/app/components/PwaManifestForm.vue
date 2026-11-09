<template>
  <UCard>
    <template #header>
      <h3 class="font-semibold">
        Manifest
      </h3>
    </template>

    <div class="flex flex-col gap-4">
      <UFormField label="Nom de l'application">
        <UInput
          v-model="local.name"
          placeholder="Mon Application"
          maxlength="45"
        />
      </UFormField>
      <UFormField label="Nom court (écran d'accueil, 12 caractères max)">
        <UInput
          v-model="local.short_name"
          placeholder="MonApp"
          maxlength="12"
        />
      </UFormField>

      <div class="grid grid-cols-2 gap-4">
        <UFormField label="Couleur du thème">
          <UColorPicker v-model="local.theme_color" />
        </UFormField>
        <UFormField label="Couleur de fond">
          <UColorPicker v-model="background" />
        </UFormField>
      </div>

      <UFormField label="Mode d'affichage">
        <USelect
          v-model="local.display"
          :items="[
            { label: 'Standalone (recommandé)', value: 'standalone' },
            { label: 'Plein écran', value: 'fullscreen' },
            { label: 'Interface minimale', value: 'minimal-ui' },
            { label: 'Navigateur', value: 'browser' }
          ]"
        />
      </UFormField>

      <UButton
        size="xs"
        variant="ghost"
        color="neutral"
        class="self-start"
        @click="showAdvanced = !showAdvanced"
      >
        {{ showAdvanced ? 'Masquer les options avancées' : 'Options avancées' }}
      </UButton>

      <div
        v-if="showAdvanced"
        class="flex flex-col gap-4"
      >
        <UFormField label="Description">
          <UTextarea
            v-model="descriptionValue"
            :rows="2"
            maxlength="300"
          />
        </UFormField>
        <UFormField label="Orientation">
          <USelect
            v-model="orientationValue"
            :items="[
              { label: 'Automatique', value: 'any' },
              { label: 'Portrait', value: 'portrait' },
              { label: 'Paysage', value: 'landscape' }
            ]"
          />
        </UFormField>
      </div>
    </div>
  </UCard>
</template>

<script setup lang="ts">
import type { PwaManifestFields } from '~/utils/api'

const props = defineProps<{ modelValue: PwaManifestFields, backgroundColor: string }>()
const emit = defineEmits<{
  'update:modelValue': [value: PwaManifestFields]
  'update:backgroundColor': [value: string]
}>()

const showAdvanced = ref(false)
const local = reactive<PwaManifestFields>({ ...props.modelValue })
const background = ref(props.backgroundColor)

// UTextarea/USelect need plain refs; bridge them to the optional fields on `local`.
const descriptionValue = ref(local.description ?? '')
const orientationValue = ref(local.orientation ?? 'any')

watch(descriptionValue, (value) => {
  local.description = value || null
})
watch(orientationValue, (value) => {
  local.orientation = value
})

watch(local, value => emit('update:modelValue', { ...value }), { deep: true })
watch(background, value => emit('update:backgroundColor', value))

watch(
  () => props.modelValue,
  (newVal) => {
    if (JSON.stringify(newVal) !== JSON.stringify(local)) {
      Object.assign(local, newVal)
      descriptionValue.value = newVal.description ?? ''
      orientationValue.value = newVal.orientation ?? 'any'
    }
  }
)
watch(
  () => props.backgroundColor,
  (newVal) => {
    if (newVal !== background.value) background.value = newVal
  }
)
</script>
