"""Request-handling helpers shared by all three routers (image/video/PWA).

Each router previously reimplemented these independently; a change to the
read strategy, the body-parse shape, or the timeout-handling message had to
be made in three places. Now it's one.
"""

import asyncio
import json
from typing import TypeVar

from fastapi import UploadFile
from pydantic import BaseModel, ValidationError
from starlette.concurrency import run_in_threadpool

from app.errors import ImageError

ModelT = TypeVar("ModelT", bound=BaseModel)


async def read_upload(file: UploadFile, limit_bytes: int, limit_mb: int, error_code: str) -> bytes:
    """Read the body, refusing anything past the limit without buffering it all."""
    chunks: list[bytes] = []
    total = 0
    while chunk := await file.read(1024 * 1024):
        total += len(chunk)
        if total > limit_bytes:
            raise ImageError(error_code, f"File exceeds the {limit_mb} MB limit", limit_bytes=limit_bytes)
        chunks.append(chunk)
    return b"".join(chunks)


def parse_body(model_cls: type[ModelT], raw: str) -> ModelT:
    try:
        return model_cls.model_validate(json.loads(raw))
    except json.JSONDecodeError:
        raise ImageError("INVALID_OPERATION", "The request payload is invalid", errors=[{"message": "malformed JSON"}])
    except ValidationError as exc:
        # Field paths only — never the raw pydantic message, which can echo
        # back submitted values verbatim.
        errors = [{"field": ".".join(str(p) for p in e["loc"]), "message": e["msg"]} for e in exc.errors()]
        raise ImageError("INVALID_OPERATION", "The request payload is invalid", errors=errors)


async def run_with_timeout(fn, *args, timeout_s: float):
    """Run a blocking function in the threadpool, bounded by timeout_s.

    wait_for bounds the caller's wait but cannot kill the running thread —
    the CPU work continues to completion in the pool (a known Python limit).
    """
    try:
        return await asyncio.wait_for(run_in_threadpool(fn, *args), timeout=timeout_s)
    except asyncio.TimeoutError:
        raise ImageError("PROCESSING_FAILED", f"Processing exceeded the {timeout_s}s limit")
