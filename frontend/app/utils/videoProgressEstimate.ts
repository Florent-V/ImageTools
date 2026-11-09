import type { VideoContainer } from '~/utils/api'

// libx264 "veryfast" comfortably beats real-time at social-clip resolutions;
// libvpx-vp9 (WebM) is markedly slower — these are rough multipliers on the
// source duration, not measured benchmarks, hence "estimated" in the UI.
const CONTAINER_SPEED_FACTOR: Record<VideoContainer, number> = {
  mp4: 0.5,
  mov: 0.5,
  mkv: 0.5,
  webm: 3
}

const REFERENCE_PIXELS = 1920 * 1080

/** A rough processing-time estimate (seconds), for an animated "estimated progress" bar — not a real ffmpeg readout. */
export function estimateProcessingSeconds(
  durationS: number,
  outputWidth: number,
  outputHeight: number,
  container: VideoContainer
): number {
  const resolutionFactor = Math.max((outputWidth * outputHeight) / REFERENCE_PIXELS, 0.2)
  const estimate = durationS * CONTAINER_SPEED_FACTOR[container] * resolutionFactor
  return Math.max(estimate, 1.5)
}
