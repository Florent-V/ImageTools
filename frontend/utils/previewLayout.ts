// Shared sizing for every image-preview canvas (crop, watermark, video crop).
// One relative cap so the preview never dwarfs the page on a wide monitor,
// while still scaling down to fit on narrow screens.
export const PREVIEW_WRAP_CLASS = 'relative block w-full max-w-3xl mx-auto select-none touch-none'
export const PREVIEW_IMG_CLASS = 'block w-full rounded-md'
