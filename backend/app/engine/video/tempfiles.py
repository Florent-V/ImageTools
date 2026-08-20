import tempfile
from contextlib import contextmanager
from pathlib import Path


@contextmanager
def temp_video_file(data: bytes, suffix: str = ".mp4"):
    """Write data to a temp file, guaranteeing cleanup even if the block raises."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(data)
        path = Path(tmp.name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)


@contextmanager
def temp_output_path(suffix: str):
    """An empty temp path for ffmpeg to write into, cleaned up on the way out."""
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        path = Path(tmp.name)
    try:
        yield path
    finally:
        path.unlink(missing_ok=True)
