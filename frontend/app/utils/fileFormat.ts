import type { OutputFormat } from '~/utils/api'

// Keep in sync with DropZone.vue's own copy — extension-to-canonical-format
// aliasing used both for accept-filtering and for format detection.
const EXTENSION_ALIASES: Record<string, string> = { JPG: 'JPEG', TIF: 'TIFF' }

const WRITABLE_BY_EXTENSION: Record<string, OutputFormat> = {
  JPEG: 'jpeg',
  PNG: 'png',
  WEBP: 'webp',
  AVIF: 'avif'
}

export function extensionOf(name: string): string {
  const dot = name.lastIndexOf('.')
  return dot === -1 ? '' : name.slice(dot + 1).toUpperCase()
}

export function normalizedExtension(name: string): string {
  const ext = extensionOf(name)
  return EXTENSION_ALIASES[ext] ?? ext
}

/** The write-format that would preserve this file's own format, or null if the
 * backend can't write that format (e.g. TIFF, BMP, HEIC) and a fallback is needed. */
export function detectWritableFormat(name: string): OutputFormat | null {
  return WRITABLE_BY_EXTENSION[normalizedExtension(name)] ?? null
}
