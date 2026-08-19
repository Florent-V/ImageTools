import asyncio

import pytest

from app.engine.video.runner import FfmpegError, run_ffmpeg


def test_run_ffmpeg_returns_stdout_on_success():
    stdout = asyncio.run(run_ffmpeg(["/bin/echo", "-n", "hello"], timeout_s=5))
    assert stdout == b"hello"


def test_run_ffmpeg_raises_on_nonzero_exit():
    with pytest.raises(FfmpegError):
        asyncio.run(run_ffmpeg(["/bin/false"], timeout_s=5))


def test_run_ffmpeg_kills_the_process_on_timeout():
    with pytest.raises(FfmpegError, match="timed out"):
        asyncio.run(run_ffmpeg(["/bin/sleep", "5"], timeout_s=0.2))
