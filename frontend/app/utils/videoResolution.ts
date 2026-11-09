import type { VideoResolutionLadderEntry } from '~/utils/api'

export interface VideoResolutionOption {
  label: string
  width: number
  height: number
}

/**
 * Derives selectable output resolutions from the crop rectangle's own aspect
 * ratio (not the ratio preset id — works identically for fixed presets and
 * freeform "Libre" crops) plus an "Original" entry equal to the crop's own
 * pixel size.
 */
export function computeResolutionOptions(
  cropWidth: number,
  cropHeight: number,
  ladder: VideoResolutionLadderEntry[]
): VideoResolutionOption[] {
  if (cropWidth <= 0 || cropHeight <= 0) return []
  const aspect = cropWidth / cropHeight
  const derived = ladder.map(({ label, height }) => ({
    label,
    width: Math.round((height * aspect) / 2) * 2,
    height
  }))
  return [{ label: 'Original', width: cropWidth, height: cropHeight }, ...derived]
}
