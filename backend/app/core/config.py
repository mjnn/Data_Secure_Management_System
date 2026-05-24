from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "DSMS Backend"
    secret_key: str = Field(default="change-me-in-production", alias="SECRET_KEY")
    algorithm: str = Field(default="HS256", alias="ALGORITHM")
    access_token_expire_minutes: int = Field(default=30, alias="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(default=7, alias="REFRESH_TOKEN_EXPIRE_DAYS")
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


settings = Settings()
