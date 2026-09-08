from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env", "../../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    database_url: str = "sqlite:///./cheltuieli.db"
    secret_key: str = "schimba-aceasta-cheie-in-productie"
    jwt_expire_hours: int = 336
    openai_api_key: str = ""
    openai_model: str = "gpt-4o-mini"
    upload_dir: str = "./uploads"
    cors_origins: str = "http://localhost:5173,http://127.0.0.1:5173,http://localhost:5174,http://127.0.0.1:5174"
    cookie_secure: bool = False
    cookie_samesite: str = "lax"
    public_url: str = "http://localhost:5173"
    auth_mode: str = "local"
    ingress_trusted_ips: str = "172.30.32.2"
    hass_admin_users: str = ""
    frontend_dir: str = ""
    supervisor_token: str = ""

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]

    @property
    def openai_configured(self) -> bool:
        return bool(self.openai_api_key.strip())

    @property
    def is_homeassistant(self) -> bool:
        return self.auth_mode.strip().lower() in {"homeassistant", "ha", "hassio"}

    @property
    def ingress_ip_list(self) -> list[str]:
        return [item.strip() for item in self.ingress_trusted_ips.split(",") if item.strip()]

    @property
    def hass_admin_user_list(self) -> list[str]:
        return [item.strip().lower() for item in self.hass_admin_users.split(",") if item.strip()]


settings = Settings()
