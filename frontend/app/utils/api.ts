export type OutputFormat = 'jpeg' | 'png' | 'webp' | 'avif'
// Keep in sync with backend/app/schemas/request.py's Preset and
// components/op-forms/OutputForm.vue's presetNames — fixed enum, not data.
export type Preset = 'light' | 'recommended' | 'strong'

export interface ResizeOp {
  op: 'resize'
  width?: number | null
  height?: number | null
  percent?: number | null
  keep_ratio?: boolean
  no_upscale?: boolean
}

export interface CropOp {
  op: 'crop'
  x: number
  y: number
  width: number
  height: number
}

export interface RotateOp {
  op: 'rotate'
  degrees?: 0 | 90 | 180 | 270
  flip_horizontal?: boolean
  flip_vertical?: boolean
}

export interface WatermarkOp {
  op: 'watermark'
  mode: 'text' | 'image'
  text?: string | null
  position_x: number
  position_y: number
  scale: number
  opacity: number
  rotation?: number
  white_veil?: boolean
  veil_opacity?: number
}

export type Operation = ResizeOp | CropOp | RotateOp | WatermarkOp

export interface OutputSpec {
  format: OutputFormat
  quality?: number | null
  preset?: Preset | null
  target_size_kb?: number | null
  strip_metadata?: boolean
}

export interface ProcessRequest {
  ops: Operation[]
  output: OutputSpec
}

export interface ProcessResult {
  blob: Blob
  outputWidth: number
  outputHeight: number
  outputSize: number
  inputSize: number
  quality: number
  extension: string
}

export interface FormatsResponse {
  read: string[]
  write: string[]
  presets: Record<Preset, Record<string, number>>
  limits: { max_file_size_mb: number, max_megapixels: number }
}

export interface InspectResponse {
  width: number
  height: number
  format: string
  size_bytes: number
  has_exif: boolean
  has_gps: boolean
  has_icc: boolean
}

interface ApiErrorPayload {
  error: { code: string, message: string, detail: Record<string, unknown> }
}

export class ApiError extends Error {
  code: string
  detail: Record<string, unknown>

  constructor(payload: ApiErrorPayload) {
    super(payload.error.message)
    this.code = payload.error.code
    this.detail = payload.error.detail
  }
}

async function throwApiError(response: Response): Promise<never> {
  try {
    const payload = (await response.json()) as ApiErrorPayload
    throw new ApiError(payload)
  } catch (err) {
    if (err instanceof ApiError) throw err
    throw new ApiError({
      error: {
        code: 'PROCESSING_FAILED',
        message: `Erreur inattendue du serveur (${response.status}).`,
        detail: {}
      }
    })
  }
}

// Same-origin /api/** calls, authenticated by the session cookie. A 401 means
// the session is gone (expired, revoked, access removed): send the user back
// through the OAuth server, then to this page.
async function apiFetch(path: string, init?: RequestInit): Promise<Response> {
  const response = await fetch(path, init)
  if (response.status === 401) {
    useUser().login()
    throw new ApiError({
      error: { code: 'UNAUTHENTICATED', message: 'Session expirée, reconnexion…', detail: {} }
    })
  }
  return response
}

export async function fetchFormats(): Promise<FormatsResponse> {
  const response = await apiFetch('/api/formats')
  if (!response.ok) return throwApiError(response)
  return response.json()
}

export async function inspectImage(file: File): Promise<InspectResponse> {
  const body = new FormData()
  body.append('file', file)
  const response = await apiFetch('/api/inspect', { method: 'POST', body })
  if (!response.ok) return throwApiError(response)
  return response.json()
}

export async function processImage(
  file: File,
  request: ProcessRequest,
  watermarkFile?: File
): Promise<ProcessResult> {
  const body = new FormData()
  body.append('file', file)
  body.append('request', JSON.stringify(request))
  if (watermarkFile) body.append('watermark_file', watermarkFile)
  const response = await apiFetch('/api/process', { method: 'POST', body })
  if (!response.ok) return throwApiError(response)
  const blob = await response.blob()
  return {
    blob,
    outputWidth: Number(response.headers.get('X-Output-Width')),
    outputHeight: Number(response.headers.get('X-Output-Height')),
    outputSize: Number(response.headers.get('X-Output-Size')),
    inputSize: Number(response.headers.get('X-Input-Size')),
    quality: Number(response.headers.get('X-Output-Quality')),
    extension: response.headers.get('X-Output-Extension') ?? 'bin'
  }
}

export interface PwaCropRect {
  x: number
  y: number
  width: number
  height: number
}

export interface PwaManifestFields {
  name: string
  short_name: string
  theme_color: string
  display: 'standalone' | 'fullscreen' | 'minimal-ui' | 'browser'
  description?: string | null
  orientation?: 'any' | 'portrait' | 'landscape' | null
}

export interface PwaPlatforms {
  android: boolean
  ios: boolean
  favicon: boolean
  windows: boolean
  splash: boolean
}

export interface PwaGenerateRequest {
  crop: PwaCropRect
  background_color: string
  manifest: PwaManifestFields
  platforms: PwaPlatforms
}

export interface PwaKitResult {
  blob: Blob
  fileCount: number
}

export async function generatePwaKit(file: File, request: PwaGenerateRequest): Promise<PwaKitResult> {
  const body = new FormData()
  body.append('file', file)
  body.append('request', JSON.stringify(request))
  const response = await apiFetch('/api/pwa/generate', { method: 'POST', body })
  if (!response.ok) return throwApiError(response)
  const blob = await response.blob()
  return { blob, fileCount: Number(response.headers.get('X-File-Count') ?? 0) }
}

export type VideoQuality = 'light' | 'recommended' | 'strong' | 'max'
export type VideoContainer = 'mp4' | 'mov' | 'mkv' | 'webm'
export type VideoFps = 'original' | 30 | 60

export interface VideoCropRect {
  x: number
  y: number
  width: number
  height: number
}

export interface VideoRatioPreset {
  id: string
  label: string
  description: string
  ratio: [number, number] | null
}

export interface VideoResolutionLadderEntry {
  label: string
  height: number
}

export interface VideoContainerOption {
  id: VideoContainer
  label: string
}

export interface VideoPresetsResponse {
  ratios: VideoRatioPreset[]
  resolution_ladder: VideoResolutionLadderEntry[]
  containers: VideoContainerOption[]
  fps: VideoFps[]
  quality: VideoQuality[]
}

export interface VideoLimits {
  max_file_size_mb: number
  max_duration_s: number
}

export interface VideoInspectResponse {
  duration_s: number
  width: number
  height: number
  format: string
  size_bytes: number
  preview_frame: string
}

export interface VideoOutputSpec {
  resolution_width: number
  resolution_height: number
  quality: VideoQuality
  container: VideoContainer
  fps: VideoFps
}

export interface VideoProcessRequest {
  crop: VideoCropRect | null
  output: VideoOutputSpec
}

export interface VideoProcessResult {
  blob: Blob
  outputWidth: number
  outputHeight: number
  outputSize: number
  inputSize: number
}

export async function fetchVideoLimits(): Promise<VideoLimits> {
  const response = await apiFetch('/api/video/limits')
  if (!response.ok) return throwApiError(response)
  return response.json()
}

export async function fetchVideoPresets(): Promise<VideoPresetsResponse> {
  const response = await apiFetch('/api/video/presets')
  if (!response.ok) return throwApiError(response)
  return response.json()
}

export async function fetchVideoFrame(file: File, timestampS: number): Promise<{ preview_frame: string }> {
  const body = new FormData()
  body.append('file', file)
  body.append('timestamp_s', String(timestampS))
  const response = await apiFetch('/api/video/frame', { method: 'POST', body })
  if (!response.ok) return throwApiError(response)
  return response.json()
}

export async function inspectVideo(file: File): Promise<VideoInspectResponse> {
  const body = new FormData()
  body.append('file', file)
  const response = await apiFetch('/api/video/inspect', { method: 'POST', body })
  if (!response.ok) return throwApiError(response)
  return response.json()
}

export async function processVideo(file: File, request: VideoProcessRequest): Promise<VideoProcessResult> {
  const body = new FormData()
  body.append('file', file)
  body.append('request', JSON.stringify(request))
  const response = await apiFetch('/api/video/process', { method: 'POST', body })
  if (!response.ok) return throwApiError(response)
  const blob = await response.blob()
  return {
    blob,
    outputWidth: Number(response.headers.get('X-Output-Width')),
    outputHeight: Number(response.headers.get('X-Output-Height')),
    outputSize: Number(response.headers.get('X-Output-Size')),
    inputSize: Number(response.headers.get('X-Input-Size'))
  }
}
