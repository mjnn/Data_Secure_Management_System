from pydantic import Field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_WEAK_SECRET_KEYS = frozenset({"", "change-me-in-production"})
_WEAK_SUPERUSER_PASSWORDS = frozenset({"Admin123456"})


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DSMS Backend"
    dsms_environment: str = Field(default="development", alias="DSMS_ENVIRONMENT")
    dsms_seed_test_users: bool = Field(default=False, alias="DSMS_SEED_TEST_USERS")
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
    refresh_token_purge_interval_seconds: int = Field(
        default=3600, alias="REFRESH_TOKEN_PURGE_INTERVAL_SECONDS"
    )
    first_superuser: str = Field(default="admin", alias="FIRST_SUPERUSER")
    first_superuser_password: str = Field(default="Admin123456", alias="FIRST_SUPERUSER_PASSWORD")
    database_url: str = Field(default="sqlite:///./dsms.db", alias="DATABASE_URL")
    backend_cors_origins: list[str] = Field(
        default=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:4173", "http://127.0.0.1:4173"],
        alias="BACKEND_CORS_ORIGINS",
    )
    tenant_admin_user_directory_scope: str = Field(default="all", alias="TENANT_ADMIN_USER_DIRECTORY_SCOPE")
    test_security_fo_password: str = Field(default="SecurityFo123456", alias="TEST_SECURITY_FO_PASSWORD")
    test_function_fo_password: str = Field(default="FunctionFo123456", alias="TEST_FUNCTION_FO_PASSWORD")
    upload_root: str = Field(default="./uploads", alias="DSMS_UPLOAD_ROOT")
    upload_max_bytes: int = Field(default=20 * 1024 * 1024, alias="DSMS_UPLOAD_MAX_BYTES")
    auth_rate_limit_enabled: bool = Field(default=True, alias="DSMS_AUTH_RATE_LIMIT_ENABLED")

    @model_validator(mode="after")
    def validate_production_secrets(self) -> "Settings":
        if self.dsms_environment.lower() != "production":
            return self
        if self.secret_key in _WEAK_SECRET_KEYS:
            raise ValueError("生产环境必须设置安全的 SECRET_KEY")
        if self.first_superuser_password in _WEAK_SUPERUSER_PASSWORDS:
            raise ValueError("生产环境必须设置安全的 FIRST_SUPERUSER_PASSWORD")
        return self

    def should_seed_test_users(self) -> bool:
        if self.dsms_environment.lower() == "production":
            return self.dsms_seed_test_users
        return True


settings = Settings()
