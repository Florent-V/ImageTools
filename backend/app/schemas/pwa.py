from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.operations import MAX_DIMENSION

HEX_COLOR_PATTERN = r"^#[0-9a-fA-F]{6}$"


class PwaCropRect(BaseModel):
    x: int = Field(ge=0, le=MAX_DIMENSION)
    y: int = Field(ge=0, le=MAX_DIMENSION)
    width: int = Field(gt=0, le=MAX_DIMENSION)
    height: int = Field(gt=0, le=MAX_DIMENSION)

    @model_validator(mode="after")
    def check_square(self):
        if self.width != self.height:
            raise ValueError("PWA crop must be square (width == height)")
        return self


class PwaManifest(BaseModel):
    name: str = Field(min_length=1, max_length=45)
    # Home-screen labels truncate long short_names; 12 chars is the widely
    # used practical ceiling recommended for manifest short_name.
    short_name: str = Field(min_length=1, max_length=12)
    theme_color: str = Field(pattern=HEX_COLOR_PATTERN)
    display: Literal["standalone", "fullscreen", "minimal-ui", "browser"] = "standalone"
    description: str | None = Field(default=None, max_length=300)
    orientation: Literal["any", "portrait", "landscape"] | None = None


class PwaPlatforms(BaseModel):
    android: bool = True
    ios: bool = True
    favicon: bool = True
    windows: bool = True
    splash: bool = True


class PwaGenerateRequest(BaseModel):
    crop: PwaCropRect
    background_color: str = Field(pattern=HEX_COLOR_PATTERN)
    manifest: PwaManifest
    platforms: PwaPlatforms = Field(default_factory=PwaPlatforms)
