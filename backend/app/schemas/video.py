from typing import Literal

from pydantic import BaseModel, Field

from app.schemas.operations import Rect

VideoQuality = Literal["light", "recommended", "strong", "max"]
VideoContainer = Literal["mp4", "mov", "mkv", "webm"]
VideoFps = Literal["original", 30, 60]


class VideoCropRect(Rect):
    pass


class VideoOutputSpec(BaseModel):
    resolution_width: int = Field(gt=0)
    resolution_height: int = Field(gt=0)
    quality: VideoQuality = "recommended"
    container: VideoContainer = "mp4"
    fps: VideoFps = "original"


class VideoProcessRequest(BaseModel):
    crop: VideoCropRect | None = None
    output: VideoOutputSpec
