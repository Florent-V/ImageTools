from typing import Literal

from pydantic import BaseModel, Field, model_validator

from app.schemas.operations import Operation

OutputFormat = Literal["jpeg", "png", "webp", "avif"]
# Keep in sync with frontend/utils/api.ts's Preset type and
# frontend/components/op-forms/OutputForm.vue's presetNames — these three
# names are a fixed enum, not data, so they're duplicated by design.
Preset = Literal["light", "recommended", "strong"]


class OutputSpec(BaseModel):
    format: OutputFormat
    quality: int | None = Field(default=None, ge=1, le=100)
    preset: Preset | None = None
    target_size_kb: int | None = Field(default=None, gt=0)
    strip_metadata: bool = False

    @model_validator(mode="after")
    def check_single_quality_mode(self):
        chosen = [f for f in (self.quality, self.preset, self.target_size_kb) if f is not None]
        if len(chosen) > 1:
            raise ValueError("choose only one of quality, preset, target_size_kb")
        return self


class ProcessRequest(BaseModel):
    ops: list[Operation] = Field(default_factory=list)
    output: OutputSpec
