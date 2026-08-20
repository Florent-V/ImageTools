import asyncio

from app.config import settings

# Shared across all three routers — one cap on simultaneous heavy work
# (image process, video transcode, PWA kit generation), not one per endpoint.
job_semaphore = asyncio.Semaphore(settings.max_concurrent_jobs)
