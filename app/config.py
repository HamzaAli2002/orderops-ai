from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    database_url: str = "mysql+aiomysql://orderops:orderops@localhost:3306/orderops"
    alembic_database_url: str = "mysql+pymysql://orderops:orderops@localhost:3306/orderops"

    environment: str = "development"
    app_secret_key: str = "change-me"

    # Used to build the Accept/Reject links inside negotiation emails.
    app_base_url: str = "http://localhost:8000"

    llm_provider: str = "openai"
    openai_api_key: str | None = None
    google_api_key: str | None = None

    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True

    negotiation_discount_pct: int = 10
    negotiation_response_timeout_hours: int = 24

    fraud_risk_threshold: float = 0.7

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()
