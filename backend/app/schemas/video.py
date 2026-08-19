from typing import Literal

from pydantic import BaseModel, Field

VideoQuality = Literal["light", "recommended", "strong", "max"]
VideoContainer = Literal["mp4", "mov", "mkv", "webm"]
VideoFps = Literal["original", 30, 60]


class VideoCropRect(BaseModel):
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    width: int = Field(gt=0)
    height: int = Field(gt=0)


class VideoOutputSpec(BaseModel):
    resolution_width: int = Field(gt=0)
    resolution_height: int = Field(gt=0)
    quality: VideoQuality = "recommended"
    container: VideoContainer = "mp4"
    fps: VideoFps = "original"


class VideoProcessRequest(BaseModel):
    crop: VideoCropRect | None = None
    output: VideoOutputSpec
