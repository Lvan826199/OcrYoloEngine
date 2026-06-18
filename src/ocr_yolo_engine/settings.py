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
    default_conf_threshold: float = Field(default=0.25, ge=0.0, le=1.0)

    models_config_path: str = "configs/models.yaml"
    templates_config_path: str = "configs/templates.yaml"

    model_cache_size: int = Field(default=3, ge=1)
    # 结果缓存:size=0 时完全关闭(默认),核心管线零开销;ttl_s=0 表示不过期。
    result_cache_size: int = Field(default=0, ge=0)
    result_cache_ttl_s: int = Field(default=0, ge=0)
    max_workers: int = Field(default=4, ge=1)
    max_queue: int = Field(default=32, ge=0)
    request_timeout_s: int = Field(default=30, gt=0)

    max_image_bytes: int = Field(default=10 * 1024 * 1024, gt=0)
    max_image_pixels: int = Field(default=4096 * 4096, gt=0)

    allowed_path_roots: list[str] = Field(default_factory=list)
    api_keys: list[str] = Field(default_factory=list)

    @property
    def auth_enabled(self) -> bool:
        return len(self.api_keys) > 0


@lru_cache
def get_settings() -> Settings:
    return Settings()
