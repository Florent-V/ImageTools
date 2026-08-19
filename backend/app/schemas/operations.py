from typing import Annotated, Literal

from pydantic import BaseModel, Field, model_validator

MAX_DIMENSION = 100_000


class ResizeOp(BaseModel):
    op: Literal["resize"]
    width: int | None = Field(default=None, gt=0, le=MAX_DIMENSION)
    height: int | None = Field(default=None, gt=0, le=MAX_DIMENSION)
    percent: float | None = Field(default=None, gt=0, le=1000)
    keep_ratio: bool = True
    no_upscale: bool = True

    @model_validator(mode="after")
    def check_dimensions(self):
        if self.percent is not None:
            if self.width is not None or self.height is not None:
                raise ValueError("percent cannot be combined with width or height")
            return self
        if self.width is None and self.height is None:
            raise ValueError("resize needs percent, or width, or height")
        return self


class CropOp(BaseModel):
    op: Literal["crop"]
    x: int = Field(ge=0, le=MAX_DIMENSION)
    y: int = Field(ge=0, le=MAX_DIMENSION)
    width: int = Field(gt=0, le=MAX_DIMENSION)
    height: int = Field(gt=0, le=MAX_DIMENSION)


class RotateOp(BaseModel):
    op: Literal["rotate"]
    degrees: Literal[0, 90, 180, 270] = 0
    flip_horizontal: bool = False
    flip_vertical: bool = False


class WatermarkOp(BaseModel):
    op: Literal["watermark"]
    mode: Literal["text", "image"]
    text: str | None = Field(default=None, max_length=200)
    # Fraction of the target image's width/height, anchored at the
    # watermark's own center — 0.5/0.5 is dead center.
    position_x: float = Field(ge=0, le=1, default=0.5)
    position_y: float = Field(ge=0, le=1, default=0.5)
    # Fraction of the target image's width the watermark should occupy.
    scale: float = Field(gt=0, le=2, default=0.5)
    opacity: float = Field(ge=0, le=1, default=0.7)
    rotation: float = Field(ge=-180, le=180, default=0)
    # A translucent white wash over the whole photo, independent of mode and
    # of the watermark's own opacity above.
    white_veil: bool = False
    veil_opacity: float = Field(ge=0, le=1, default=0.3)

    @model_validator(mode="after")
    def check_text(self):
        if self.mode == "text" and not (self.text and self.text.strip()):
            raise ValueError("text watermark needs non-empty text")
        return self


Operation = Annotated[
    ResizeOp | CropOp | RotateOp | WatermarkOp, Field(discriminator="op")
]
