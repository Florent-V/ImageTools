import asyncio


class FfmpegError(Exception):
    """An ffmpeg/ffprobe command exited non-zero, or timed out."""


async def run_ffmpeg(cmd: list[str], timeout_s: float) -> bytes:
    """Run an ffmpeg/ffprobe command, killing it on timeout. Returns stdout."""
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    try:
        stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout_s)
    except TimeoutError:
        process.kill()
        await process.wait()
        raise FfmpegError(f"command timed out after {timeout_s}s: {' '.join(cmd)}")

    if process.returncode != 0:
        raise FfmpegError(stderr.decode(errors="replace").strip())

    return stdout
