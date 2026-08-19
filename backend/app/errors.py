ERROR_STATUS: dict[str, int] = {
    "FILE_TOO_LARGE": 413,
    "UNSUPPORTED_FORMAT": 415,
    "IMAGE_TOO_LARGE": 413,
    "CORRUPT_IMAGE": 422,
    "INVALID_OPERATION": 422,
    "PROCESSING_FAILED": 500,
    "VIDEO_TOO_LARGE": 413,
    "VIDEO_TOO_LONG": 413,
    "UNSUPPORTED_VIDEO_FORMAT": 415,
    "VIDEO_PROCESSING_FAILED": 500,
}


class ImageError(Exception):
    """Every failure the client is allowed to see. Carries a stable code."""

    def __init__(self, code: str, message: str, **detail):
        if code not in ERROR_STATUS:
            raise ValueError(f"unknown error code: {code}")
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = ERROR_STATUS[code]
        super().__init__(message)

    def to_payload(self) -> dict:
        return {"error": {"code": self.code, "message": self.message, "detail": self.detail}}
