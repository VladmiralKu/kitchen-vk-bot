from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    database_url: str = Field(default="sqlite+aiosqlite:///./local.db", alias="DATABASE_URL")
    vk_token: str = Field(default="", alias="VK_TOKEN")
    vk_group_id: int | None = Field(default=None, alias="VK_GROUP_ID")
    vk_secret: str = Field(default="", alias="VK_SECRET")
    vk_confirmation_code: str = Field(default="", alias="VK_CONFIRMATION_CODE")
    superadmin_vk_id: int | None = Field(default=None, alias="SUPERADMIN_VK_ID")
    app_timezone: str = Field(default="Europe/Chisinau", alias="APP_TIMEZONE")
    auto_send_orders: bool = Field(default=False, alias="AUTO_SEND_ORDERS")
    toggle_item_ready: bool = Field(default=True, alias="TOGGLE_ITEM_READY")
    kitchen_mode: str = Field(default="private", alias="KITCHEN_MODE")
    kitchen_peer_id: int | None = Field(default=None, alias="KITCHEN_PEER_ID")
    stops_ttl_hours: int = Field(default=12, alias="STOPS_TTL_HOURS")
    public_base_url: str | None = Field(default=None, alias="PUBLIC_BASE_URL")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")

    @property
    def sqlalchemy_database_url(self) -> str:
        if self.database_url.startswith("postgres://"):
            return self.database_url.replace("postgres://", "postgresql+asyncpg://", 1)
        if self.database_url.startswith("postgresql://"):
            return self.database_url.replace("postgresql://", "postgresql+asyncpg://", 1)
        return self.database_url


@lru_cache
def get_settings() -> Settings:
    return Settings()
