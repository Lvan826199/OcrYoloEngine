"""集中配置:环境变量(前缀 OYE_)+ 默认值。"""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

Device = Literal["auto", "cpu", "cuda"]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="OYE_", env_file=".env", extra="ignore")

    device: Device = "auto"
    default_conf_threshold: float = 0.25

    models_config_path: str = "configs/models.yaml"
    templates_config_path: str = "configs/templates.yaml"

    model_cache_size: int = 3
    max_workers: int = 4
    max_queue: int = 32
    request_timeout_s: int = 30

    max_image_bytes: int = 10 * 1024 * 1024
    max_image_pixels: int = 4096 * 4096

    allowed_path_roots: list[str] = Field(default_factory=list)
    api_keys: list[str] = Field(default_factory=list)
    warmup: bool = True

    @property
    def auth_enabled(self) -> bool:
        return len(self.api_keys) > 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
