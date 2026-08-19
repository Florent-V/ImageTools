from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    max_file_size_mb: int = 50
    max_megapixels: int = 100
    request_timeout_s: int = 30
    max_video_file_size_mb: int = 200
    max_video_duration_s: int = 60
    video_timeout_s: int = 180

    model_config = {"env_prefix": "IMGCONV_"}

    @property
    def max_file_size_bytes(self) -> int:
        return self.max_file_size_mb * 1024 * 1024

    @property
    def max_pixels(self) -> int:
        return self.max_megapixels * 1_000_000

    @property
    def max_video_file_size_bytes(self) -> int:
        return self.max_video_file_size_mb * 1024 * 1024


settings = Settings()
